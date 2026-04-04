"""MagicZoom — AI-powered auto-zoom at emphasis points in video.

Analyzes a transcript for key moments (statistics, emotional peaks,
rhetorical questions, transition words) and applies smooth zoom effects
using ffmpeg's zoompan filter with keyframe-based zoom in/out.
"""

from __future__ import annotations

import json
import logging
import math
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg

from vidmation.config.settings import Settings, get_settings
from vidmation.utils.ffmpeg import FFmpegError, get_duration, get_frame_rate, get_resolution, run_ffmpeg
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Easing functions — map t in [0, 1] to an eased value in [0, 1]
# ---------------------------------------------------------------------------

_EASING_FUNCTIONS: dict[str, Any] = {
    "linear": lambda t: t,
    "easeInOutCubic": lambda t: 4 * t * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2,
    "easeOutExpo": lambda t: 1.0 if t == 1.0 else 1.0 - math.pow(2, -10 * t),
    "easeOutQuart": lambda t: 1 - (1 - t) ** 4,
}

# ---------------------------------------------------------------------------
# Claude prompt for emphasis detection
# ---------------------------------------------------------------------------

_EMPHASIS_SYSTEM_PROMPT = """\
You are an expert video editor. Given a transcript with word-level timestamps,
identify the most impactful moments that deserve a zoom effect.

For each moment, return a JSON array of objects with these fields:
- "start": float — start time in seconds
- "end": float — end time in seconds
- "intensity": float between 0.0 and 1.0 — how strong the zoom should be
- "style": one of "smooth", "crash", "expo", "linear"
- "reason": brief explanation (e.g. "key statistic", "emotional peak")

Focus on:
1. Key statistics or numbers being revealed
2. Emotional peaks (excitement, surprise, urgency)
3. Rhetorical questions or question marks
4. List items or numbered points (first item especially)
5. Transition words that signal a twist ("but", "however", "the truth is",
   "here's the thing", "plot twist")
6. Call-to-action moments

Rules:
- Maximum {max_zooms} zoom points
- Space them at least 3 seconds apart
- Prefer moments in the first 30% and last 20% of the video
- Respond with ONLY the JSON array — no markdown fences, no commentary
"""

_EMPHASIS_USER_TEMPLATE = """\
Transcript ({word_count} words, {duration:.1f}s total):

{transcript_text}

Identify the top moments for zoom effects (max {max_zooms}).
"""


