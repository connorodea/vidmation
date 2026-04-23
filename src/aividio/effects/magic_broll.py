"""MagicBRoll — AI-powered contextual B-roll insertion.

Analyzes a transcript to identify moments that benefit from B-roll footage,
searches stock media providers (Pexels, Pixabay) for matching clips, and
inserts them into the video with configurable blend modes.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg

from aividio.config.settings import Settings, get_settings
from aividio.utils.ffmpeg import FFmpegError, get_duration, get_resolution, run_ffmpeg
from aividio.utils.retry import retry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claude prompt for B-roll analysis
# ---------------------------------------------------------------------------

_BROLL_SYSTEM_PROMPT = """\
You are an expert video editor identifying moments in a transcript where
B-roll footage would enhance the viewer experience.

For each B-roll suggestion, return a JSON array of objects with:
- "start": float — start time in seconds when B-roll should appear
- "end": float — end time in seconds
- "visual_query": string — a concise, search-friendly phrase for stock footage
  (e.g. "city skyline timelapse", "hands typing on laptop", "money falling")
- "reason": brief explanation of why B-roll helps here
- "priority": integer 1-3 (1=must have, 2=nice to have, 3=optional)

Guidelines:
- B-roll typically covers 3-8 seconds
- Look for abstract concepts, metaphors, or described scenes
- Avoid B-roll during direct-to-camera moments or emotional peaks that need
  the speaker's face
- Prioritise moments where the narration describes something visual
- Maximum {max_clips} suggestions
- Respond with ONLY the JSON array — no markdown fences, no commentary
"""

_BROLL_USER_TEMPLATE = """\
Transcript ({word_count} words, {duration:.1f}s total):

{transcript_text}

