"""Audio-first video pipeline — generate video from existing audio content.

This is a key differentiator from InVideo.io, which focuses on text-to-video.
The audio-first pipeline enables podcast-to-video, lecture-to-video, and
any audio-to-visual-content workflow.

Workflow:
1. Transcribe audio with Whisper (word-level timestamps).
2. Analyze transcript for sections/topics via Claude.
3. Generate visual queries per section from transcript.
4. Source/generate visuals matching each section.
5. Sync visuals to audio timeline.
6. Add captions from transcription.
7. Assemble final video.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import anthropic

from aividio.audio_first.segmenter import AudioSegmenter
from aividio.config.profiles import ChannelProfile, get_default_profile, load_profile
from aividio.config.settings import Settings, get_settings
from aividio.services.captions.whisper import WhisperCaptionGenerator
from aividio.utils.retry import retry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_SECTION_ANALYSIS_SYSTEM = """\
You are a content analyst.  Given a transcript with timestamps, identify \
distinct sections/topics and their boundaries.

For each section, provide:
- A descriptive heading
- Start and end timestamps (in seconds)
- A summary of the section content
- The emotional tone/energy of the section
- Key terms or entities mentioned

Return **strict JSON** — no markdown fences, no commentary:
{
  "sections": [
    {
      "section_number": <int>,
      "heading": "<descriptive heading>",
      "start_seconds": <float>,
      "end_seconds": <float>,
      "summary": "<1-2 sentence summary>",
      "tone": "<informative|excited|serious|humorous|dramatic|conversational>",
      "key_terms": ["<important terms>"]
    }
  ],
  "overall_topic": "<main topic of the audio>",
  "suggested_title": "<YouTube-ready title>",
  "total_sections": <int>
}
"""

_VISUAL_PLAN_SYSTEM = """\
You are a visual director for a faceless YouTube video.  Given a list of \
audio sections with summaries and timestamps, create a visual plan that \
keeps viewers engaged throughout.

For each section, specify:
- The type of visual (stock_video, stock_image, ai_image)
- A search query for stock media OR an AI image generation prompt
- Visual mood/style notes
- Whether to use text overlays and what they should say
- Transition type to the next section

Rules:
- Vary visual types to maintain interest.
- Use stock video for action/process content.
- Use AI images for abstract concepts or when stock fails.
- Add text overlays for key statistics, quotes, or emphasis.
- Use smooth transitions (crossfade for related topics, cut for topic changes).