class MagicZoom:
    """Analyze transcript and apply zoom effects at key moments.

    Supports four zoom styles with different easing curves:

    * ``smooth`` — gentle ease-in-out cubic, 1.3x scale over 0.8s
    * ``crash`` — aggressive exponential ease-out, 1.5x scale in 0.3s
    * ``expo`` — moderate quartic ease-out, 1.4x scale in 0.5s
    * ``linear`` — constant-speed zoom, 1.2x scale over 0.6s
    """

    ZOOM_STYLES: dict[str, dict[str, Any]] = {
        "smooth": {"ease": "easeInOutCubic", "duration": 0.8, "scale": 1.3},
        "crash": {"ease": "easeOutExpo", "duration": 0.3, "scale": 1.5},
        "expo": {"ease": "easeOutQuart", "duration": 0.5, "scale": 1.4},
        "linear": {"ease": "linear", "duration": 0.6, "scale": 1.2},
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(f"vidmation.effects.{self.__class__.__name__}")

    # ------------------------------------------------------------------
    # Emphasis detection
    # ------------------------------------------------------------------

    def detect_emphasis_points(
        self,
        word_timestamps: list[dict],
        script: dict | None = None,
        max_zooms: int = 10,
    ) -> list[dict]:
        """AI-powered detection of moments that deserve zoom effects.

        Uses Claude to analyze the transcript and identify key moments such as
        statistics, emotional peaks, rhetorical questions, list items, and
        transition words.

        Parameters:
            word_timestamps: List of ``{"word": str, "start": float, "end": float}`` dicts.
            script: Optional script dict for additional context.
            max_zooms: Maximum number of zoom points to return.

        Returns:
            List of zoom-point dicts, each with keys:
            ``start``, ``end``, ``intensity``, ``style``, ``reason``.
        """
        if not word_timestamps:
            self.logger.warning("No word timestamps provided; returning empty zoom points")
            return []

        import anthropic

        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            self.logger.warning(
                "No Anthropic API key configured; falling back to heuristic detection"
            )
            return self._detect_emphasis_heuristic(word_timestamps, max_zooms)

        client = anthropic.Anthropic(api_key=api_key)

        # Build transcript text with timestamps for context.
        transcript_text = self._format_transcript(word_timestamps)
        total_duration = word_timestamps[-1]["end"] if word_timestamps else 0.0

        system = _EMPHASIS_SYSTEM_PROMPT.format(max_zooms=max_zooms)
        user_msg = _EMPHASIS_USER_TEMPLATE.format(
            word_count=len(word_timestamps),
            duration=total_duration,
            transcript_text=transcript_text,
            max_zooms=max_zooms,
        )

        self.logger.info(
            "Detecting emphasis points via Claude (%d words, max_zooms=%d)",
            len(word_timestamps),
            max_zooms,
        )

        try:
            response = self._call_claude(client, system, user_msg)
            points = self._parse_emphasis_response(response)
        except Exception as exc:
            self.logger.error("Claude emphasis detection failed: %s — using heuristic", exc)
            return self._detect_emphasis_heuristic(word_timestamps, max_zooms)

        # Clamp and validate.
        validated: list[dict] = []
        for pt in points[:max_zooms]:
            pt["start"] = max(0.0, float(pt.get("start", 0)))
            pt["end"] = max(pt["start"] + 0.1, float(pt.get("end", pt["start"] + 0.5)))
            pt["intensity"] = max(0.0, min(1.0, float(pt.get("intensity", 0.5))))
            pt["style"] = pt.get("style", "smooth") if pt.get("style") in self.ZOOM_STYLES else "smooth"
            pt.setdefault("reason", "detected by AI")
            validated.append(pt)

        self.logger.info("Detected %d emphasis points", len(validated))
        return validated

    @retry(max_attempts=2, base_delay=2.0, exceptions=(Exception,))
    def _call_claude(
        self,
        client: Any,
        system: str,
        user_msg: str,
    ) -> str:
        """Call Claude API and return the raw response text."""
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()

    def _parse_emphasis_response(self, raw_text: str) -> list[dict]:
        """Parse Claude's response into a list of emphasis-point dicts."""
        # Strip markdown fences.
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        return json.loads(text)

    def _detect_emphasis_heuristic(
        self,
        word_timestamps: list[dict],
        max_zooms: int,
    ) -> list[dict]:
        """Fallback heuristic emphasis detection without an LLM.

        Looks for numbers/statistics, question marks, transition words,
        and periodic emphasis based on video length.
        """
        transition_words = {
            "but", "however", "actually", "surprisingly", "importantly",
            "secret", "truth", "thing", "twist", "meanwhile", "suddenly",
            "instead", "finally", "first", "second", "third",
        }
        question_words = {"what", "why", "how", "when", "where", "who", "which"}
        emphasis_words = {
            "amazing", "incredible", "shocking", "insane", "crazy",
            "million", "billion", "thousand", "percent", "guarantee",
        }

        candidates: list[dict] = []
        total_duration = word_timestamps[-1]["end"] if word_timestamps else 0.0

        for i, w in enumerate(word_timestamps):
            word_lower = w["word"].lower().strip(".,!?;:")
            reason = None
            intensity = 0.5

            # Number/statistic detection.
            if any(ch.isdigit() for ch in w["word"]):
                reason = "statistic or number"
                intensity = 0.7

            # Question mark (rhetorical question).
            elif w["word"].endswith("?"):
                reason = "rhetorical question"
                intensity = 0.6

            # Transition words.
            elif word_lower in transition_words:
                reason = f"transition word: {word_lower}"
                intensity = 0.65

            # Emphasis words.
            elif word_lower in emphasis_words:
                reason = f"emphasis word: {word_lower}"
                intensity = 0.75

            # Question starters.
            elif word_lower in question_words and i > 0:
                prev_word = word_timestamps[i - 1]["word"]
                if prev_word.endswith((".", "!", "?", ",")):
                    reason = "question opening"
                    intensity = 0.55

            if reason:
                candidates.append({
                    "start": w["start"],
                    "end": w["end"],
                    "intensity": intensity,
                    "style": "smooth",
                    "reason": reason,
                })

        # Deduplicate (keep highest intensity within 3s windows).
        if not candidates:
            # If nothing was found, add periodic zooms.
            interval = max(5.0, total_duration / max(1, max_zooms))
            for i in range(min(max_zooms, max(1, int(total_duration / interval)))):
                t = interval * (i + 0.5)
                if t < total_duration:
                    candidates.append({
                        "start": t,
                        "end": t + 0.5,
                        "intensity": 0.4,
                        "style": "smooth",
                        "reason": "periodic emphasis",
                    })

        # Sort by time and deduplicate within 3-second windows.
        candidates.sort(key=lambda c: c["start"])
        deduped: list[dict] = []
        for cand in candidates:
            if deduped and cand["start"] - deduped[-1]["start"] < 3.0:
                # Keep the higher-intensity one.
                if cand["intensity"] > deduped[-1]["intensity"]:
                    deduped[-1] = cand
            else:
                deduped.append(cand)

        return deduped[:max_zooms]

    # ------------------------------------------------------------------
    # Zoom application
    # ------------------------------------------------------------------

    def apply_zooms(
        self,
        video_path: Path,
        zoom_points: list[dict],
        output_path: Path,
    ) -> Path:
        """Apply zoom effects to video at specified points.

        Uses ffmpeg with a complex filter graph that applies zoompan for each
        zoom point and passes through the unzoomed segments unchanged.

        Parameters:
            video_path: Input video file.
            zoom_points: List of dicts with ``start``, ``end``, ``intensity``,
                ``style`` keys.
            output_path: Where to write the zoomed video.

        Returns:
            Path to the output video.

        Raises:
            FileNotFoundError: If *video_path* does not exist.
            FFmpegError: On any ffmpeg failure.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not zoom_points:
            self.logger.info("No zoom points; copying input to output")
            self._copy_video(video_path, output_path)
            return output_path

        width, height = get_resolution(video_path)
        fps = get_frame_rate(video_path)
        duration = get_duration(video_path)

        # Sort zoom points by start time.
        zoom_points = sorted(zoom_points, key=lambda z: z["start"])

        # Build the complex filtergraph.
        # Strategy: split the video into segments, apply zoompan to zoom segments,
        # then concatenate everything back together.
        filter_parts, segment_labels = self._build_zoom_filtergraph(
            zoom_points, duration, width, height, fps,
        )

        if not segment_labels:
            self.logger.info("No valid zoom segments generated; copying input")
            self._copy_video(video_path, output_path)
            return output_path

        # Build the concat at the end.
        concat_inputs = "".join(segment_labels)
        n_segments = len(segment_labels)
        filter_parts.append(
            f"{concat_inputs}concat=n={n_segments}:v=1:a=0[outv]"
        )

        filtergraph = ";\n".join(filter_parts)

        self.logger.info(
            "Applying %d zoom effects to %s (%.1fs, %dx%d)",
            len(zoom_points),
            video_path.name,
            duration,
            width,
            height,
        )
        self.logger.debug("Zoom filtergraph:\n%s", filtergraph)

        # Run ffmpeg with the complex filter.
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-filter_complex", filtergraph,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_path),
        ]

        run_ffmpeg(cmd, desc="MagicZoom apply_zooms", timeout=600)

        self.logger.info("Zoom effects applied: %s", output_path)
        return output_path

    def _build_zoom_filtergraph(
        self,
        zoom_points: list[dict],
        duration: float,
        width: int,
        height: int,
        fps: float,
    ) -> tuple[list[str], list[str]]:
        """Build ffmpeg filter_complex parts for zoom segments.

        Returns:
            Tuple of (filter_parts, segment_labels) where segment_labels are
            ffmpeg stream labels like ``[seg0]``, ``[zoom0]``, etc.
        """
        filter_parts: list[str] = []
        segment_labels: list[str] = []
        seg_idx = 0

        cursor = 0.0

        for i, zp in enumerate(zoom_points):
            start = max(0.0, zp["start"])
            end = min(duration, zp["end"])
            if end <= start:
                continue

            style_name = zp.get("style", "smooth")
            style = self.ZOOM_STYLES.get(style_name, self.ZOOM_STYLES["smooth"])
            intensity = zp.get("intensity", 0.5)

            # Calculate actual zoom scale based on intensity.
            max_scale = style["scale"]
            scale = 1.0 + (max_scale - 1.0) * intensity
            zoom_duration = style["duration"]

            # Pre-zoom gap segment (if any).
            if start > cursor + 0.01:
                gap_start = cursor
                gap_end = start
                label = f"[seg{seg_idx}]"
                filter_parts.append(
                    f"[0:v]trim=start={gap_start:.3f}:end={gap_end:.3f},"
                    f"setpts=PTS-STARTPTS{label}"
                )
                segment_labels.append(label)
                seg_idx += 1

            # Zoom segment: use zoompan with computed expressions.
            zoom_frames = int(zoom_duration * fps)
            total_segment_frames = int((end - start) * fps)

            # Build zoom expression: zoom in for zoom_frames, hold, zoom out for zoom_frames.
            # For the zoompan d parameter we use total_segment_frames.
            zoom_in_end = min(zoom_frames, total_segment_frames // 2)
            hold_end = max(zoom_in_end, total_segment_frames - zoom_frames)
            zoom_out_start = hold_end

            # zoompan z expression using conditional segments.
            # Zoom in: linearly interpolate from 1.0 to scale.
            # Hold: maintain scale.
            # Zoom out: linearly interpolate from scale back to 1.0.
            z_expr = (
                f"if(lt(on,{zoom_in_end}),"
                f"1+({scale - 1:.4f})*on/{max(1, zoom_in_end)},"
                f"if(lt(on,{zoom_out_start}),"
                f"{scale:.4f},"
                f"{scale:.4f}-({scale - 1:.4f})*(on-{zoom_out_start})/{max(1, total_segment_frames - zoom_out_start)}))"
            )

            # Center the zoom.
            x_expr = f"iw/2-(iw/zoom/2)"
            y_expr = f"ih/2-(ih/zoom/2)"

            label = f"[zoom{i}]"
            filter_parts.append(
                f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS,"
                f"scale={width * 2}:{height * 2},"
                f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
                f"d={total_segment_frames}:s={width}x{height}:fps={fps},"
                f"setsar=1{label}"
            )
            segment_labels.append(label)
            seg_idx += 1

            cursor = end

        # Trailing gap after last zoom.
        if cursor < duration - 0.01:
            label = f"[seg{seg_idx}]"
            filter_parts.append(
                f"[0:v]trim=start={cursor:.3f}:end={duration:.3f},"
                f"setpts=PTS-STARTPTS{label}"
            )
            segment_labels.append(label)

        return filter_parts, segment_labels

    # ------------------------------------------------------------------
    # One-click auto-zoom
    # ------------------------------------------------------------------

    def auto_zoom(
        self,
        video_path: Path,
        word_timestamps: list[dict],
        style: str = "smooth",
        max_zooms: int = 10,
        output_path: Path | None = None,
    ) -> Path:
        """One-click magic zoom — detect emphasis points and apply automatically.

        Parameters:
            video_path: Input video file.
            word_timestamps: Word-level timestamps from Whisper.
            style: Default zoom style for detected points.
            max_zooms: Maximum number of zoom effects.
            output_path: Output path (auto-generated if ``None``).

        Returns:
            Path to the zoomed video.
        """
        video_path = Path(video_path)
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_zoomed{video_path.suffix}"
        output_path = Path(output_path)

        self.logger.info("Auto-zoom starting: %s (style=%s, max=%d)", video_path.name, style, max_zooms)

        # 1. Detect emphasis points.
        zoom_points = self.detect_emphasis_points(
            word_timestamps=word_timestamps,
            max_zooms=max_zooms,
        )

        # Override style if user specified one.
        if style in self.ZOOM_STYLES:
            for pt in zoom_points:
                pt["style"] = style

        # 2. Apply zoom effects.
        result = self.apply_zooms(video_path, zoom_points, output_path)

        self.logger.info(
            "Auto-zoom complete: %d effects applied -> %s",
            len(zoom_points),
            result,
        )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
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

    @staticmethod
    def _copy_video(src: Path, dst: Path) -> None:
        """Copy a video file using ffmpeg stream copy."""
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
