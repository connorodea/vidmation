"""SilenceRemover — detect and remove dead air and filler words from video.

Uses ffmpeg's ``silencedetect`` filter for silence detection and word-level
timestamps from Whisper for filler-word detection.  Supports three speed
modes (normal, fast, extra_fast) that control minimum silence duration and
how much padding to keep around cuts.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from vidmation.utils.ffmpeg import FFmpegError, get_duration, run_ffmpeg

logger = logging.getLogger(__name__)


class SilenceRemover:
    """Remove silence and filler words from video/audio.

    Detects silent segments using ffmpeg's ``silencedetect`` audio filter
    and identifies filler words from word-level timestamps.  Supports
    combined "smart trim" that removes both in a single pass.

    Modes:
        * ``normal`` — removes pauses >= 800ms, keeps 200ms padding
        * ``fast`` — removes pauses >= 500ms, keeps 100ms padding
        * ``extra_fast`` — removes pauses >= 300ms, keeps 50ms padding
    """

    FILLER_WORDS: list[str] = [
        "um", "uh", "erm", "like", "you know", "basically",
        "actually", "literally", "so", "right", "okay so",
        "i mean", "sort of", "kind of", "well",
    ]

    MODES: dict[str, dict[str, int]] = {
        "normal": {"min_silence_ms": 800, "keep_ms": 200},
        "fast": {"min_silence_ms": 500, "keep_ms": 100},
        "extra_fast": {"min_silence_ms": 300, "keep_ms": 50},
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"vidmation.effects.{self.__class__.__name__}")

    # ------------------------------------------------------------------
    # Silence detection
    # ------------------------------------------------------------------

    def detect_silence(
        self,
        audio_path: Path,
        min_duration_ms: int = 500,
        threshold_db: float = -40.0,
    ) -> list[dict]:
        """Detect silent segments using ffmpeg's ``silencedetect`` filter.

        Parameters:
            audio_path: Path to audio or video file.
            min_duration_ms: Minimum silence duration in milliseconds.
            threshold_db: Volume threshold below which audio is considered silence.

        Returns:
            List of ``{"start": float, "end": float, "duration": float}`` dicts
            representing each silent segment in seconds.

        Raises:
            FileNotFoundError: If *audio_path* does not exist.
            FFmpegError: On ffmpeg failure.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        min_duration_s = min_duration_ms / 1000.0

        self.logger.info(
            "Detecting silence in %s (threshold=%.0fdB, min_duration=%dms)",
            audio_path.name,
            threshold_db,
            min_duration_ms,
        )

        # Run ffmpeg with silencedetect filter; capture stderr which has the output.
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-af", f"silencedetect=n={threshold_db}dB:d={min_duration_s}",
            "-f", "null",
            "-",
        ]

        # silencedetect outputs to stderr even on success; we need to capture
        # stderr regardless of exit code.
        import subprocess

        self.logger.debug("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=300,
            check=False,
        )
        stderr_text = result.stderr.decode(errors="replace")

        # Parse silence start/end pairs from ffmpeg stderr.
        silences = self._parse_silencedetect_output(stderr_text)

        self.logger.info("Detected %d silent segments", len(silences))
        return silences

    @staticmethod
    def _parse_silencedetect_output(stderr: str) -> list[dict]:
        """Parse ffmpeg silencedetect output from stderr.

        Expected lines look like::

            [silencedetect @ ...] silence_start: 1.234
            [silencedetect @ ...] silence_end: 2.567 | silence_duration: 1.333
        """
        start_pattern = re.compile(r"silence_start:\s*([\d.]+)")
        end_pattern = re.compile(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)")

        starts: list[float] = []
        silences: list[dict] = []

        for line in stderr.splitlines():
            start_match = start_pattern.search(line)
            if start_match:
                starts.append(float(start_match.group(1)))
                continue

            end_match = end_pattern.search(line)
            if end_match and starts:
                start_time = starts.pop(0)
                end_time = float(end_match.group(1))
                duration = float(end_match.group(2))
                silences.append({
                    "start": round(start_time, 3),
                    "end": round(end_time, 3),
                    "duration": round(duration, 3),
                })

        return silences

    # ------------------------------------------------------------------
    # Filler-word detection
    # ------------------------------------------------------------------

    def detect_filler_words(self, word_timestamps: list[dict]) -> list[dict]:
        """Find filler words in a transcript.

        Detects single-word fillers by exact match and multi-word fillers
        (e.g. "you know", "okay so") by scanning consecutive word pairs.

        Parameters:
            word_timestamps: List of ``{"word": str, "start": float, "end": float}``
                dicts from Whisper transcription.

        Returns:
            List of ``{"word": str, "start": float, "end": float}`` dicts for
            each detected filler.
        """
        if not word_timestamps:
            return []

        self.logger.info("Scanning %d words for filler words", len(word_timestamps))

        # Split fillers into single-word and multi-word groups.
        single_fillers = set()
        multi_fillers: list[list[str]] = []
        for filler in self.FILLER_WORDS:
            parts = filler.split()
            if len(parts) == 1:
                single_fillers.add(parts[0])
            else:
                multi_fillers.append(parts)

        found: list[dict] = []

        # Single-word filler detection.
        for w in word_timestamps:
            cleaned = w["word"].lower().strip(".,!?;:'\"")
            if cleaned in single_fillers:
                found.append({
                    "word": cleaned,
                    "start": w["start"],
                    "end": w["end"],
                })

        # Multi-word filler detection.
        for filler_parts in multi_fillers:
            n = len(filler_parts)
            for i in range(len(word_timestamps) - n + 1):
                window = word_timestamps[i : i + n]
                window_words = [ww["word"].lower().strip(".,!?;:'\"") for ww in window]
                if window_words == filler_parts:
                    found.append({
                        "word": " ".join(filler_parts),
                        "start": window[0]["start"],
                        "end": window[-1]["end"],
                    })

        # Sort by start time and remove overlaps.
        found.sort(key=lambda f: f["start"])
        deduped: list[dict] = []
        for item in found:
            if deduped and item["start"] < deduped[-1]["end"]:
                # Overlap — keep the longer one.
                if item["end"] - item["start"] > deduped[-1]["end"] - deduped[-1]["start"]:
                    deduped[-1] = item
            else:
                deduped.append(item)

        self.logger.info("Found %d filler words", len(deduped))
        return deduped

    # ------------------------------------------------------------------
    # Silence removal
    # ------------------------------------------------------------------

    def remove_silence(
        self,
        video_path: Path,
        mode: str = "normal",
        output_path: Path | None = None,
    ) -> Path:
        """Remove silent segments from video.

        Detects silence, builds a cut list of non-silent segments, and
        concatenates them using ffmpeg's concat demuxer.

        Parameters:
            video_path: Input video/audio file.
            mode: One of ``"normal"``, ``"fast"``, ``"extra_fast"``.
            output_path: Output path (auto-generated if ``None``).

        Returns:
            Path to the trimmed output file.

        Raises:
            ValueError: If *mode* is not recognised.
            FileNotFoundError: If *video_path* does not exist.
            FFmpegError: On any ffmpeg failure.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if mode not in self.MODES:
            raise ValueError(f"Unknown mode '{mode}'. Valid modes: {list(self.MODES)}")

        mode_cfg = self.MODES[mode]
        min_silence_ms = mode_cfg["min_silence_ms"]
        keep_ms = mode_cfg["keep_ms"]

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_trimmed{video_path.suffix}"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "Removing silence from %s (mode=%s, min_silence=%dms, keep=%dms)",
            video_path.name,
            mode,
            min_silence_ms,
            keep_ms,
        )

        # 1. Detect silence.
        silences = self.detect_silence(video_path, min_duration_ms=min_silence_ms)

        if not silences:
            self.logger.info("No silence detected; copying input to output")
            self._copy_file(video_path, output_path)
            return output_path

        # 2. Build keep segments (inverse of silence segments with padding).
        total_duration = get_duration(video_path)
        keep_segments = self._build_keep_segments(silences, total_duration, keep_ms / 1000.0)

        if not keep_segments:
            self.logger.warning("All content would be removed; copying input unchanged")
            self._copy_file(video_path, output_path)
            return output_path

        # 3. Concatenate keep segments.
        self._concat_segments(video_path, keep_segments, output_path)

        removed_seconds = total_duration - sum(s["end"] - s["start"] for s in keep_segments)
        self.logger.info(
            "Silence removed: %.1fs cut from %.1fs total -> %s",
            removed_seconds,
            total_duration,
            output_path,
        )
        return output_path

    # ------------------------------------------------------------------
    # Filler removal
    # ------------------------------------------------------------------

    def remove_fillers(
        self,
        video_path: Path,
        word_timestamps: list[dict],
        output_path: Path | None = None,
    ) -> Path:
        """Remove filler words from video.

        Detects fillers in the transcript, builds a cut list that excludes
        the filler-word time ranges, and concatenates the remaining segments.

        Parameters:
            video_path: Input video file.
            word_timestamps: Word-level timestamps from transcription.
            output_path: Output path (auto-generated if ``None``).

        Returns:
            Path to the output file with fillers removed.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_no_fillers{video_path.suffix}"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fillers = self.detect_filler_words(word_timestamps)

        if not fillers:
            self.logger.info("No filler words detected; copying input")
            self._copy_file(video_path, output_path)
            return output_path

        total_duration = get_duration(video_path)

        # Convert filler positions to silence-like dicts for reuse.
        filler_segments = [
            {"start": f["start"], "end": f["end"], "duration": f["end"] - f["start"]}
            for f in fillers
        ]

        keep_segments = self._build_keep_segments(filler_segments, total_duration, padding=0.02)

        if not keep_segments:
            self.logger.warning("All content would be removed; copying input unchanged")
            self._copy_file(video_path, output_path)
            return output_path

        self._concat_segments(video_path, keep_segments, output_path)

        removed_seconds = total_duration - sum(s["end"] - s["start"] for s in keep_segments)
        self.logger.info(
            "Fillers removed: %d fillers (%.1fs) -> %s",
            len(fillers),
            removed_seconds,
            output_path,
        )
        return output_path

    # ------------------------------------------------------------------
    # Smart trim (combined)
    # ------------------------------------------------------------------

    def smart_trim(
        self,
        video_path: Path,
        word_timestamps: list[dict],
        mode: str = "normal",
        remove_fillers: bool = True,
        output_path: Path | None = None,
    ) -> tuple[Path, dict]:
        """Combined silence + filler removal.

        Detects both silence and filler words, merges the cut regions,
        and produces a single trimmed output.

        Parameters:
            video_path: Input video file.
            word_timestamps: Word-level timestamps from transcription.
            mode: Silence removal mode (``"normal"``, ``"fast"``, ``"extra_fast"``).
            remove_fillers: Whether to also remove filler words.
            output_path: Output path (auto-generated if ``None``).

        Returns:
            Tuple of ``(output_path, stats)`` where stats contains
            ``removed_seconds``, ``segments_cut``, ``fillers_removed``,
            ``original_duration``, and ``new_duration``.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if mode not in self.MODES:
            raise ValueError(f"Unknown mode '{mode}'. Valid modes: {list(self.MODES)}")

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_smart_trimmed{video_path.suffix}"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mode_cfg = self.MODES[mode]
        min_silence_ms = mode_cfg["min_silence_ms"]
        keep_ms = mode_cfg["keep_ms"]

        self.logger.info(
            "Smart trim: %s (mode=%s, fillers=%s)",
            video_path.name,
            mode,
            remove_fillers,
        )

        # 1. Detect silence.
        silences = self.detect_silence(video_path, min_duration_ms=min_silence_ms)

        # 2. Detect fillers.
        fillers: list[dict] = []
        if remove_fillers and word_timestamps:
            fillers = self.detect_filler_words(word_timestamps)

        # 3. Merge all cut regions.
        cut_regions: list[dict] = []
        for s in silences:
            cut_regions.append({"start": s["start"], "end": s["end"]})
        for f in fillers:
            cut_regions.append({"start": f["start"], "end": f["end"]})

        if not cut_regions:
            self.logger.info("Nothing to trim; copying input")
            self._copy_file(video_path, output_path)
            original_dur = get_duration(video_path)
            return output_path, {
                "removed_seconds": 0.0,
                "segments_cut": 0,
                "fillers_removed": 0,
                "original_duration": original_dur,
                "new_duration": original_dur,
            }

        # Sort and merge overlapping cut regions.
        cut_regions.sort(key=lambda r: r["start"])
        merged_cuts: list[dict] = [cut_regions[0]]
        for region in cut_regions[1:]:
            prev = merged_cuts[-1]
            if region["start"] <= prev["end"] + 0.01:
                prev["end"] = max(prev["end"], region["end"])
            else:
                merged_cuts.append(region)

        # 4. Build keep segments.
        total_duration = get_duration(video_path)
        keep_segments = self._build_keep_segments(
            merged_cuts, total_duration, keep_ms / 1000.0,
        )

        if not keep_segments:
            self.logger.warning("Smart trim would remove everything; copying input unchanged")
            self._copy_file(video_path, output_path)
            return output_path, {
                "removed_seconds": 0.0,
                "segments_cut": 0,
                "fillers_removed": len(fillers),
                "original_duration": total_duration,
                "new_duration": total_duration,
            }

        # 5. Concatenate.
        self._concat_segments(video_path, keep_segments, output_path)

        new_duration = sum(s["end"] - s["start"] for s in keep_segments)
        removed_seconds = total_duration - new_duration

        stats = {
            "removed_seconds": round(removed_seconds, 2),
            "segments_cut": len(merged_cuts),
            "fillers_removed": len(fillers),
            "original_duration": round(total_duration, 2),
            "new_duration": round(new_duration, 2),
        }

        self.logger.info(
            "Smart trim complete: removed %.1fs (%d cuts, %d fillers) -> %s",
            removed_seconds,
            len(merged_cuts),
            len(fillers),
            output_path,
        )
        return output_path, stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_keep_segments(
        cut_regions: list[dict],
        total_duration: float,
        padding: float,
    ) -> list[dict]:
        """Invert cut regions into keep segments with optional padding.

        Padding is added around each cut boundary so transitions sound
        natural rather than abrupt.

        Parameters:
            cut_regions: Sorted list of ``{"start": float, "end": float}`` dicts.
            total_duration: Total duration of the source media.
            padding: Seconds of padding to keep around each cut.

        Returns:
            List of ``{"start": float, "end": float}`` dicts for segments to keep.
        """
        keep: list[dict] = []
        cursor = 0.0

        for region in cut_regions:
            # Add padding: shrink the cut region slightly.
            cut_start = region["start"] + padding
            cut_end = region["end"] - padding

            if cut_start < cut_end and cursor < cut_start:
                keep.append({"start": cursor, "end": cut_start})

            cursor = max(cursor, cut_end)

        # Trailing segment.
        if cursor < total_duration - 0.01:
            keep.append({"start": cursor, "end": total_duration})

        # Filter out very short segments (< 50ms).
        return [seg for seg in keep if seg["end"] - seg["start"] >= 0.05]

    def _concat_segments(
        self,
        source_path: Path,
        segments: list[dict],
        output_path: Path,
    ) -> None:
        """Extract and concatenate non-contiguous segments from a video.

        Uses ffmpeg's concat filter with trim for each segment to avoid
        file-level re-demuxing issues.

        Parameters:
            source_path: Source video/audio file.
            segments: List of ``{"start": float, "end": float}`` dicts.
            output_path: Where to write the concatenated output.

        Raises:
            FFmpegError: On ffmpeg failure.
        """
        if not segments:
            raise FFmpegError("No segments to concatenate")

        # For many segments, use the concat filter approach.
        # Build filter_complex with trim for each segment.
        filter_parts: list[str] = []
        stream_labels: list[str] = []

        for i, seg in enumerate(segments):
            v_label = f"[v{i}]"
            a_label = f"[a{i}]"
            filter_parts.append(
                f"[0:v]trim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"setpts=PTS-STARTPTS{v_label}"
            )
            filter_parts.append(
                f"[0:a]atrim=start={seg['start']:.3f}:end={seg['end']:.3f},"
                f"asetpts=PTS-STARTPTS{a_label}"
            )
            stream_labels.append(f"{v_label}{a_label}")

        concat_input = "".join(stream_labels)
        n = len(segments)
        filter_parts.append(
            f"{concat_input}concat=n={n}:v=1:a=1[outv][outa]"
        )

        filtergraph = ";\n".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(source_path),
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
        ]

        run_ffmpeg(cmd, desc="SilenceRemover concat_segments", timeout=600)

    @staticmethod
    def _copy_file(src: Path, dst: Path) -> None:
        """Copy a media file via ffmpeg stream copy."""
        import ffmpeg as ffmpeg_lib

        try:
            (
                ffmpeg_lib
                .input(str(src))
                .output(str(dst), codec="copy")
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg_lib.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(f"File copy failed ({src} -> {dst}): {stderr}") from exc
