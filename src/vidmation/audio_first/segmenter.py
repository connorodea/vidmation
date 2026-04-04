"""Audio segmenter — detect natural section breaks in audio files.

Analyzes audio for:
- Silence gaps (natural section boundaries)
- Topic changes via transcript analysis
- Energy/pace changes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from vidmation.config.settings import Settings, get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """A detected segment within an audio file."""

    start_seconds: float
    end_seconds: float
    text: str = ""
    topic: str = ""
    energy_level: str = "medium"  # "low", "medium", "high"
    is_silence: bool = False
    confidence: float = 1.0

    @property
    def duration_seconds(self) -> float:
        """Duration of this segment in seconds."""
        return self.end_seconds - self.start_seconds


@dataclass
class SegmentationResult:
    """Complete segmentation analysis of an audio file."""

    segments: list[AudioSegment] = field(default_factory=list)
    silence_gaps: list[tuple[float, float]] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    speech_ratio: float = 0.0  # Ratio of speech to total duration.
    average_segment_duration: float = 0.0


class AudioSegmenter:
    """Analyzes audio for natural section breaks.

    Detection strategies:
    1. **Silence gaps**: Detect periods of silence that indicate natural
       pauses or topic transitions. Uses amplitude thresholding.
    2. **Topic changes**: Analyze transcript text for semantic shifts
       using word-level timestamps from Whisper.
    3. **Energy changes**: Detect shifts in speaking pace and volume
       that often correspond to topic transitions.
    """

    # Default parameters for silence detection.
    DEFAULT_SILENCE_THRESHOLD_DB: float = -40.0
    DEFAULT_MIN_SILENCE_DURATION: float = 0.5  # seconds
    DEFAULT_MIN_SEGMENT_DURATION: float = 10.0  # seconds

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger("vidmation.audio_first.AudioSegmenter")

    # ------------------------------------------------------------------
    # Silence detection
    # ------------------------------------------------------------------

    def detect_silence_gaps(
        self,
        audio_path: Path,
        silence_threshold_db: float | None = None,
        min_silence_duration: float | None = None,
        min_segment_duration: float | None = None,
    ) -> list[AudioSegment]:
        """Detect silence gaps in audio and return speech segments.

        Uses pydub for audio analysis.  Falls back to a simple
        duration-based segmentation if pydub is not available.

        Args:
            audio_path: Path to the audio file.
            silence_threshold_db: Volume threshold for silence detection
                (default: -40 dB).
            min_silence_duration: Minimum silence duration to count as a
                gap (default: 0.5 seconds).
            min_segment_duration: Minimum segment duration — very short
                segments are merged with neighbors (default: 10 seconds).

        Returns:
            List of :class:`AudioSegment` objects representing speech regions.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        threshold = silence_threshold_db or self.DEFAULT_SILENCE_THRESHOLD_DB
        min_silence = min_silence_duration or self.DEFAULT_MIN_SILENCE_DURATION
        min_segment = min_segment_duration or self.DEFAULT_MIN_SEGMENT_DURATION

        try:
            return self._detect_with_pydub(
                audio_path, threshold, min_silence, min_segment
            )
        except ImportError:
            self.logger.warning(
                "pydub not available — falling back to duration-based segmentation. "
                "Install pydub for better results: pip install pydub"
            )
            return self._fallback_segmentation(audio_path, min_segment)

    def _detect_with_pydub(
        self,
        audio_path: Path,
        threshold_db: float,
        min_silence_ms: float,
        min_segment: float,
    ) -> list[AudioSegment]:
        """Detect silence gaps using pydub's silence detection."""
        from pydub import AudioSegment as PydubSegment
        from pydub.silence import detect_nonsilent

        self.logger.info(
            "Detecting silence gaps: threshold=%.0f dB, min_silence=%.1fs",
            threshold_db,
            min_silence_ms,
        )

        audio = PydubSegment.from_file(str(audio_path))
        total_duration = len(audio) / 1000.0  # ms -> seconds

        # detect_nonsilent returns [(start_ms, end_ms), ...]
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=int(min_silence_ms * 1000),
            silence_thresh=threshold_db,
            seek_step=10,  # Check every 10ms.
        )

        if not nonsilent_ranges:
            self.logger.warning("No speech detected in %s", audio_path.name)
            return [
                AudioSegment(
                    start_seconds=0.0,
                    end_seconds=total_duration,
                    text="",
                    topic="full_audio",
                    energy_level="medium",
                )
            ]

        # Convert to AudioSegment objects.
        raw_segments: list[AudioSegment] = []
        for start_ms, end_ms in nonsilent_ranges:
            raw_segments.append(
                AudioSegment(
                    start_seconds=start_ms / 1000.0,
                    end_seconds=end_ms / 1000.0,
                    energy_level="medium",
                )
            )

        # Merge segments that are too short.
        merged = self._merge_short_segments(raw_segments, min_segment)

        self.logger.info(
            "Detected %d speech segments (from %d raw) in %.1fs audio",
            len(merged),
            len(raw_segments),
            total_duration,
        )

        return merged

    def _fallback_segmentation(
        self,
        audio_path: Path,
        segment_duration: float,
    ) -> list[AudioSegment]:
        """Simple duration-based segmentation when pydub is not available.

        Splits the audio into fixed-length segments.
        """
        # Try to get duration from the audio file.
        duration = self._get_audio_duration(audio_path)
        if duration <= 0:
            self.logger.error("Could not determine audio duration for %s", audio_path)
            return []

        segments: list[AudioSegment] = []
        start = 0.0
        seg_num = 1

        while start < duration:
            end = min(start + segment_duration, duration)
            segments.append(
                AudioSegment(
                    start_seconds=start,
                    end_seconds=end,
                    topic=f"segment_{seg_num}",
                    energy_level="medium",
                )
            )
            start = end
            seg_num += 1

        self.logger.info(
            "Fallback segmentation: %d segments of ~%.0fs from %.1fs audio",
            len(segments),
            segment_duration,
            duration,
        )
        return segments

    # ------------------------------------------------------------------
    # Transcript-based segmentation
    # ------------------------------------------------------------------

    def segment_by_transcript(
        self,
        words: list[dict],
        target_segment_count: int | None = None,
        max_segment_duration: float = 60.0,
    ) -> list[AudioSegment]:
        """Segment audio based on word-level transcript timestamps.

        Groups words into segments based on natural pause points
        (gaps between words) and maximum duration constraints.

        Args:
            words: Word-level timestamps from Whisper transcription.
                Each dict has keys: word, start, end.
            target_segment_count: Desired number of segments.  If None,
                segments are created based on natural pauses.
            max_segment_duration: Maximum duration per segment in seconds.

        Returns:
            List of :class:`AudioSegment` objects with text populated.
        """
        if not words:
            return []

        # Find natural pause points (gaps > 0.3 seconds between words).
        pause_threshold = 0.3  # seconds
        pause_points: list[int] = []

        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i - 1]["end"]
            if gap >= pause_threshold:
                pause_points.append(i)

        if not pause_points:
            # No natural pauses found — create one big segment.
            text = " ".join(w["word"] for w in words)
            return [
                AudioSegment(
                    start_seconds=words[0]["start"],
                    end_seconds=words[-1]["end"],
                    text=text,
                    energy_level="medium",
                )
            ]

        # Build segments at pause points.
        segments: list[AudioSegment] = []
        seg_start_idx = 0

        for pause_idx in pause_points:
            seg_words = words[seg_start_idx:pause_idx]
            if not seg_words:
                continue

            duration = seg_words[-1]["end"] - seg_words[0]["start"]

            # Only create a segment if it meets minimum duration.
            if duration >= 5.0 or pause_idx == pause_points[-1]:
                text = " ".join(w["word"] for w in seg_words)
                segments.append(
                    AudioSegment(
                        start_seconds=seg_words[0]["start"],
                        end_seconds=seg_words[-1]["end"],
                        text=text,
                        energy_level=self._estimate_energy(seg_words),
                    )
                )
                seg_start_idx = pause_idx

        # Handle remaining words after last pause.
        remaining = words[seg_start_idx:]
        if remaining:
            text = " ".join(w["word"] for w in remaining)
            segments.append(
                AudioSegment(
                    start_seconds=remaining[0]["start"],
                    end_seconds=remaining[-1]["end"],
                    text=text,
                    energy_level=self._estimate_energy(remaining),
                )
            )

        # Enforce max segment duration by splitting long segments.
        final_segments: list[AudioSegment] = []
        for seg in segments:
            if seg.duration_seconds > max_segment_duration:
                split = self._split_long_segment(seg, words, max_segment_duration)
                final_segments.extend(split)
            else:
                final_segments.append(seg)

        # If target count specified, merge to match.
        if target_segment_count and len(final_segments) > target_segment_count:
            final_segments = self._merge_to_target_count(
                final_segments, target_segment_count
            )

        self.logger.info(
            "Transcript segmentation: %d segments from %d words",
            len(final_segments),
            len(words),
        )
        return final_segments

    def full_analysis(
        self,
        audio_path: Path,
        words: list[dict] | None = None,
    ) -> SegmentationResult:
        """Run full segmentation analysis combining all strategies.

        Args:
            audio_path: Path to the audio file.
            words: Optional pre-computed word timestamps.  If not provided,
                only silence-based segmentation is performed.

        Returns:
            A :class:`SegmentationResult` with all detected segments.
        """
        audio_path = Path(audio_path)

        # Silence-based detection.
        silence_segments = self.detect_silence_gaps(audio_path)

        # Compute silence gaps (inverse of speech segments).
        silence_gaps: list[tuple[float, float]] = []
        for i in range(1, len(silence_segments)):
            gap_start = silence_segments[i - 1].end_seconds
            gap_end = silence_segments[i].start_seconds
            if gap_end > gap_start:
                silence_gaps.append((gap_start, gap_end))

        total_duration = self._get_audio_duration(audio_path)
        speech_duration = sum(s.duration_seconds for s in silence_segments)
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0

        # Transcript-based segmentation if words are available.
        if words:
            transcript_segments = self.segment_by_transcript(words)
            # Use transcript segments as the primary result since they
            # have richer information (text, energy levels).
            segments = transcript_segments
        else:
            segments = silence_segments

        avg_duration = (
            sum(s.duration_seconds for s in segments) / len(segments)
            if segments
            else 0.0
        )

        return SegmentationResult(
            segments=segments,
            silence_gaps=silence_gaps,
            total_duration_seconds=total_duration,
            speech_ratio=speech_ratio,
            average_segment_duration=avg_duration,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge_short_segments(
        self,
        segments: list[AudioSegment],
        min_duration: float,
    ) -> list[AudioSegment]:
        """Merge segments shorter than min_duration with their neighbors."""
        if not segments:
            return segments

        merged: list[AudioSegment] = [segments[0]]

        for seg in segments[1:]:
            prev = merged[-1]
            # Merge if either the current or previous segment is too short,
            # OR if the gap between them is very small (< 0.5s).
            gap = seg.start_seconds - prev.end_seconds
            if prev.duration_seconds < min_duration or gap < 0.5:
                # Extend the previous segment.
                merged[-1] = AudioSegment(
                    start_seconds=prev.start_seconds,
                    end_seconds=seg.end_seconds,
                    text=(prev.text + " " + seg.text).strip(),
                    topic=prev.topic or seg.topic,
                    energy_level=prev.energy_level,
                )
            else:
                merged.append(seg)

        # Final pass: merge the last segment if it is too short.
        if len(merged) > 1 and merged[-1].duration_seconds < min_duration:
            last = merged.pop()
            prev = merged[-1]
            merged[-1] = AudioSegment(
                start_seconds=prev.start_seconds,
                end_seconds=last.end_seconds,
                text=(prev.text + " " + last.text).strip(),
                topic=prev.topic or last.topic,
                energy_level=prev.energy_level,
            )

        return merged

    def _split_long_segment(
        self,
        segment: AudioSegment,
        all_words: list[dict],
        max_duration: float,
    ) -> list[AudioSegment]:
        """Split a long segment into smaller pieces at word boundaries."""
        # Find words within this segment's time range.
        seg_words = [
            w for w in all_words
            if w["start"] >= segment.start_seconds and w["end"] <= segment.end_seconds
        ]

        if not seg_words:
            return [segment]

        pieces: list[AudioSegment] = []
        chunk_start_idx = 0
        chunk_start_time = seg_words[0]["start"]

        for i, word in enumerate(seg_words):
            elapsed = word["end"] - chunk_start_time
            if elapsed >= max_duration and i > chunk_start_idx:
                chunk_words = seg_words[chunk_start_idx:i]
                text = " ".join(w["word"] for w in chunk_words)
                pieces.append(
                    AudioSegment(
                        start_seconds=chunk_words[0]["start"],
                        end_seconds=chunk_words[-1]["end"],
                        text=text,
                        energy_level=self._estimate_energy(chunk_words),
                    )
                )
                chunk_start_idx = i
                chunk_start_time = word["start"]

        # Flush remaining.
        remaining = seg_words[chunk_start_idx:]
        if remaining:
            text = " ".join(w["word"] for w in remaining)
            pieces.append(
                AudioSegment(
                    start_seconds=remaining[0]["start"],
                    end_seconds=remaining[-1]["end"],
                    text=text,
                    energy_level=self._estimate_energy(remaining),
                )
            )

        return pieces

    def _merge_to_target_count(
        self,
        segments: list[AudioSegment],
        target: int,
    ) -> list[AudioSegment]:
        """Merge adjacent segments until we reach the target count.

        Preferentially merges the shortest segments first.
        """
        while len(segments) > target and len(segments) > 1:
            # Find the shortest segment.
            min_idx = min(
                range(len(segments)),
                key=lambda i: segments[i].duration_seconds,
            )

            # Merge with the shorter neighbor.
            if min_idx == 0:
                merge_idx = 0
            elif min_idx == len(segments) - 1:
                merge_idx = min_idx - 1
            else:
                # Merge with whichever neighbor is shorter.
                if segments[min_idx - 1].duration_seconds <= segments[min_idx + 1].duration_seconds:
                    merge_idx = min_idx - 1
                else:
                    merge_idx = min_idx

            a = segments[merge_idx]
            b = segments[merge_idx + 1]
            merged = AudioSegment(
                start_seconds=a.start_seconds,
                end_seconds=b.end_seconds,
                text=(a.text + " " + b.text).strip(),
                topic=a.topic or b.topic,
                energy_level=a.energy_level,
            )
            segments[merge_idx] = merged
            segments.pop(merge_idx + 1)

        return segments

    @staticmethod
    def _estimate_energy(words: list[dict]) -> str:
        """Estimate energy level from word pacing.

        Fast pacing (many words per second) suggests high energy.
        """
        if not words or len(words) < 2:
            return "medium"

        duration = words[-1]["end"] - words[0]["start"]
        if duration <= 0:
            return "medium"

        words_per_second = len(words) / duration

        if words_per_second > 3.5:
            return "high"
        elif words_per_second < 2.0:
            return "low"
        return "medium"

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get the duration of an audio file in seconds."""
        try:
            from pydub import AudioSegment as PydubSegment

            audio = PydubSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
        except ImportError:
            pass

        # Fallback: try ffprobe.
        try:
            import subprocess

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        self.logger.warning(
            "Could not determine duration for %s — install pydub or ffprobe",
            audio_path,
        )
        return 0.0
