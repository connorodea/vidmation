"""Whisper-based caption generator — local or Replicate-hosted."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aividio.services.base import BaseService
from aividio.utils.retry import retry

if TYPE_CHECKING:
    from aividio.config.settings import Settings

# Replicate model for Whisper (incredibly-fast-whisper with word timestamps).
_REPLICATE_MODEL = "vaibhavs10/incredibly-fast-whisper:3ab86df6c8f54c11309d4d1f930ac292bad43ace52d10c80d87eb258b3c9f79c"


class WhisperCaptionGenerator(BaseService):
    """Generate word-level captions using OpenAI Whisper.

    Supports two backends:
    - ``"local"``: Uses the ``openai-whisper`` package locally.
    - ``"replicate"``: Uses Replicate's hosted Whisper model.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        backend: str = "faster-whisper",
    ) -> None:
        super().__init__(settings=settings)
        self._backend = backend

        if backend == "replicate":
            api_token = self.settings.replicate_api_token.get_secret_value()
            if not api_token:
                raise ValueError(
                    "replicate_api_token is required for Whisper via Replicate. "
                    "Set AIVIDIO_REPLICATE_API_TOKEN in your environment."
                )
            import replicate

            self._replicate_client = replicate.Client(api_token=api_token)

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def transcribe(self, audio_path: Path) -> list[dict]:
        """Transcribe audio to word-level timestamps.

        Args:
            audio_path: Path to audio file (mp3, wav, etc.).

        Returns:
            List of ``{"word": str, "start": float, "end": float}`` dicts.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self._backend == "replicate":
            return self._transcribe_replicate(audio_path)
        if self._backend == "faster-whisper":
            return self._transcribe_faster_whisper(audio_path)
        if self._backend == "local":
            return self._transcribe_local(audio_path)

        raise ValueError(f"Unknown Whisper backend: {self._backend!r}")

    def _transcribe_faster_whisper(self, audio_path: Path) -> list[dict]:
        """Run transcription using faster-whisper (CTranslate2). Python 3.14 compatible."""
        self.logger.info("Whisper (faster-whisper): transcribing %s", audio_path.name)

        # Prevent OpenMP duplicate library crash on macOS (ctranslate2 + torch conflict)
        import os
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "faster-whisper backend requires the 'faster-whisper' package. "
                "Install it with: pip install faster-whisper"
            ) from exc

        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(audio_path), word_timestamps=True)

        words: list[dict] = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                    })

        self.logger.info("faster-whisper transcription: %d words (lang=%s, prob=%.2f)",
                         len(words), info.language, info.language_probability)
        return words

    @retry(max_attempts=3, base_delay=5.0, exceptions=(Exception,))
    def _transcribe_replicate(self, audio_path: Path) -> list[dict]:
        """Run transcription via Replicate's hosted Whisper."""
        self.logger.info("Whisper (Replicate): transcribing %s", audio_path.name)

        with open(audio_path, "rb") as f:
            output = self._replicate_client.run(
                _REPLICATE_MODEL,
                input={
                    "audio": f,
                    "transcript_output_format": "words_only",
                    "timestamp": "word",
                    "batch_size": 64,
                },
            )

        # Parse the Replicate output into our standard format.
        words = self._parse_replicate_output(output)
        self.logger.info("Whisper transcription: %d words", len(words))
        return words

    def _transcribe_local(self, audio_path: Path) -> list[dict]:
        """Run transcription locally using openai-whisper package."""
        self.logger.info("Whisper (local): transcribing %s", audio_path.name)

        try:
            import whisper
        except ImportError as exc:
            raise ImportError(
                "Local Whisper backend requires the 'openai-whisper' package. "
                "Install it with: pip install openai-whisper"
            ) from exc

        model = whisper.load_model("base")
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
        )

        words: list[dict] = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                words.append(
                    {
                        "word": word_info["word"].strip(),
                        "start": round(word_info["start"], 3),
                        "end": round(word_info["end"], 3),
                    }
                )

        self.logger.info("Whisper transcription: %d words", len(words))
        return words

    @staticmethod
    def _parse_replicate_output(output: Any) -> list[dict]:
        """Normalize Replicate Whisper output into standard word list."""
        words: list[dict] = []

        # The output format can vary; handle common shapes.
        if isinstance(output, dict):
            # New format: {"words": [{"word": ..., "start": ..., "end": ...}]}
            word_list = output.get("words", [])
            if not word_list:
                # Alternative: segments with words
                for seg in output.get("segments", []):
                    for w in seg.get("words", []):
                        words.append(
                            {
                                "word": w.get("word", "").strip(),
                                "start": round(float(w.get("start", 0)), 3),
                                "end": round(float(w.get("end", 0)), 3),
                            }
                        )
                return words

            for w in word_list:
                words.append(
                    {
                        "word": w.get("word", "").strip(),
                        "start": round(float(w.get("start", 0)), 3),
                        "end": round(float(w.get("end", 0)), 3),
                    }
                )
        elif isinstance(output, str):
            # Sometimes output is a JSON string.
            parsed = json.loads(output)
            return WhisperCaptionGenerator._parse_replicate_output(parsed)

        return words

    # ------------------------------------------------------------------
    # SRT generation
    # ------------------------------------------------------------------

    def generate_srt(
        self,
        words: list[dict],
        output_path: Path,
        words_per_group: int = 3,
    ) -> Path:
        """Generate an SRT subtitle file from word timestamps.

        Args:
            words: Word-level timestamps from :meth:`transcribe`.
            output_path: Path to write the ``.srt`` file.
            words_per_group: Number of words per subtitle cue.

        Returns:
            Path to the written SRT file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        groups = self._group_words(words, words_per_group)
        lines: list[str] = []

        for idx, group in enumerate(groups, 1):
            start_ts = self._format_srt_time(group[0]["start"])
            end_ts = self._format_srt_time(group[-1]["end"])
            text = " ".join(w["word"] for w in group)
            lines.append(f"{idx}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        self.logger.info("SRT written: %s (%d cues)", output_path, len(groups))
        return output_path

    # ------------------------------------------------------------------
    # ASS generation (styled captions)
    # ------------------------------------------------------------------

    def generate_ass(
        self,
        words: list[dict],
        output_path: Path,
        style_config: dict | None = None,
    ) -> Path:
        """Generate an ASS (Advanced SubStation Alpha) subtitle file.

        ASS supports styling — font, color, position, outline — which is
        used for the bold centered captions typical in faceless videos.

        Args:
            words: Word-level timestamps from :meth:`transcribe`.
            output_path: Path to write the ``.ass`` file.
            style_config: Optional overrides for caption styling.  Keys:
                ``font_name``, ``font_size``, ``primary_color``,
                ``outline_color``, ``outline_width``, ``alignment``,
                ``margin_v``, ``words_per_group``.

        Returns:
            Path to the written ASS file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cfg = {
            "font_name": "Montserrat Bold",
            "font_size": 48,
            "primary_color": "&H00FFFFFF",  # white (ASS BGR format)
            "outline_color": "&H00000000",  # black
            "outline_width": 3,
            "alignment": 2,  # bottom-center
            "margin_v": 60,
            "words_per_group": 3,
        }
        if style_config:
            cfg.update(style_config)

        groups = self._group_words(words, cfg["words_per_group"])

        header = textwrap.dedent(f"""\
            [Script Info]
            ScriptType: v4.00+
            PlayResX: 1920
            PlayResY: 1080
            WrapStyle: 0

            [V4+ Styles]
            Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
            Style: Default,{cfg["font_name"]},{cfg["font_size"]},{cfg["primary_color"]},&H000000FF,{cfg["outline_color"]},&H80000000,-1,0,0,0,100,100,0,0,1,{cfg["outline_width"]},0,{cfg["alignment"]},10,10,{cfg["margin_v"]},1

            [Events]
            Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        """)

        event_lines: list[str] = []
        for group in groups:
            start_ts = self._format_ass_time(group[0]["start"])
            end_ts = self._format_ass_time(group[-1]["end"])
            text = " ".join(w["word"] for w in group)
            event_lines.append(
                f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
            )

        content = header + "\n".join(event_lines) + "\n"
        output_path.write_text(content, encoding="utf-8")
        self.logger.info("ASS written: %s (%d cues)", output_path, len(groups))
        return output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _group_words(words: list[dict], group_size: int) -> list[list[dict]]:
        """Split a word list into groups of *group_size*."""
        return [
            words[i : i + group_size]
            for i in range(0, len(words), group_size)
        ]

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Format seconds as SRT timestamp ``HH:MM:SS,mmm``."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds % 1) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Format seconds as ASS timestamp ``H:MM:SS.cc``."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds % 1) * 100))
        return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"
