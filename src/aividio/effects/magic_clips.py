"""MagicClips — extract viral short-form clips from long-form videos.

Analyzes a transcript for clip-worthy segments using Claude, extracts them
from the source video, optionally reformats to portrait (9:16), and applies
captions.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg

from aividio.config.settings import Settings, get_settings
from aividio.utils.ffmpeg import (
    FFmpegError,
    get_resolution,
    run_ffmpeg,
)
from aividio.utils.retry import retry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claude prompt for clip extraction
# ---------------------------------------------------------------------------

_CLIPS_SYSTEM_PROMPT = """\
You are an expert at identifying viral-worthy clips from long-form video
transcripts. Analyze the transcript and find the best segments for short-form
content (TikTok, YouTube Shorts, Instagram Reels).

For each clip, return a JSON array of objects with:
- "start": float — start timestamp in seconds
- "end": float — end timestamp in seconds
- "title": string — catchy title for the clip (max 60 chars)
- "hook": string — the opening hook line of the clip
- "score": integer 1-100 — virality score
- "reason": string — why this segment would perform well

Criteria for high-scoring clips:
1. **Hook potential** — Does it start with something attention-grabbing?
2. **Self-contained narrative** — Can it stand alone without full context?
3. **Emotional peak** — Does it evoke strong emotion (surprise, laughter, curiosity)?
4. **Surprise/twist** — Is there an unexpected insight or revelation?
5. **Shareability** — Would someone share this with a friend?
6. **Educational value** — Does it teach something concisely?

Constraints:
- Target duration: {min_duration}-{max_duration} seconds per clip
- Maximum {count} clips
- Clips should NOT overlap
- Prefer natural sentence boundaries for start/end
- Response: ONLY the JSON array — no markdown fences, no commentary
"""

_CLIPS_USER_TEMPLATE = """\
Full transcript ({word_count} words, {total_duration:.1f}s):

{transcript_text}