Return **strict JSON** — no markdown fences:
{
  "visual_plan": [
    {
      "section_number": <int>,
      "heading": "<section heading>",
      "visual_type": "stock_video|stock_image|ai_image",
      "search_query": "<stock media search query>",
      "ai_image_prompt": "<detailed prompt if visual_type is ai_image, else empty>",
      "mood": "<visual mood>",
      "text_overlay": "<text to overlay or empty>",
      "text_overlay_position": "top|center|bottom|none",
      "transition_to_next": "crossfade|cut|zoom|slide",
      "duration_seconds": <float>,
      "notes": "<any additional direction>"
    }
  ]
}
"""


class AudioFirstPipeline:
    """Generate video from existing audio content.

    This pipeline inverts the typical text-first workflow: instead of
    generating a script and then audio, it starts with existing audio
    (podcast episode, lecture, voiceover) and builds the visual layer
    around it.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger("aividio.audio_first.AudioFirstPipeline")
        self._segmenter = AudioSegmenter(settings=self.settings)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_claude_client(self) -> anthropic.Anthropic:
        """Create an Anthropic client from settings."""
        api_key = self.settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError(
                "anthropic_api_key is required for audio analysis. "
                "Set VIDMATION_ANTHROPIC_API_KEY in your environment."
            )
        return anthropic.Anthropic(api_key=api_key)

    def _call_claude(self, system: str, user_message: str) -> str:
        """Send a request to Claude and return the cleaned text response."""
        client = self._get_claude_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences.
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]

        return raw.strip()

    def _resolve_profile(self, channel_name: str) -> ChannelProfile:
        """Load the channel profile, falling back to defaults."""
        from aividio.db.engine import get_session, init_db
        from aividio.db.repos import ChannelRepo

        init_db()
        session = get_session()
        try:
            repo = ChannelRepo(session)
            ch = repo.get_by_name(channel_name)
            if ch is None:
                return get_default_profile()
            try:
                return load_profile(ch.profile_path)
            except (FileNotFoundError, AttributeError):
                return get_default_profile()
        finally:
            session.close()

    def _ensure_work_dir(self, audio_path: Path) -> Path:
        """Create a work directory for pipeline artifacts."""
        work_id = str(uuid.uuid4())[:8]
        stem = audio_path.stem[:30]  # Truncate long filenames.
        work_dir = self.settings.output_dir / f"audio_first_{stem}_{work_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        audio_path: Path,
        channel_name: str,
        format: str = "landscape",
    ) -> Path:
        """Full audio-to-video pipeline.

        Steps:
        1. Transcribe audio with word-level timestamps.
        2. Segment audio into sections via silence detection and topic analysis.
        3. Analyze sections with Claude for content understanding.
        4. Generate a visual plan for each section.
        5. (Placeholder) Source or generate visuals.
        6. (Placeholder) Sync visuals to audio timeline.
        7. (Placeholder) Add captions and assemble final video.

        Args:
            audio_path: Path to the audio file (mp3, wav, m4a, etc.).
            channel_name: Name of the channel for profile resolution.
            format: Video format (landscape, portrait, short).

        Returns:
            Path to the work directory containing all pipeline artifacts.
            The final video path will be ``work_dir / "final_video.mp4"``
            once the assembly stages are implemented.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self.logger.info(
            "Starting audio-first pipeline: audio=%s, channel=%s, format=%s",
            audio_path.name,
            channel_name,
            format,
        )

        profile = self._resolve_profile(channel_name)
        work_dir = self._ensure_work_dir(audio_path)

        # Step 1: Transcribe.
        self.logger.info("Step 1/7: Transcribing audio...")
        analysis = self.analyze_audio(audio_path)

        # Save transcription.
        transcript_path = work_dir / "transcript.json"
        transcript_path.write_text(
            json.dumps(analysis, indent=2, default=str),
            encoding="utf-8",
        )
        self.logger.info("Transcript saved to %s", transcript_path)

        # Step 2-3: Section analysis is included in analyze_audio.
        sections = analysis.get("sections", [])
        self.logger.info("Step 2-3: Identified %d sections", len(sections))

        # Step 4: Generate visual plan.
        self.logger.info("Step 4/7: Planning visuals...")
        visual_plan = self.plan_visuals(sections)

        # Save visual plan.
        visual_plan_path = work_dir / "visual_plan.json"
        visual_plan_path.write_text(
            json.dumps(visual_plan, indent=2, default=str),
            encoding="utf-8",
        )
        self.logger.info("Visual plan saved to %s", visual_plan_path)

        # Steps 5-7: Visual sourcing, sync, and assembly.
        # These are placeholders — they require the media sourcing and
        # video assembly services to be wired in.
        pipeline_state = {
            "audio_path": str(audio_path),
            "channel_name": channel_name,
            "format": format,
            "work_dir": str(work_dir),
            "transcript_path": str(transcript_path),
            "visual_plan_path": str(visual_plan_path),
            "sections_count": len(sections),
            "words_count": analysis.get("word_count", 0),
            "status": "visual_plan_ready",
            "steps_completed": ["transcribe", "segment", "analyze", "plan_visuals"],
            "steps_remaining": ["source_visuals", "sync_timeline", "assemble_video"],
        }

        state_path = work_dir / "pipeline_state.json"
        state_path.write_text(
            json.dumps(pipeline_state, indent=2),
            encoding="utf-8",
        )

        self.logger.info(
            "Audio-first pipeline checkpoint saved. Work dir: %s\n"
            "Steps remaining: source_visuals, sync_timeline, assemble_video",
            work_dir,
        )

        return work_dir

    def analyze_audio(self, audio_path: Path) -> dict[str, Any]:
        """Transcribe and segment audio into sections.

        Combines Whisper transcription with Claude analysis to produce
        a rich understanding of the audio content.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Dict containing:
            - words: list of word-level timestamps
            - word_count: total word count
            - full_transcript: joined text
            - segments: silence-based segments from AudioSegmenter
            - sections: topic-based sections from Claude analysis
            - overall_topic: main topic
            - suggested_title: YouTube-ready title
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self.logger.info("Analyzing audio: %s", audio_path.name)

        # Step 1: Whisper transcription.
        whisper = WhisperCaptionGenerator(settings=self.settings)
        words = whisper.transcribe(audio_path)

        if not words:
            raise ValueError(
                f"Whisper returned no words for {audio_path.name}. "
                f"The file may be silent, corrupted, or in an unsupported format."
            )

        full_transcript = " ".join(w["word"] for w in words)
        total_duration = words[-1]["end"] if words else 0.0

        self.logger.info(
            "Transcription complete: %d words, %.1fs duration",
            len(words),
            total_duration,
        )

        # Step 2: Silence-based segmentation.
        segments = self._segmenter.detect_silence_gaps(audio_path)
        self.logger.info("Detected %d silence-based segments", len(segments))

        # Step 3: Topic analysis via Claude.
        # Build a condensed transcript with timestamps for Claude.
        timestamped_chunks = self._build_timestamped_chunks(words, chunk_seconds=30.0)

        sections_data = self._analyze_sections_with_claude(timestamped_chunks, full_transcript)

        return {
            "words": words,
            "word_count": len(words),
            "full_transcript": full_transcript,
            "total_duration_seconds": total_duration,
            "segments": [
                {
                    "start": s.start_seconds,
                    "end": s.end_seconds,
                    "duration": s.duration_seconds,
                    "text": s.text,
                    "topic": s.topic,
                    "energy": s.energy_level,
                }
                for s in segments
            ],
            "sections": sections_data.get("sections", []),
            "overall_topic": sections_data.get("overall_topic", ""),
            "suggested_title": sections_data.get("suggested_title", ""),
        }

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def plan_visuals(self, sections: list[dict]) -> list[dict]:
        """Generate a visual plan for each audio section.

        Uses Claude to determine the best visual approach for each section,
        including stock media queries, AI image prompts, text overlays,
        and transition types.

        Args:
            sections: List of section dicts from :meth:`analyze_audio`.

        Returns:
            List of visual plan dicts, one per section.
        """
        if not sections:
            self.logger.warning("No sections provided for visual planning")
            return []

        self.logger.info("Planning visuals for %d sections", len(sections))

        user_message = (
            f"Create a visual plan for this video with {len(sections)} sections:\n\n"
            + json.dumps(sections, indent=2)
        )

        raw = self._call_claude(
            system=_VISUAL_PLAN_SYSTEM,
            user_message=user_message,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.logger.error("Claude returned invalid JSON for visual plan: %s", exc)
            raise ValueError("Visual plan response was not valid JSON") from exc

        plan = data.get("visual_plan", data if isinstance(data, list) else [])

        self.logger.info("Visual plan created: %d entries", len(plan))
        return plan

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_timestamped_chunks(
        self,
        words: list[dict],
        chunk_seconds: float = 30.0,
    ) -> str:
        """Group words into time-stamped chunks for Claude analysis.

        Produces a human-readable transcript with timestamps every
        ``chunk_seconds`` seconds, which is more efficient than sending
        every individual word.
        """
        if not words:
            return ""

        chunks: list[str] = []
        current_chunk_words: list[str] = []
        chunk_start = words[0]["start"]
        next_boundary = chunk_start + chunk_seconds

        for word in words:
            if word["start"] >= next_boundary and current_chunk_words:
                chunk_end = word["start"]
                text = " ".join(current_chunk_words)
                chunks.append(f"[{chunk_start:.1f}s - {chunk_end:.1f}s] {text}")
                current_chunk_words = []
                chunk_start = word["start"]
                next_boundary = chunk_start + chunk_seconds

            current_chunk_words.append(word["word"])

        # Flush remaining words.
        if current_chunk_words:
            chunk_end = words[-1]["end"]
            text = " ".join(current_chunk_words)
            chunks.append(f"[{chunk_start:.1f}s - {chunk_end:.1f}s] {text}")

        return "\n".join(chunks)

    @retry(max_attempts=3, base_delay=2.0, exceptions=(anthropic.APIError,))
    def _analyze_sections_with_claude(
        self,
        timestamped_chunks: str,
        full_transcript: str,
    ) -> dict:
        """Use Claude to identify topic sections in the transcript."""
        self.logger.info("Analyzing transcript sections with Claude")

        # Truncate full transcript if very long (Claude can handle a lot,
        # but the timestamped chunks are the primary input).
        transcript_preview = full_transcript[:5000]
        if len(full_transcript) > 5000:
            transcript_preview += "\n... [truncated]"

        user_message = (
            f"Analyze this timestamped transcript and identify distinct sections:\n\n"
            f"**Timestamped transcript:**\n{timestamped_chunks}\n\n"
            f"**Full transcript preview:**\n{transcript_preview}"
        )

        raw = self._call_claude(
            system=_SECTION_ANALYSIS_SYSTEM,
            user_message=user_message,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.logger.error("Claude returned invalid JSON for section analysis: %s", exc)
            raise ValueError("Section analysis response was not valid JSON") from exc

        section_count = len(data.get("sections", []))
        self.logger.info(
            "Section analysis complete: %d sections, topic=%r",
            section_count,
            data.get("overall_topic", "unknown"),
        )
        return data
