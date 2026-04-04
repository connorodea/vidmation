"""EmojiSFXEngine — auto-insert animated emojis and sound effects.

Detects keywords in a transcript that map to emojis and/or sound effects,
then overlays emoji graphics using ffmpeg's ``drawtext`` filter and mixes
SFX into the audio track.
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg

from vidmation.config.settings import Settings, get_settings
from vidmation.utils.ffmpeg import FFmpegError, get_duration, get_resolution, run_ffmpeg
from vidmation.utils.retry import retry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SFX detection prompt
# ---------------------------------------------------------------------------

_SFX_SYSTEM_PROMPT = """\
You are an expert video editor. Given a transcript with word-level timestamps,
identify moments where sound effects would enhance viewer engagement.

Available sound effects:
- "emphasis" — ding/chime for key points
- "transition" — whoosh for topic changes
- "reveal" — dramatic reveal sound
- "pop" — pop sound for list items or emphasis
- "typing" — keyboard typing sound
- "success" — positive/win sound
- "fail" — negative/error sound
- "cash" — cash register for money topics

Return a JSON array with:
- "start": float — timestamp in seconds
- "sfx_name": string — one of the available SFX names above
- "volume": float between 0.3 and 1.0 — relative volume

Rules:
- Maximum {max_sfx} sound effects
- Space them at least 2 seconds apart
- Don't overdo it — quality over quantity
- Respond with ONLY the JSON array
"""


class EmojiSFXEngine:
    """Auto-insert animated emojis and sound effects based on transcript.

    Provides keyword-to-emoji mapping for visual overlays and a sound-effect
    library for audio enhancement.  Supports AI-powered context-aware
    placement via Claude for SFX.
    """

    # Keyword -> emoji mapping (case-insensitive).
    EMOJI_MAP: dict[str, str] = {
        # Money & Finance
        "money": "\U0001f4b0", "dollar": "\U0001f4b5", "rich": "\U0001f911",
        "cash": "\U0001f4b8", "profit": "\U0001f4b0", "revenue": "\U0001f4b0",
        "income": "\U0001f4b5", "invest": "\U0001f4b0", "stock": "\U0001f4c8",
        "crypto": "\U0001f4b0", "bitcoin": "\U0001f4b0", "bank": "\U0001f3e6",
        "price": "\U0001f4b2", "expensive": "\U0001f4b8", "cheap": "\U0001f4b5",
        # Fire & Excitement
        "fire": "\U0001f525", "hot": "\U0001f525", "amazing": "\U0001f525",
        "awesome": "\U0001f525", "incredible": "\U0001f525", "insane": "\U0001f525",
        "viral": "\U0001f525", "trending": "\U0001f525", "epic": "\U0001f525",
        # Love & Emotion
        "love": "\u2764\ufe0f", "heart": "\u2764\ufe0f", "favorite": "\u2764\ufe0f",
        "passion": "\u2764\ufe0f", "beautiful": "\u2764\ufe0f",
        # Brain & Intelligence
        "brain": "\U0001f9e0", "smart": "\U0001f9e0", "think": "\U0001f914",
        "idea": "\U0001f4a1", "strategy": "\U0001f9e0", "genius": "\U0001f9e0",
        "learn": "\U0001f4da", "knowledge": "\U0001f4da", "education": "\U0001f393",
        # Warning & Danger
        "warning": "\u26a0\ufe0f", "danger": "\U0001f6a8", "risk": "\u26a0\ufe0f",
        "careful": "\u26a0\ufe0f", "caution": "\u26a0\ufe0f", "alert": "\U0001f6a8",
        # Surprise & Shock
        "wow": "\U0001f631", "shocked": "\U0001f631", "crazy": "\U0001f92f",
        "mind": "\U0001f92f", "unbelievable": "\U0001f631", "surprise": "\U0001f631",
        "mindblowing": "\U0001f92f", "insane": "\U0001f92f",
        # Humor
        "laugh": "\U0001f602", "funny": "\U0001f602", "joke": "\U0001f602",
        "hilarious": "\U0001f923", "lol": "\U0001f602",
        # Pointing & Direction
        "point": "\U0001f449", "this": "\U0001f446", "look": "\U0001f440",
        "watch": "\U0001f440", "see": "\U0001f440", "here": "\U0001f449",
        # Status
        "check": "\u2705", "correct": "\u2705", "yes": "\u2705",
        "right": "\u2705", "true": "\u2705", "done": "\u2705",
        "wrong": "\u274c", "false": "\u274c", "no": "\u274c",
        "bad": "\u274c", "mistake": "\u274c", "error": "\u274c",
        # Numbers & Lists
        "number": "\U0001f522", "list": "\U0001f4cb", "step": "\U0001f4cb",
        "tip": "\U0001f4cb", "rule": "\U0001f4cb", "hack": "\U0001f4cb",
        # Secret & Quiet
        "secret": "\U0001f92b", "quiet": "\U0001f92b", "hidden": "\U0001f92b",
        "trick": "\U0001f92b", "loophole": "\U0001f92b",
        # Time
        "time": "\u23f0", "clock": "\U0001f550", "fast": "\u23f0",
        "quick": "\u23f0", "hurry": "\u23f0", "deadline": "\u23f0",
        # Growth & Charts
        "growth": "\U0001f4c8", "up": "\U0001f4c8", "increase": "\U0001f4c8",
        "rise": "\U0001f4c8", "boost": "\U0001f4c8", "grow": "\U0001f4c8",
        "down": "\U0001f4c9", "decrease": "\U0001f4c9", "drop": "\U0001f4c9",
        "fall": "\U0001f4c9", "decline": "\U0001f4c9", "crash": "\U0001f4c9",
        # Celebration
        "win": "\U0001f3c6", "success": "\U0001f3c6", "champion": "\U0001f3c6",
        "celebrate": "\U0001f389", "party": "\U0001f389", "congratulations": "\U0001f389",
        # Work & Tools
        "work": "\U0001f4bc", "business": "\U0001f4bc", "tool": "\U0001f527",
        "build": "\U0001f527", "create": "\U0001f3a8", "design": "\U0001f3a8",
        # Technology
        "computer": "\U0001f4bb", "phone": "\U0001f4f1", "app": "\U0001f4f1",
        "website": "\U0001f4bb", "software": "\U0001f4bb", "ai": "\U0001f916",
        "robot": "\U0001f916",
        # Food
        "food": "\U0001f354", "eat": "\U0001f37d\ufe0f", "coffee": "\u2615",
        "pizza": "\U0001f355",
        # Misc
        "world": "\U0001f30d", "earth": "\U0001f30d", "global": "\U0001f30d",
        "rocket": "\U0001f680", "launch": "\U0001f680", "start": "\U0001f680",
        "power": "\u26a1", "energy": "\u26a1", "electric": "\u26a1",
        "star": "\u2b50", "best": "\u2b50", "top": "\u2b50",
        "key": "\U0001f511", "unlock": "\U0001f511", "access": "\U0001f511",
        "target": "\U0001f3af", "goal": "\U0001f3af", "focus": "\U0001f3af",
    }

    # Sound effect library — names map to bundled SFX filenames.
    SFX_MAP: dict[str, str] = {
        "emphasis": "ding.mp3",
        "transition": "whoosh.mp3",
        "reveal": "reveal.mp3",
        "pop": "pop.mp3",
        "typing": "typing.mp3",
        "success": "success.mp3",
        "fail": "fail.mp3",
        "cash": "cash_register.mp3",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(f"vidmation.effects.{self.__class__.__name__}")
        self._sfx_dir = self.settings.assets_dir / "sfx"

    # ------------------------------------------------------------------
    # Emoji detection
    # ------------------------------------------------------------------

    def detect_emoji_points(
        self,
        word_timestamps: list[dict],
        max_emojis: int = 20,
    ) -> list[dict]:
        """Find words that should have emoji overlays.

        Matches transcript words against the keyword-emoji map.  Deduplicates
        so the same emoji is not shown within 3 seconds.

        Parameters:
            word_timestamps: Word-level timestamps from Whisper.
            max_emojis: Maximum number of emoji overlays.

        Returns:
            List of dicts with ``word``, ``start``, ``end``, ``emoji``,
            ``position`` keys.  ``position`` is one of ``"top_right"``,
            ``"top_left"``, ``"center"``.
        """
        if not word_timestamps:
            return []

        self.logger.info("Scanning %d words for emoji matches", len(word_timestamps))

        matches: list[dict] = []
        positions = ["top_right", "top_left", "center"]

        for w in word_timestamps:
            cleaned = w["word"].lower().strip(".,!?;:'\"()-")
            if cleaned in self.EMOJI_MAP:
                emoji = self.EMOJI_MAP[cleaned]
                position = positions[len(matches) % len(positions)]
                matches.append({
                    "word": cleaned,
                    "start": w["start"],
                    "end": w["end"],
                    "emoji": emoji,
                    "position": position,
                })

        # Deduplicate: same emoji not within 3 seconds.
        deduped: list[dict] = []
        recent_emojis: dict[str, float] = {}  # emoji -> last timestamp

        for m in matches:
            last_time = recent_emojis.get(m["emoji"], -10.0)
            if m["start"] - last_time >= 3.0:
                deduped.append(m)
                recent_emojis[m["emoji"]] = m["start"]

        result = deduped[:max_emojis]
        self.logger.info("Detected %d emoji points", len(result))
        return result

    # ------------------------------------------------------------------
    # SFX detection
    # ------------------------------------------------------------------

    def detect_sfx_points(
        self,
        word_timestamps: list[dict],
        script: dict | None = None,
        max_sfx: int = 15,
    ) -> list[dict]:
        """Identify moments for sound effects.

        Uses keyword matching as a baseline.  If a Claude API key is
        configured, uses AI for context-aware placement.

        Parameters:
            word_timestamps: Word-level timestamps from Whisper.
            script: Optional script dict for context.
            max_sfx: Maximum number of SFX placements.

        Returns:
            List of dicts with ``start``, ``sfx_name``, ``volume`` keys.
        """
        if not word_timestamps:
            return []

        # Keyword-based SFX mapping.
        sfx_keywords: dict[str, str] = {
            "money": "cash", "dollar": "cash", "cash": "cash",
            "profit": "cash", "revenue": "cash",
            "but": "transition", "however": "transition",
            "meanwhile": "transition", "instead": "transition",
            "secret": "reveal", "truth": "reveal", "reveal": "reveal",
            "first": "pop", "second": "pop", "third": "pop",
            "one": "pop", "two": "pop", "three": "pop",
            "tip": "pop", "step": "pop", "hack": "pop",
            "success": "success", "win": "success", "won": "success",
            "fail": "fail", "mistake": "fail", "wrong": "fail",
            "important": "emphasis", "key": "emphasis",
            "remember": "emphasis", "crucial": "emphasis",
        }

        # Try AI detection first.
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if api_key:
            try:
                return self._detect_sfx_ai(word_timestamps, max_sfx)
            except Exception as exc:
                self.logger.warning("AI SFX detection failed: %s — using keywords", exc)

        # Keyword fallback.
        self.logger.info("Detecting SFX points via keyword matching")
        matches: list[dict] = []

        for w in word_timestamps:
            cleaned = w["word"].lower().strip(".,!?;:'\"()-")
            if cleaned in sfx_keywords:
                sfx_name = sfx_keywords[cleaned]
                matches.append({
                    "start": w["start"],
                    "sfx_name": sfx_name,
                    "volume": 0.6,
                })

        # Deduplicate: same SFX not within 4 seconds.
        deduped: list[dict] = []
        recent_sfx: dict[str, float] = {}

        for m in matches:
            last_time = recent_sfx.get(m["sfx_name"], -10.0)
            if m["start"] - last_time >= 4.0:
                deduped.append(m)
                recent_sfx[m["sfx_name"]] = m["start"]

        result = deduped[:max_sfx]
        self.logger.info("Detected %d SFX points", len(result))
        return result

    @retry(max_attempts=2, base_delay=2.0, exceptions=(Exception,))
    def _detect_sfx_ai(
        self,
        word_timestamps: list[dict],
        max_sfx: int,
    ) -> list[dict]:
        """AI-powered SFX detection using Claude."""
        import anthropic

        api_key = self.settings.anthropic_api_key.get_secret_value()
        client = anthropic.Anthropic(api_key=api_key)

        transcript_text = _format_transcript(word_timestamps)

        system = _SFX_SYSTEM_PROMPT.format(max_sfx=max_sfx)
        user_msg = (
            f"Transcript ({len(word_timestamps)} words, "
            f"{word_timestamps[-1]['end']:.1f}s):\n\n"
            f"{transcript_text}\n\n"
            f"Identify the best moments for sound effects (max {max_sfx})."
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw_text = response.content[0].text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]

        points = json.loads(raw_text.strip())

        # Validate.
        validated: list[dict] = []
        for pt in points[:max_sfx]:
            sfx_name = str(pt.get("sfx_name", "emphasis"))
            if sfx_name not in self.SFX_MAP:
                sfx_name = "emphasis"
            validated.append({
                "start": max(0.0, float(pt.get("start", 0))),
                "sfx_name": sfx_name,
                "volume": max(0.3, min(1.0, float(pt.get("volume", 0.6)))),
            })

        self.logger.info("AI detected %d SFX points", len(validated))
        return validated

    # ------------------------------------------------------------------
    # Emoji overlay
    # ------------------------------------------------------------------

    def overlay_emojis(
        self,
        video_path: Path,
        emoji_points: list[dict],
        output_path: Path,
    ) -> Path:
        """Burn emoji overlays into video using ffmpeg drawtext filter.

        Each emoji appears for 1.5 seconds at its detected timestamp with
        a pop-in/fade-out animation.

        Parameters:
            video_path: Input video file.
            emoji_points: List of dicts with ``emoji``, ``start``, ``position`` keys.
            output_path: Output video path.

        Returns:
            Path to the output video.
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not emoji_points:
            self.logger.info("No emoji points; copying input")
            self._copy_video(video_path, output_path)
            return output_path

        width, height = get_resolution(video_path)

        # Build drawtext filter chain for each emoji.
        drawtext_filters: list[str] = []

        for pt in emoji_points:
            emoji = pt["emoji"]
            start = pt["start"]
            position = pt.get("position", "top_right")
            display_duration = 1.5  # seconds
            end = start + display_duration

            # Position coordinates.
            if position == "top_right":
                x, y = f"{width - 120}", "40"
            elif position == "top_left":
                x, y = "40", "40"
            elif position == "center":
                x, y = f"{width // 2 - 40}", f"{height // 2 - 40}"
            else:
                x, y = f"{width - 120}", "40"

            # Drawtext with enable expression for time-limited display.
            # Use fontsize animation for pop-in effect.
            drawtext_filters.append(
                f"drawtext=text='{emoji}':"
                f"fontsize=80:"
                f"x={x}:y={y}:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )

        # Chain all drawtext filters.
        filter_chain = ",".join(drawtext_filters)

        self.logger.info(
            "Overlaying %d emojis on %s",
            len(emoji_points),
            video_path.name,
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", filter_chain,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_path),
        ]

        run_ffmpeg(cmd, desc="EmojiSFXEngine overlay_emojis", timeout=600)

        self.logger.info("Emoji overlay complete: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # SFX mixing
    # ------------------------------------------------------------------

    def mix_sfx(
        self,
        audio_path: Path,
        sfx_points: list[dict],
        output_path: Path,
    ) -> Path:
        """Mix sound effects into the audio track at specified timestamps.

        Each SFX is loaded from the bundled assets, volume-adjusted, and
        mixed into the audio at the specified timestamp using ffmpeg's
        ``amix`` and ``adelay`` filters.

        Parameters:
            audio_path: Input audio file (or video with audio track).
            sfx_points: List of dicts with ``start``, ``sfx_name``, ``volume`` keys.
            output_path: Output audio file path.

        Returns:
            Path to the output audio file.
        """
        audio_path = Path(audio_path)
        output_path = Path(output_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Filter to only SFX that have available files.
        valid_sfx: list[dict] = []
        for pt in sfx_points:
            sfx_filename = self.SFX_MAP.get(pt["sfx_name"])
            if sfx_filename:
                sfx_path = self._sfx_dir / sfx_filename
                if sfx_path.exists():
                    valid_sfx.append({**pt, "_sfx_path": sfx_path})
                else:
                    self.logger.warning("SFX file not found: %s", sfx_path)
            else:
                self.logger.warning("Unknown SFX name: %s", pt.get("sfx_name"))

        if not valid_sfx:
            self.logger.info("No valid SFX files; copying input audio")
            self._copy_video(audio_path, output_path)
            return output_path

        self.logger.info("Mixing %d SFX into %s", len(valid_sfx), audio_path.name)

        # Build ffmpeg command with multiple inputs and adelay+volume filters.
        cmd = ["ffmpeg", "-y", "-i", str(audio_path)]

        filter_parts: list[str] = []
        input_labels: list[str] = []

        for i, sfx in enumerate(valid_sfx):
            cmd.extend(["-i", str(sfx["_sfx_path"])])
            input_idx = i + 1
            delay_ms = int(sfx["start"] * 1000)
            volume = sfx.get("volume", 0.6)

            label = f"[sfx{i}]"
            filter_parts.append(
                f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},"
                f"volume={volume:.2f}{label}"
            )
            input_labels.append(label)

        # Mix all SFX with the main audio.
        all_inputs = "[0:a]" + "".join(input_labels)
        n_inputs = len(valid_sfx) + 1
        filter_parts.append(
            f"{all_inputs}amix=inputs={n_inputs}:duration=first:dropout_transition=2[outa]"
        )

        filtergraph = ";\n".join(filter_parts)

        cmd.extend([
            "-filter_complex", filtergraph,
            "-map", "[outa]",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ])

        run_ffmpeg(cmd, desc="EmojiSFXEngine mix_sfx", timeout=300)

        self.logger.info("SFX mix complete: %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Combined auto-enhance
    # ------------------------------------------------------------------

    def auto_enhance(
        self,
        video_path: Path,
        word_timestamps: list[dict],
        emojis: bool = True,
        sfx: bool = True,
        max_emojis: int = 20,
        max_sfx: int = 15,
        output_path: Path | None = None,
    ) -> Path:
        """One-click emoji + SFX enhancement.

        Detects emoji and SFX points from the transcript, overlays emojis
        on the video, and mixes SFX into the audio track.

        Parameters:
            video_path: Input video file.
            word_timestamps: Word-level timestamps from Whisper.
            emojis: Whether to add emoji overlays.
            sfx: Whether to add sound effects.
            max_emojis: Maximum emoji overlays.
            max_sfx: Maximum sound effects.
            output_path: Output path (auto-generated if ``None``).

        Returns:
            Path to the enhanced video.
        """
        video_path = Path(video_path)
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_enhanced{video_path.suffix}"
        output_path = Path(output_path)

        self.logger.info(
            "Auto-enhance: %s (emojis=%s, sfx=%s)",
            video_path.name,
            emojis,
            sfx,
        )

        current_video = video_path

        # Step 1: Emoji overlays.
        if emojis:
            emoji_points = self.detect_emoji_points(word_timestamps, max_emojis=max_emojis)
            if emoji_points:
                emoji_output = video_path.parent / f"{video_path.stem}_emoji_tmp.mp4"
                current_video = self.overlay_emojis(current_video, emoji_points, emoji_output)
                self.logger.info("Added %d emoji overlays", len(emoji_points))

        # Step 2: SFX mixing.
        if sfx:
            sfx_points = self.detect_sfx_points(word_timestamps, max_sfx=max_sfx)
            if sfx_points:
                # Extract audio, mix SFX, then recombine with video.
                with tempfile.TemporaryDirectory(prefix="vidmation_sfx_") as tmp_dir:
                    tmp_path = Path(tmp_dir)
                    extracted_audio = tmp_path / "audio.aac"
                    mixed_audio = tmp_path / "mixed_audio.aac"

                    # Extract audio from current video.
                    cmd_extract = [
                        "ffmpeg", "-y",
                        "-i", str(current_video),
                        "-vn", "-acodec", "aac",
                        "-b:a", "192k",
                        str(extracted_audio),
                    ]
                    run_ffmpeg(cmd_extract, desc="Extract audio for SFX mixing")

                    # Mix SFX.
                    self.mix_sfx(extracted_audio, sfx_points, mixed_audio)

                    # Recombine video + mixed audio.
                    cmd_mux = [
                        "ffmpeg", "-y",
                        "-i", str(current_video),
                        "-i", str(mixed_audio),
                        "-map", "0:v",
                        "-map", "1:a",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-shortest",
                        str(output_path),
                    ]
                    run_ffmpeg(cmd_mux, desc="Mux video + SFX audio")
                    current_video = output_path

                    self.logger.info("Added %d SFX", len(sfx_points))

        # If only emojis were applied (no SFX), copy to final output.
        if current_video != output_path:
            self._copy_video(current_video, output_path)

        # Clean up temp emoji file.
        emoji_tmp = video_path.parent / f"{video_path.stem}_emoji_tmp.mp4"
        if emoji_tmp.exists() and emoji_tmp != output_path:
            try:
                emoji_tmp.unlink()
            except OSError:
                pass

        self.logger.info("Auto-enhance complete: %s", output_path)
        return output_path

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