Find the {count} best viral clips ({min_duration}-{max_duration}s each).
"""


class MagicClips:
    """Extract viral short-form clips from long-form videos.

    Uses Claude to identify the most clip-worthy segments based on hook
    potential, narrative completeness, emotional peaks, and shareability.
    Supports automatic reformatting from landscape to portrait and
    optional caption burn-in.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(f"aividio.effects.{self.__class__.__name__}")

    # ------------------------------------------------------------------
    # Clip analysis
    # ------------------------------------------------------------------

    def analyze_for_clips(
        self,
        word_timestamps: list[dict],
        script: dict | None = None,
        target_duration: tuple[int, int] = (15, 60),
        count: int = 5,
    ) -> list[dict]:
        """Use Claude to identify the best clip-worthy segments.

        Considers hook potential, self-contained narrative, emotional peaks,
        and surprise/twist moments.

        Parameters:
            word_timestamps: Word-level timestamps from Whisper.
            script: Optional script dict for additional context.
            target_duration: Tuple of ``(min_seconds, max_seconds)`` for clips.
            count: Number of clips to find.

        Returns:
            List of clip dicts sorted by score (descending), each with keys:
            ``start``, ``end``, ``title``, ``hook``, ``score``, ``reason``.
        """
        if not word_timestamps:
            self.logger.warning("No word timestamps; returning empty clip list")
            return []

        import anthropic

        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            self.logger.warning(
                "No Anthropic API key; falling back to heuristic clip detection"
            )
            return self._analyze_heuristic(word_timestamps, target_duration, count)

        client = anthropic.Anthropic(api_key=api_key)

        transcript_text = _format_transcript(word_timestamps)
        total_duration = word_timestamps[-1]["end"] if word_timestamps else 0.0
        min_dur, max_dur = target_duration

        system = _CLIPS_SYSTEM_PROMPT.format(
            min_duration=min_dur,
            max_duration=max_dur,
            count=count,
        )
        user_msg = _CLIPS_USER_TEMPLATE.format(
            word_count=len(word_timestamps),
            total_duration=total_duration,
            transcript_text=transcript_text,
            count=count,
            min_duration=min_dur,
            max_duration=max_dur,
        )

        self.logger.info(
            "Analyzing %d words for viral clips (target %d-%ds, count=%d)",
            len(word_timestamps),
            min_dur,
            max_dur,
            count,
        )

        try:
            response = self._call_claude(client, system, user_msg)
            clips = self._parse_clips_response(response)
        except Exception as exc:
            self.logger.error("Claude clip analysis failed: %s — using heuristic", exc)
            return self._analyze_heuristic(word_timestamps, target_duration, count)

        # Validate and clean up.
        validated: list[dict] = []
        for clip in clips[:count]:
            clip["start"] = max(0.0, float(clip.get("start", 0)))
            clip["end"] = max(
                clip["start"] + min_dur,
                min(total_duration, float(clip.get("end", clip["start"] + 30))),
            )
            clip["title"] = str(clip.get("title", "Untitled Clip"))[:60]
            clip["hook"] = str(clip.get("hook", ""))
            clip["score"] = max(0, min(100, int(clip.get("score", 50))))
            clip.setdefault("reason", "AI selection")
            validated.append(clip)

        # Sort by score descending.
        validated.sort(key=lambda c: c["score"], reverse=True)

        self.logger.info("Found %d clip candidates", len(validated))
        return validated

    @retry(max_attempts=2, base_delay=2.0, exceptions=(Exception,))
    def _call_claude(self, client: Any, system: str, user_msg: str) -> str:
        """Call Claude API and return raw response text."""
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()

    def _parse_clips_response(self, raw_text: str) -> list[dict]:
        """Parse Claude's clip analysis response."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())

    def _analyze_heuristic(
        self,
        word_timestamps: list[dict],
        target_duration: tuple[int, int],
        count: int,
    ) -> list[dict]:
        """Heuristic clip detection without an LLM.

        Looks for natural sentence boundaries and selects segments of the
        target duration that begin at sentence starts.
        """
        if not word_timestamps:
            return []

        min_dur, max_dur = target_duration
        total_duration = word_timestamps[-1]["end"]

        # Find sentence boundaries (words after . ! ?).
        sentence_starts: list[int] = [0]
        for i, w in enumerate(word_timestamps):
            if i > 0 and word_timestamps[i - 1]["word"].rstrip().endswith((".", "!", "?")):
                sentence_starts.append(i)

        # Generate candidate clips from sentence boundaries.
        candidates: list[dict] = []
        target_mid = (min_dur + max_dur) / 2.0

        for start_idx in sentence_starts:
            start_time = word_timestamps[start_idx]["start"]

            # Find the best end point near target duration.
            best_end_idx = start_idx
            for j in range(start_idx + 1, len(word_timestamps)):
                elapsed = word_timestamps[j]["end"] - start_time
                if elapsed >= min_dur:
                    best_end_idx = j
                if elapsed >= target_mid:
                    # Try to end at a sentence boundary.
                    if word_timestamps[j]["word"].rstrip().endswith((".", "!", "?")):
                        best_end_idx = j
                        break
                if elapsed >= max_dur:
                    break

            if best_end_idx <= start_idx:
                continue

            end_time = word_timestamps[best_end_idx]["end"]
            clip_duration = end_time - start_time

            if clip_duration < min_dur:
                continue

            # Extract hook (first few words).
            hook_words = [
                word_timestamps[k]["word"]
                for k in range(start_idx, min(start_idx + 8, len(word_timestamps)))
            ]
            hook = " ".join(hook_words)

            # Simple scoring: prefer clips in the first third or last quarter.
            position_score = 0
            relative_pos = start_time / max(1.0, total_duration)
            if relative_pos < 0.33:
                position_score = 30  # Early content often has strong hooks.
            elif relative_pos > 0.75:
                position_score = 20  # Late content often has conclusions.
            else:
                position_score = 10

            # Duration score: prefer clips near the middle of the target range.
            duration_score = max(0, 30 - abs(clip_duration - target_mid) * 2)

            score = int(position_score + duration_score)

            candidates.append({
                "start": start_time,
                "end": end_time,
                "title": f"Clip at {start_time:.0f}s",
                "hook": hook,
                "score": min(100, max(0, score)),
                "reason": "heuristic selection",
            })

        # Remove overlapping clips (keep higher-scored ones).
        candidates.sort(key=lambda c: c["score"], reverse=True)
        selected: list[dict] = []
        for cand in candidates:
            overlaps = any(
                not (cand["end"] <= s["start"] or cand["start"] >= s["end"])
                for s in selected
            )
            if not overlaps:
                selected.append(cand)
            if len(selected) >= count:
                break

        return selected

    # ------------------------------------------------------------------
    # Clip extraction
    # ------------------------------------------------------------------

    def extract_clip(
        self,
        video_path: Path,
        start: float,
        end: float,
        output_path: Path,
        reformat: str | None = "portrait",
    ) -> Path:
        """Extract and optionally reformat a single clip.

        Can crop landscape video to portrait (9:16) with smart center
        detection (keeps the center third of the frame by default).

        Parameters:
            video_path: Source video.
            start: Start timestamp in seconds.
            end: End timestamp in seconds.
            output_path: Where to write the extracted clip.
            reformat: ``"portrait"`` to crop to 9:16, ``"square"`` for 1:1,
                or ``None`` to keep the original aspect ratio.

        Returns:
            Path to the extracted clip.

        Raises:
            FileNotFoundError: If *video_path* does not exist.
            FFmpegError: On any ffmpeg failure.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        width, height = get_resolution(video_path)
        duration = end - start

        self.logger.info(
            "Extracting clip: %.1f-%.1fs (%.1fs) from %s, reformat=%s",
            start,
            end,
            duration,
            video_path.name,
            reformat,
        )

        # Build filter chain.
        video_filters: list[str] = []

        if reformat == "portrait":
            # Crop to 9:16 aspect ratio from center.
            target_w = int(height * 9 / 16)
            if target_w > width:
                # Video is already narrower than 9:16; scale up.
                target_w = 1080
                target_h = 1920
                video_filters.append(f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease")
                video_filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
            else:
                # Crop center.
                crop_x = (width - target_w) // 2
                video_filters.append(f"crop={target_w}:{height}:{crop_x}:0")
                video_filters.append("scale=1080:1920:force_original_aspect_ratio=decrease")
                video_filters.append("pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black")

        elif reformat == "square":
            # Crop to 1:1 from center.
            side = min(width, height)
            crop_x = (width - side) // 2
            crop_y = (height - side) // 2
            video_filters.append(f"crop={side}:{side}:{crop_x}:{crop_y}")
            video_filters.append("scale=1080:1080")

        video_filters.append("setsar=1")

        filter_str = ",".join(video_filters)

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-i", str(video_path),
            "-t", f"{duration:.3f}",
            "-vf", filter_str,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]

        run_ffmpeg(cmd, desc="MagicClips extract_clip", timeout=300)

        self.logger.info("Clip extracted: %s (%.1fs)", output_path, duration)
        return output_path

    # ------------------------------------------------------------------
    # Batch clip generation
    # ------------------------------------------------------------------

    def generate_clips(
        self,
        video_path: Path,
        word_timestamps: list[dict],
        count: int = 5,
        format: str = "portrait",
        apply_captions: bool = True,
        caption_template: str = "tiktok_viral",
        target_duration: tuple[int, int] = (15, 60),
        output_dir: Path | None = None,
    ) -> list[Path]:
        """One-click: analyze, extract, reformat, and caption multiple clips.

        Parameters:
            video_path: Source long-form video.
            word_timestamps: Word-level timestamps from Whisper.
            count: Number of clips to generate.
            format: Output format: ``"portrait"``, ``"square"``, or ``"landscape"``.
            apply_captions: Whether to burn captions into clips.
            caption_template: Caption style name for burn-in.
            target_duration: Tuple of (min, max) seconds per clip.
            output_dir: Directory for output clips (auto-generated if ``None``).

        Returns:
            List of paths to generated clip files, sorted by virality score.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_dir is None:
            output_dir = video_path.parent / f"{video_path.stem}_clips"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "Generating %d clips from %s (format=%s, captions=%s)",
            count,
            video_path.name,
            format,
            apply_captions,
        )

        # 1. Analyze for clip-worthy segments.
        clips = self.analyze_for_clips(
            word_timestamps=word_timestamps,
            target_duration=target_duration,
            count=count,
        )

        if not clips:
            self.logger.warning("No clip candidates found")
            return []

        # 2. Extract each clip.
        reformat = format if format != "landscape" else None
        output_paths: list[Path] = []

        for i, clip in enumerate(clips):
            clip_filename = f"clip_{i + 1:02d}_{clip['score']}_{_slugify(clip['title'])}.mp4"
            clip_path = output_dir / clip_filename

            try:
                extracted = self.extract_clip(
                    video_path=video_path,
                    start=clip["start"],
                    end=clip["end"],
                    output_path=clip_path,
                    reformat=reformat,
                )
            except (FFmpegError, FileNotFoundError) as exc:
                self.logger.error("Failed to extract clip %d: %s", i + 1, exc)
                continue

            # 3. Apply captions if requested.
            if apply_captions:
                try:
                    captioned = self._apply_clip_captions(
                        clip_path=extracted,
                        word_timestamps=word_timestamps,
                        clip_start=clip["start"],
                        clip_end=clip["end"],
                        caption_template=caption_template,
                    )
                    output_paths.append(captioned)
                except Exception as exc:
                    self.logger.warning(
                        "Caption burn-in failed for clip %d: %s — keeping uncaptioned",
                        i + 1,
                        exc,
                    )
                    output_paths.append(extracted)
            else:
                output_paths.append(extracted)

        self.logger.info(
            "Generated %d/%d clips in %s",
            len(output_paths),
            len(clips),
            output_dir,
        )
        return output_paths

    def _apply_clip_captions(
        self,
        clip_path: Path,
        word_timestamps: list[dict],
        clip_start: float,
        clip_end: float,
        caption_template: str,
    ) -> Path:
        """Apply captions to an extracted clip.

        Filters word timestamps to the clip's time range, adjusts them to
        start from 0, generates an ASS file, and burns it in.
        """
        from aividio.video.captions_render import burn_captions, generate_ass_file

        # Filter and offset word timestamps for this clip.
        clip_words: list[dict] = []
        for w in word_timestamps:
            if w["start"] >= clip_start and w["end"] <= clip_end:
                clip_words.append({
                    "word": w["word"],
                    "start": round(w["start"] - clip_start, 3),
                    "end": round(w["end"] - clip_start, 3),
                })

        if not clip_words:
            return clip_path

        # Map caption template names to style presets.
        style_map: dict[str, str] = {
            "tiktok_viral": "bold_centered",
            "youtube_shorts": "bold_centered",
            "subtitle": "subtitle_bottom",
            "karaoke": "karaoke",
        }
        style = style_map.get(caption_template, "bold_centered")

        # Determine animation.
        animation = "karaoke" if caption_template == "karaoke" else "pop_in"

        # Generate ASS file.
        with tempfile.TemporaryDirectory(prefix="aividio_clip_captions_") as tmp_dir:
            ass_path = Path(tmp_dir) / "clip_captions.ass"
            generate_ass_file(
                words=clip_words,
                output_path=ass_path,
                style=style,
                animation=animation,
            )

            # Burn captions — output replaces the clip.
            captioned_path = clip_path.parent / f"{clip_path.stem}_captioned.mp4"
            burn_captions(clip_path, ass_path, captioned_path)

        # Replace original clip with captioned version.
        if captioned_path.exists():
            clip_path.unlink(missing_ok=True)
            captioned_path.rename(clip_path)

        return clip_path

    # ------------------------------------------------------------------
    # Clip ranking
    # ------------------------------------------------------------------

    def rank_clips(self, clips: list[dict]) -> list[dict]:
        """Re-rank clips based on virality potential.

        Adjusts scores using heuristic factors:
        - Duration sweet spot (21-45s gets a bonus)
        - Strong hooks (starting with a question or bold statement)
        - Self-contained narrative check

        Parameters:
            clips: List of clip dicts with ``start``, ``end``, ``title``,
                ``hook``, ``score``, ``reason`` keys.

        Returns:
            Re-ranked list of clip dicts with adjusted scores.
        """
        if not clips:
            return []

        ranked = []
        for clip in clips:
            score = clip.get("score", 50)
            duration = clip.get("end", 0) - clip.get("start", 0)
            hook = clip.get("hook", "")

            # Duration sweet spot bonus (21-45s).
            if 21 <= duration <= 45:
                score += 10
            elif duration < 10 or duration > 90:
                score -= 10

            # Strong hook bonus.
            hook_lower = hook.lower().strip()
            if hook_lower.startswith(("what if", "did you know", "here's why", "the secret")):
                score += 15
            elif hook_lower.endswith("?"):
                score += 10
            elif any(word in hook_lower for word in ["shocking", "insane", "unbelievable", "secret"]):
                score += 8

            # Clamp score.
            score = max(0, min(100, score))

            ranked.append({**clip, "score": score})

        ranked.sort(key=lambda c: c["score"], reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _copy_video(src: Path, dst: Path) -> None:
        """Copy a video file using ffmpeg stream copy."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            (
                ffmpeg
                .input(str(src))
                .output(str(dst), codec="copy")
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(f"Video copy failed ({src} -> {dst}): {stderr}") from exc


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _format_transcript(word_timestamps: list[dict]) -> str:
    """Format word timestamps into a readable transcript with time markers."""
    lines: list[str] = []
    current_line: list[str] = []
    line_start: float = 0.0

    for w in word_timestamps:
        if not current_line:
            line_start = w["start"]
        current_line.append(w["word"])

        if len(current_line) >= 10 or w["word"].endswith((".", "!", "?")):
            timestamp = f"[{line_start:.1f}s]"
            lines.append(f"{timestamp} {' '.join(current_line)}")
            current_line = []

    if current_line:
        timestamp = f"[{line_start:.1f}s]"
        lines.append(f"{timestamp} {' '.join(current_line)}")

    return "\n".join(lines)


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "_", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:50].strip("_-")