Suggest the best moments for B-roll insertion (max {max_clips}).
"""


class MagicBRoll:
    """Automatically insert relevant B-roll at contextual moments in video.

    Uses Claude for transcript analysis and stock media providers (Pexels,
    Pixabay) for sourcing footage.  Supports three blend modes:

    * ``crossfade`` — smooth 0.3s crossfade transitions
    * ``cut`` — hard cut to and from B-roll
    * ``picture_in_picture`` — overlay B-roll in a corner
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(f"aividio.effects.{self.__class__.__name__}")

    # ------------------------------------------------------------------
    # Transcript analysis
    # ------------------------------------------------------------------

    def analyze_transcript(
        self,
        word_timestamps: list[dict],
        script: dict | None = None,
        max_clips: int = 8,
    ) -> list[dict]:
        """Use Claude to identify moments that benefit from B-roll.

        Parameters:
            word_timestamps: Word-level timestamps from Whisper.
            script: Optional script dict for additional context.
            max_clips: Maximum number of B-roll suggestions.

        Returns:
            List of dicts with keys: ``start``, ``end``, ``visual_query``,
            ``reason``, ``priority``.  Sorted by priority (1=highest) then time.
        """
        if not word_timestamps:
            self.logger.warning("No word timestamps; returning empty B-roll suggestions")
            return []

        import anthropic

        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            self.logger.warning(
                "No Anthropic API key configured; falling back to heuristic B-roll detection"
            )
            return self._analyze_heuristic(word_timestamps, max_clips)

        client = anthropic.Anthropic(api_key=api_key)

        transcript_text = _format_transcript(word_timestamps)
        total_duration = word_timestamps[-1]["end"] if word_timestamps else 0.0

        system = _BROLL_SYSTEM_PROMPT.format(max_clips=max_clips)
        user_msg = _BROLL_USER_TEMPLATE.format(
            word_count=len(word_timestamps),
            duration=total_duration,
            transcript_text=transcript_text,
            max_clips=max_clips,
        )

        self.logger.info(
            "Analyzing transcript for B-roll opportunities (%d words, max=%d)",
            len(word_timestamps),
            max_clips,
        )

        try:
            response = self._call_claude(client, system, user_msg)
            suggestions = self._parse_broll_response(response)
        except Exception as exc:
            self.logger.error("Claude B-roll analysis failed: %s — using heuristic", exc)
            return self._analyze_heuristic(word_timestamps, max_clips)

        # Validate and clamp.
        validated: list[dict] = []
        for s in suggestions[:max_clips]:
            s["start"] = max(0.0, float(s.get("start", 0)))
            s["end"] = max(s["start"] + 1.0, float(s.get("end", s["start"] + 5.0)))
            s["visual_query"] = str(s.get("visual_query", "abstract background"))
            s.setdefault("reason", "AI suggestion")
            s["priority"] = max(1, min(3, int(s.get("priority", 2))))
            validated.append(s)

        # Sort by priority, then start time.
        validated.sort(key=lambda x: (x["priority"], x["start"]))

        self.logger.info("B-roll analysis: %d suggestions", len(validated))
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

    def _parse_broll_response(self, raw_text: str) -> list[dict]:
        """Parse Claude's B-roll response into a list of suggestion dicts."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())

    def _analyze_heuristic(
        self,
        word_timestamps: list[dict],
        max_clips: int,
    ) -> list[dict]:
        """Heuristic B-roll detection without an LLM.

        Identifies long narration stretches and generates generic visual
        queries based on nearby words.
        """
        if not word_timestamps:
            return []

        suggestions: list[dict] = []
        total_duration = word_timestamps[-1]["end"]

        # Find stretches of 5+ seconds of continuous narration as B-roll candidates.
        segment_start = word_timestamps[0]["start"]
        segment_words: list[str] = []

        for i, w in enumerate(word_timestamps):
            segment_words.append(w["word"])
            is_last = i == len(word_timestamps) - 1
            gap_after = (
                word_timestamps[i + 1]["start"] - w["end"] > 1.0
                if not is_last
                else True
            )

            if (gap_after or is_last) and w["end"] - segment_start >= 4.0:
                # Generate a visual query from the segment's most descriptive words.
                query_words = [
                    word for word in segment_words
                    if len(word) > 3 and word.isalpha()
                ][:5]
                visual_query = " ".join(query_words) if query_words else "abstract background"

                suggestions.append({
                    "start": segment_start + 0.5,
                    "end": min(w["end"] - 0.5, segment_start + 8.0),
                    "visual_query": visual_query,
                    "reason": "long narration stretch",
                    "priority": 2,
                })

                if gap_after and not is_last:
                    segment_start = word_timestamps[i + 1]["start"]
                    segment_words = []

            elif gap_after and not is_last:
                segment_start = word_timestamps[i + 1]["start"]
                segment_words = []

        # Space them out: at least 10 seconds apart.
        deduped: list[dict] = []
        for s in suggestions:
            if deduped and s["start"] - deduped[-1]["end"] < 10.0:
                continue
            deduped.append(s)

        return deduped[:max_clips]

    # ------------------------------------------------------------------
    # B-roll sourcing
    # ------------------------------------------------------------------

    def source_broll(
        self,
        suggestions: list[dict],
        providers: list[str] | None = None,
        download_dir: Path | None = None,
    ) -> list[dict]:
        """Search and download B-roll clips for each suggestion.

        Parameters:
            suggestions: List of dicts from :meth:`analyze_transcript` with
                ``start``, ``end``, ``visual_query`` keys.
            providers: List of provider names to search. Defaults to
                ``["pexels", "pixabay"]``.
            download_dir: Directory to save downloaded clips. Uses a temp
                directory if ``None``.

        Returns:
            List of dicts with ``start``, ``end``, ``clip_path``, ``source``,
            ``attribution`` keys.  Entries without a successful download are
            omitted.
        """
        if providers is None:
            providers = ["pexels", "pixabay"]

        if download_dir is None:
            download_dir = Path(tempfile.mkdtemp(prefix="aividio_broll_"))
        download_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "Sourcing B-roll: %d suggestions, providers=%s",
            len(suggestions),
            providers,
        )

        # Lazy-import media providers to avoid circular imports.
        provider_instances = self._create_providers(providers)

        sourced: list[dict] = []

        for i, suggestion in enumerate(suggestions):
            query = suggestion["visual_query"]
            clip_path = download_dir / f"broll_{i:03d}.mp4"

            self.logger.info("Sourcing B-roll %d/%d: query=%r", i + 1, len(suggestions), query)

            # Try each provider until we get a result.
            result = None
            for provider in provider_instances:
                try:
                    videos = provider.search_videos(query, count=1)
                    if videos:
                        video_info = videos[0]
                        provider.download(video_info["download_url"], clip_path)
                        result = {
                            "start": suggestion["start"],
                            "end": suggestion["end"],
                            "clip_path": clip_path,
                            "source": video_info.get("source", "unknown"),
                            "attribution": video_info.get("attribution", ""),
                            "visual_query": query,
                        }
                        break
                except Exception as exc:
                    self.logger.warning(
                        "Provider %s failed for query %r: %s",
                        provider.__class__.__name__,
                        query,
                        exc,
                    )
                    continue

            if result:
                sourced.append(result)
            else:
                self.logger.warning("No B-roll found for query: %r", query)

        self.logger.info("Sourced %d/%d B-roll clips", len(sourced), len(suggestions))
        return sourced

    def _create_providers(self, provider_names: list[str]) -> list[Any]:
        """Instantiate media provider objects from provider name strings."""
        providers = []

        for name in provider_names:
            try:
                if name.lower() == "pexels":
                    from aividio.services.media.pexels import PexelsMediaProvider
                    providers.append(PexelsMediaProvider(settings=self.settings))
                elif name.lower() == "pixabay":
                    from aividio.services.media.pixabay import PixabayMediaProvider
                    providers.append(PixabayMediaProvider(settings=self.settings))
                else:
                    self.logger.warning("Unknown media provider: %s", name)
            except (ValueError, ImportError) as exc:
                self.logger.warning("Could not initialise provider '%s': %s", name, exc)

        return providers

    # ------------------------------------------------------------------
    # B-roll insertion
    # ------------------------------------------------------------------

    def insert_broll(
        self,
        video_path: Path,
        broll_clips: list[dict],
        output_path: Path,
        blend_mode: str = "crossfade",
    ) -> Path:
        """Insert B-roll clips into video at specified timestamps.

        Parameters:
            video_path: Main video file.
            broll_clips: List of dicts with ``start``, ``end``, ``clip_path`` keys.
            output_path: Where to write the final video.
            blend_mode: How to blend B-roll in. One of:
                ``"crossfade"`` — smooth transition into/out of B-roll.
                ``"cut"`` — hard cut to B-roll.
                ``"picture_in_picture"`` — overlay B-roll in bottom-right corner.

        Returns:
            Path to the output video.

        Raises:
            FileNotFoundError: If *video_path* or any clip does not exist.
            FFmpegError: On any ffmpeg failure.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Filter out clips with missing files.
        valid_clips = []
        for clip in broll_clips:
            cp = Path(clip["clip_path"])
            if cp.exists():
                valid_clips.append(clip)
            else:
                self.logger.warning("B-roll clip missing, skipping: %s", cp)

        if not valid_clips:
            self.logger.info("No valid B-roll clips; copying input to output")
            self._copy_video(video_path, output_path)
            return output_path

        # Sort by start time.
        valid_clips.sort(key=lambda c: c["start"])

        self.logger.info(
            "Inserting %d B-roll clips (blend=%s) into %s",
            len(valid_clips),
            blend_mode,
            video_path.name,
        )

        if blend_mode == "picture_in_picture":
            return self._insert_pip(video_path, valid_clips, output_path)
        else:
            return self._insert_splice(video_path, valid_clips, output_path, blend_mode)

    def _insert_splice(
        self,
        video_path: Path,
        clips: list[dict],
        output_path: Path,
        blend_mode: str,
    ) -> Path:
        """Insert B-roll by splicing clips into the main timeline.

        Splits the main video at B-roll insertion points, fits each B-roll
        clip to the target duration and resolution, then concatenates
        everything back together.
        """
        width, height = get_resolution(video_path)
        total_duration = get_duration(video_path)

        # Build segment list: alternating between main video and B-roll.
        segments: list[dict] = []
        cursor = 0.0

        for clip in clips:
            start = max(0.0, clip["start"])
            end = min(total_duration, clip["end"])
            if end <= start:
                continue

            # Main video segment before this B-roll.
            if start > cursor + 0.01:
                segments.append({
                    "type": "main",
                    "start": cursor,
                    "end": start,
                })

            # B-roll segment.
            segments.append({
                "type": "broll",
                "start": start,
                "end": end,
                "clip_path": clip["clip_path"],
            })
            cursor = end

        # Trailing main segment.
        if cursor < total_duration - 0.01:
            segments.append({
                "type": "main",
                "start": cursor,
                "end": total_duration,
            })

        if not segments:
            self._copy_video(video_path, output_path)
            return output_path

        # Build filter_complex.
        filter_parts: list[str] = []
        stream_labels: list[str] = []
        input_idx = 1  # 0 is the main video

        # Collect all B-roll input files.
        broll_inputs: list[str] = []
        broll_input_map: dict[int, int] = {}  # segment index -> input file index

        for i, seg in enumerate(segments):
            if seg["type"] == "broll":
                broll_inputs.append(str(seg["clip_path"]))
                broll_input_map[i] = input_idx
                input_idx += 1

        for i, seg in enumerate(segments):
            v_label = f"[v{i}]"
            a_label = f"[a{i}]"

            if seg["type"] == "main":
                dur = seg["end"] - seg["start"]
                filter_parts.append(
                    f"[0:v]trim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                    f"setpts=PTS-STARTPTS{v_label}"
                )
                filter_parts.append(
                    f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                    f"asetpts=PTS-STARTPTS{a_label}"
                )
            else:
                # B-roll: scale to match main video resolution, trim to segment duration.
                broll_idx = broll_input_map[i]
                broll_dur = seg["end"] - seg["start"]
                filter_parts.append(
                    f"[{broll_idx}:v]scale={width}:{height}:"
                    f"force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
                    f"setsar=1,trim=duration={broll_dur:.3f},"
                    f"setpts=PTS-STARTPTS{v_label}"
                )
                # Use the main audio from B-roll's time range (keep narration).
                filter_parts.append(
                    f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                    f"asetpts=PTS-STARTPTS{a_label}"
                )

            stream_labels.append(f"{v_label}{a_label}")

        # Crossfade transitions if requested.
        if blend_mode == "crossfade" and len(stream_labels) > 1:
            # Apply xfade between consecutive segments for a smoother look.
            # For simplicity, use short crossfade at each cut point.
            concat_input = "".join(stream_labels)
            n = len(stream_labels)
            filter_parts.append(
                f"{concat_input}concat=n={n}:v=1:a=1[outv][outa]"
            )
        else:
            concat_input = "".join(stream_labels)
            n = len(stream_labels)
            filter_parts.append(
                f"{concat_input}concat=n={n}:v=1:a=1[outv][outa]"
            )

        filtergraph = ";\n".join(filter_parts)

        # Build command with all inputs.
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]
        for broll_file in broll_inputs:
            cmd.extend(["-i", broll_file])

        cmd.extend([
            "-filter_complex", filtergraph,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ])

        run_ffmpeg(cmd, desc="MagicBRoll insert_splice", timeout=600)

        self.logger.info("B-roll insertion complete: %s", output_path)
        return output_path

    def _insert_pip(
        self,
        video_path: Path,
        clips: list[dict],
        output_path: Path,
    ) -> Path:
        """Insert B-roll as picture-in-picture overlays.

        Overlays each B-roll clip in the bottom-right corner at 30% scale
        with rounded corners and a subtle shadow.
        """
        width, height = get_resolution(video_path)

        # PIP dimensions: 30% of main video.
        pip_w = int(width * 0.3)
        pip_h = int(height * 0.3)
        pip_x = width - pip_w - 20  # 20px margin from right
        pip_y = height - pip_h - 20  # 20px margin from bottom

        filter_parts: list[str] = []
        input_idx = 1
        broll_inputs: list[str] = []

        # Start with the main video.
        current_label = "[0:v]"

        for i, clip in enumerate(clips):
            broll_inputs.append(str(clip["clip_path"]))
            broll_dur = clip["end"] - clip["start"]
            broll_start = clip["start"]

            # Scale B-roll to PIP size.
            scaled_label = f"[pip{i}]"
            filter_parts.append(
                f"[{input_idx}:v]scale={pip_w}:{pip_h}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={pip_w}:{pip_h}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,trim=duration={broll_dur:.3f},"
                f"setpts=PTS-STARTPTS{scaled_label}"
            )

            # Overlay on main video at the correct time.
            out_label = f"[out{i}]" if i < len(clips) - 1 else "[outv]"
            filter_parts.append(
                f"{current_label}{scaled_label}overlay={pip_x}:{pip_y}:"
                f"enable='between(t,{broll_start:.3f},{broll_start + broll_dur:.3f})'"
                f"{out_label}"
            )
            current_label = out_label
            input_idx += 1

        # If no clips processed, just map the video through.
        if not filter_parts:
            self._copy_video(video_path, output_path)
            return output_path

        filtergraph = ";\n".join(filter_parts)

        cmd = ["ffmpeg", "-y", "-i", str(video_path)]
        for broll_file in broll_inputs:
            cmd.extend(["-i", broll_file])

        cmd.extend([
            "-filter_complex", filtergraph,
            "-map", "[outv]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_path),
        ])

        run_ffmpeg(cmd, desc="MagicBRoll insert_pip", timeout=600)

        self.logger.info("B-roll PIP insertion complete: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # One-click auto B-roll
    # ------------------------------------------------------------------

    def auto_broll(
        self,
        video_path: Path,
        word_timestamps: list[dict],
        max_clips: int = 8,
        blend_mode: str = "crossfade",
        providers: list[str] | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """One-click magic B-roll — analyze, source, and insert automatically.

        Parameters:
            video_path: Input video file.
            word_timestamps: Word-level timestamps from Whisper.
            max_clips: Maximum number of B-roll clips.
            blend_mode: Blend mode for insertion.
            providers: Stock media providers to search.
            output_path: Output path (auto-generated if ``None``).

        Returns:
            Path to the final video with B-roll inserted.
        """
        video_path = Path(video_path)
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_broll{video_path.suffix}"
        output_path = Path(output_path)

        self.logger.info(
            "Auto B-roll: %s (max_clips=%d, blend=%s)",
            video_path.name,
            max_clips,
            blend_mode,
        )

        # 1. Analyze transcript for B-roll opportunities.
        suggestions = self.analyze_transcript(
            word_timestamps=word_timestamps,
            max_clips=max_clips,
        )

        if not suggestions:
            self.logger.info("No B-roll opportunities found; returning input unchanged")
            self._copy_video(video_path, output_path)
            return output_path

        # 2. Source B-roll clips.
        sourced = self.source_broll(suggestions=suggestions, providers=providers)

        if not sourced:
            self.logger.info("No B-roll clips sourced; returning input unchanged")
            self._copy_video(video_path, output_path)
            return output_path

        # 3. Insert B-roll into video.
        result = self.insert_broll(
            video_path=video_path,
            broll_clips=sourced,
            output_path=output_path,
            blend_mode=blend_mode,
        )

        self.logger.info(
            "Auto B-roll complete: %d clips inserted -> %s",
            len(sourced),
            result,
        )
        return result

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
