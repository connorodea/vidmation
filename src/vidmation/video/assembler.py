"""Main video assembly engine for VIDMATION.

Orchestrates clip fitting, transitions, audio mixing, caption burn-in,
and final encoding into a single cohesive video file.

Supports multi-clip sections: when a section provides ``media_paths``
(a list of visual assets), the assembler splits the section duration
into 3-5 second sub-clips and interleaves them -- producing the fast-cut
visual style typical of faceless YouTube content.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

import ffmpeg

from vidmation.config.profiles import VideoConfig
from vidmation.utils.ffmpeg import FFmpegError, get_duration
from vidmation.video.audio_mixer import get_audio_duration, mix_voiceover_and_music
from vidmation.video.captions_render import burn_captions, generate_ass_file
from vidmation.video.formats import FormatSpec, get_format

logger = logging.getLogger(__name__)

# Sub-clip duration bounds for multi-clip sections (seconds)
_MIN_SUBCLIP_DURATION = 3.0
_MAX_SUBCLIP_DURATION = 5.0


# ---------------------------------------------------------------------------
# Helpers for section timing
# ---------------------------------------------------------------------------

def _compute_section_timings(
    sections: list[dict],
    word_timestamps: list[dict],
    total_duration: float,
) -> list[dict]:
    """Assign a start/end time to each section based on word timestamps.

    Each *section* dict is expected to have a ``"text"`` key whose word count
    is used to proportionally divide the total voiceover duration.  If the
    sections carry explicit ``"start"``/``"end"`` keys they are used directly.

    Returns:
        A list of dicts with ``"start"`` and ``"end"`` (float seconds) added.
    """
    # If sections already have timing info, honour it
    if sections and "start" in sections[0] and "end" in sections[0]:
        return sections

    # Otherwise, split proportionally by word count
    word_counts = []
    for sec in sections:
        text = sec.get("text", sec.get("narration", ""))
        word_counts.append(max(1, len(text.split())))

    total_words = sum(word_counts)
    cursor = 0.0
    timed: list[dict] = []
    for sec, wc in zip(sections, word_counts):
        duration = (wc / total_words) * total_duration
        entry = dict(sec)
        entry["start"] = cursor
        entry["end"] = cursor + duration
        timed.append(entry)
        cursor += duration

    return timed


def _media_is_image(path: Path) -> bool:
    """Return True if *path* looks like a still image file."""
    return path.suffix.lower() in {
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
    }


# ---------------------------------------------------------------------------
# VideoAssembler
# ---------------------------------------------------------------------------

class VideoAssembler:
    """End-to-end video assembly engine.

    Takes pre-generated assets (media clips, voiceover, word timestamps,
    optional music) and produces a fully rendered video with transitions,
    mixed audio, and burned-in captions.
    """

    def __init__(self, video_config: VideoConfig, work_dir: Path) -> None:
        self.video_config = video_config
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.format_spec: FormatSpec = get_format(video_config.format)
        logger.info(
            "VideoAssembler initialised: format=%s (%s), transition=%s, work_dir=%s",
            self.format_spec.name,
            self.format_spec.resolution,
            video_config.transition,
            self.work_dir,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assemble(
        self,
        sections: list[dict],
        voiceover_path: Path,
        word_timestamps: list[dict],
        music_path: Path | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """Assemble the final video from pipeline artifacts.

        Parameters:
            sections: Ordered list of section dicts.  Each must contain
                ``"media_path"`` (str or Path) pointing to the visual asset
                and ``"text"`` or ``"narration"`` for timing proportions.
                Optionally, ``"media_paths"`` (list of str/Path) provides
                multiple clips for the section.  When present, the section
                duration is split into 3-5 second sub-clips that interleave
                the available media assets for a fast-cut visual style.
            voiceover_path: Path to the voiceover audio file.
            word_timestamps: List of ``{"word": str, "start": float, "end": float}``
                dicts for caption generation.
            music_path: Optional background music file.
            output_path: Where to write the final video.  If ``None``, a path
                is generated inside *work_dir*.

        Returns:
            Path to the rendered video.

        Raises:
            FileNotFoundError: If required input files are missing.
            FFmpegError: On any ffmpeg failure.
            ValueError: If *sections* is empty.
        """
        if not sections:
            raise ValueError("Cannot assemble a video with zero sections")

        voiceover_path = Path(voiceover_path)
        if not voiceover_path.exists():
            raise FileNotFoundError(f"Voiceover not found: {voiceover_path}")

        if output_path is None:
            output_path = self.work_dir / "final_output.mp4"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("=== Video assembly started (%d sections) ===", len(sections))

        # 1. Determine timing
        vo_duration = get_audio_duration(voiceover_path)
        logger.info("Voiceover duration: %.2fs", vo_duration)

        timed_sections = _compute_section_timings(sections, word_timestamps, vo_duration)

        # 2. Prepare individual visual clips
        clip_paths: list[Path] = []
        durations: list[float] = []

        for idx, sec in enumerate(timed_sections):
            sec_dur = sec["end"] - sec["start"]

            # --- Multi-clip path: interleave multiple media assets ----------
            media_paths_raw = sec.get("media_paths")
            if media_paths_raw and len(media_paths_raw) > 1:
                logger.info(
                    "Section %d/%d: %.2fs, multi-clip (%d assets)",
                    idx + 1,
                    len(timed_sections),
                    sec_dur,
                    len(media_paths_raw),
                )

                section_clip = self._render_multi_clip_section(
                    media_paths=[Path(p) for p in media_paths_raw],
                    section_duration=sec_dur,
                    section_idx=idx,
                )
                clip_paths.append(section_clip)

                actual_dur = get_duration(section_clip)
                durations.append(actual_dur)
                if abs(actual_dur - sec_dur) > 0.5:
                    logger.warning(
                        "Section %d: rendered %.2fs vs target %.2fs (delta %.2fs)",
                        idx + 1, actual_dur, sec_dur, actual_dur - sec_dur,
                    )
                continue

            # --- Single-clip path (original behaviour) ----------------------
            media_path = Path(sec["media_path"])
            if not media_path.exists():
                raise FileNotFoundError(
                    f"Media asset not found for section {idx}: {media_path}"
                )

            logger.info(
                "Section %d/%d: %.2fs, media=%s",
                idx + 1,
                len(timed_sections),
                sec_dur,
                media_path.name,
            )

            if _media_is_image(media_path):
                clip_path = self._render_ken_burns(media_path, sec_dur, idx)
            else:
                clip_path = self._render_fitted_clip(media_path, sec_dur, idx)

            clip_paths.append(clip_path)

            # Use the ACTUAL rendered duration, not the target, so xfade
            # offsets are accurate.  Rendered clips may differ from the
            # target due to trimming, speed changes, or Ken Burns rounding.
            actual_dur = get_duration(clip_path)
            durations.append(actual_dur)
            if abs(actual_dur - sec_dur) > 0.5:
                logger.warning(
                    "Section %d: rendered %.2fs vs target %.2fs (delta %.2fs)",
                    idx + 1, actual_dur, sec_dur, actual_dur - sec_dur,
                )

        # 3. Join clips with transitions
        logger.info("Building visual timeline with transition=%s", self.video_config.transition)
        timeline_path = self._build_timeline(clip_paths, durations)

        # 3b. Burn section titles onto the timeline
        headings = [sec.get("heading", "") for sec in timed_sections]
        title_starts = [sec["start"] for sec in timed_sections]
        if any(headings):
            logger.info("Burning %d section title overlays", len([h for h in headings if h]))
            timeline_path = self._burn_section_titles(
                timeline_path, headings, title_starts, durations,
            )

        # 4. Mix audio
        logger.info("Mixing audio (voiceover + music)")
        mixed_audio_path = self.work_dir / "mixed_audio.aac"
        mixed_audio_path = mix_voiceover_and_music(
            voiceover_path=voiceover_path,
            music_path=music_path,
            music_volume=0.15,
            output_path=mixed_audio_path,
        )

        # 5. Combine video + audio
        logger.info("Muxing video + audio")
        muxed_path = self.work_dir / "muxed.mp4"
        self._mux_video_audio(timeline_path, mixed_audio_path, muxed_path)

        # 6. Burn captions
        captioned_path = self.work_dir / "captioned.mp4"
        if word_timestamps:
            logger.info("Generating captions (%d words)", len(word_timestamps))
            ass_path = self.work_dir / "captions.ass"
            generate_ass_file(
                words=word_timestamps,
                output_path=ass_path,
                style=self._resolve_caption_style(),
                animation=self._resolve_caption_animation(),
            )
            logger.info("Burning captions into video")
            burn_captions(muxed_path, ass_path, captioned_path)
        else:
            # No captions -- just copy muxed result
            logger.info("No word timestamps; skipping captions")
            self._copy_file(muxed_path, captioned_path)

        # 7. Apply AIVIDIO watermark (if logo exists)
        watermarked_path = self._apply_watermark(captioned_path, output_path)
        if watermarked_path != output_path:
            # Watermark was skipped or failed -- copy captioned to output
            self._copy_file(captioned_path, output_path)

        logger.info("=== Assembly complete: %s ===", output_path)
        return output_path

    # ------------------------------------------------------------------
    # Internal: clip preparation
    # ------------------------------------------------------------------

    def _render_fitted_clip(
        self,
        clip_path: Path,
        target_duration: float,
        section_idx: int,
    ) -> Path:
        """Trim or speed-adjust a video clip to match *target_duration*.

        The clip is also scaled/padded to match the format resolution.

        Returns:
            Path to the rendered clip segment.
        """
        out_path = self.work_dir / f"section_{section_idx:03d}_video.mp4"
        clip_duration = get_duration(clip_path)
        w, h = self.format_spec.width, self.format_spec.height
        fps = self.format_spec.fps

        # Decide strategy based on clip vs target ratio
        if clip_duration > target_duration * 1.5:
            # Much longer -- trim from a random start point
            max_start = max(0.0, clip_duration - target_duration)
            start_point = random.uniform(0, max_start)
            stream = ffmpeg.input(str(clip_path), ss=start_point, t=target_duration)
        elif clip_duration > target_duration:
            # Slightly longer -- just trim
            stream = ffmpeg.input(str(clip_path), t=target_duration)
        elif clip_duration < target_duration * 0.7:
            # Much shorter -- loop the clip to fill the target duration
            # instead of extreme slow-motion which looks awkward
            stream = ffmpeg.input(str(clip_path), stream_loop=-1)
            logger.debug(
                "Looping clip %s (%.2fs) to fill %.2fs",
                clip_path.name, clip_duration, target_duration,
            )
        elif clip_duration < target_duration:
            # Between 0.7x and 1.0x -- slight slow-down is acceptable
            speed_factor = clip_duration / target_duration
            pts_factor = 1.0 / speed_factor
            stream = ffmpeg.input(str(clip_path))
            stream = stream.video.filter("setpts", f"{pts_factor}*PTS")
        else:
            # Close enough -- minor trim handles the rest
            stream = ffmpeg.input(str(clip_path))

        # Scale + pad to target resolution (letterbox/pillarbox)
        stream = stream.filter(
            "scale",
            w,
            h,
            force_original_aspect_ratio="decrease",
        )
        stream = stream.filter(
            "pad",
            w,
            h,
            "(ow-iw)/2",
            "(oh-ih)/2",
            color="black",
        )
        stream = stream.filter("fps", fps=fps)
        stream = stream.filter("setsar", "1")

        try:
            (
                stream
                .output(
                    str(out_path),
                    vcodec="libx264",
                    crf="20",
                    preset="fast",
                    pix_fmt="yuv420p",
                    t=target_duration,
                    an=None,  # strip audio -- we mix separately
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(
                f"Failed to fit clip {clip_path.name}: {stderr}"
            ) from exc

        logger.debug("Fitted clip: %s -> %s (%.2fs)", clip_path.name, out_path.name, target_duration)
        return out_path

    def _render_ken_burns(
        self,
        image_path: Path,
        duration: float,
        section_idx: int,
    ) -> Path:
        """Apply a Ken Burns (slow zoom + pan) effect to a still image.

        Returns:
            Path to the rendered video segment.
        """
        out_path = self.work_dir / f"section_{section_idx:03d}_image.mp4"
        w, h = self.format_spec.width, self.format_spec.height
        fps = self.format_spec.fps
        total_frames = int(duration * fps)

        # Decide zoom direction: 1.0 -> 1.15 (zoom in) or 1.15 -> 1.0 (zoom out)
        zoom_in = random.choice([True, False])
        if zoom_in:
            zoom_expr = f"min(1+0.15*on/{total_frames},1.15)"
        else:
            zoom_expr = f"max(1.15-0.15*on/{total_frames},1.0)"

        # Gentle pan towards centre
        x_expr = f"iw/2-(iw/zoom/2)+((iw/zoom/2)-iw/2)*on/{total_frames}"
        y_expr = f"ih/2-(ih/zoom/2)+((ih/zoom/2)-ih/2)*on/{total_frames}"

        try:
            (
                ffmpeg
                .input(str(image_path), loop=1, framerate=fps)
                .filter("scale", w * 2, h * 2)  # upscale for headroom
                .filter(
                    "zoompan",
                    z=zoom_expr,
                    x=x_expr,
                    y=y_expr,
                    d=total_frames,
                    s=f"{w}x{h}",
                    fps=fps,
                )
                .filter("setsar", "1")
                .output(
                    str(out_path),
                    vcodec="libx264",
                    crf="20",
                    preset="fast",
                    pix_fmt="yuv420p",
                    t=duration,
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(
                f"Ken Burns effect failed for {image_path.name}: {stderr}"
            ) from exc

        logger.debug("Ken Burns: %s -> %s (%.2fs)", image_path.name, out_path.name, duration)
        return out_path

    # ------------------------------------------------------------------
    # Internal: multi-clip section assembly
    # ------------------------------------------------------------------

    def _render_multi_clip_section(
        self,
        media_paths: list[Path],
        section_duration: float,
        section_idx: int,
    ) -> Path:
        """Render multiple media assets into one section clip by interleaving.

        Splits *section_duration* into sub-clips of 3-5 seconds each and
        assigns each sub-clip to a different media asset.  The assets cycle
        if there are more sub-clips than assets.

        For video assets: trim/fit to the sub-clip duration.
        For image assets: apply Ken Burns effect for the sub-clip duration.

        The rendered sub-clips are concatenated into a single section clip.

        Args:
            media_paths: Paths to the media assets (videos and/or images).
            section_duration: Total duration this section should fill (seconds).
            section_idx: Section index, used for naming intermediate files.

        Returns:
            Path to the concatenated section video.
        """
        out_path = self.work_dir / f"section_{section_idx:03d}_multi.mp4"

        # Filter to only existing files
        valid_paths = [p for p in media_paths if p.exists()]
        if not valid_paths:
            raise FileNotFoundError(
                f"No valid media files found for multi-clip section {section_idx}. "
                f"Checked: {[str(p) for p in media_paths]}"
            )

        if len(valid_paths) < len(media_paths):
            logger.warning(
                "Section %d: %d/%d media files missing, using %d available",
                section_idx,
                len(media_paths) - len(valid_paths),
                len(media_paths),
                len(valid_paths),
            )

        # If only 1 valid file, fall back to single-clip render
        if len(valid_paths) == 1:
            p = valid_paths[0]
            if _media_is_image(p):
                return self._render_ken_burns(p, section_duration, section_idx)
            return self._render_fitted_clip(p, section_duration, section_idx)

        # Compute sub-clip durations: aim for 3-5 seconds each
        target_sub = (_MIN_SUBCLIP_DURATION + _MAX_SUBCLIP_DURATION) / 2.0  # 4s
        num_subclips = max(2, round(section_duration / target_sub))

        # Don't create more sub-clips than we have assets * 2 (avoid too much
        # repetition) and cap at a reasonable maximum
        num_subclips = min(num_subclips, len(valid_paths) * 2, 10)

        # Distribute duration evenly with slight random variation
        base_dur = section_duration / num_subclips
        sub_durations: list[float] = []
        remaining = section_duration

        for i in range(num_subclips):
            if i == num_subclips - 1:
                # Last sub-clip gets whatever remains
                dur = remaining
            else:
                # Add slight variation (+/- 15%) but clamp to bounds
                jitter = random.uniform(-0.15, 0.15)
                dur = base_dur * (1.0 + jitter)
                dur = max(_MIN_SUBCLIP_DURATION, min(_MAX_SUBCLIP_DURATION, dur))
                dur = min(dur, remaining - _MIN_SUBCLIP_DURATION * (num_subclips - i - 1))
            sub_durations.append(dur)
            remaining -= dur

        logger.info(
            "Section %d: splitting %.2fs into %d sub-clips: %s",
            section_idx,
            section_duration,
            num_subclips,
            [f"{d:.1f}s" for d in sub_durations],
        )

        # Render each sub-clip, cycling through assets
        sub_clip_paths: list[Path] = []
        for i, sub_dur in enumerate(sub_durations):
            asset_path = valid_paths[i % len(valid_paths)]
            sub_idx_label = section_idx * 100 + i  # unique index for temp files

            if _media_is_image(asset_path):
                rendered = self._render_ken_burns(asset_path, sub_dur, sub_idx_label)
            else:
                rendered = self._render_fitted_clip(asset_path, sub_dur, sub_idx_label)

            sub_clip_paths.append(rendered)

        # Concatenate sub-clips into the section clip
        if len(sub_clip_paths) == 1:
            self._copy_file(sub_clip_paths[0], out_path)
        else:
            self._concat_clips(sub_clip_paths, out_path)

        logger.info(
            "Multi-clip section %d: %d sub-clips -> %s (%.2fs)",
            section_idx,
            len(sub_clip_paths),
            out_path.name,
            section_duration,
        )
        return out_path

    # ------------------------------------------------------------------
    # Internal: timeline assembly
    # ------------------------------------------------------------------

    def _build_timeline(
        self,
        clip_paths: list[Path],
        durations: list[float],
    ) -> Path:
        """Join rendered clips with the configured transition.

        For ``crossfade`` / ``slide_*`` transitions the ``xfade`` filter is
        chained incrementally.  For ``cut`` / ``fade_black`` a simple concat
        is used with optional per-clip fades.

        Returns:
            Path to the joined video file.
        """
        out_path = self.work_dir / "timeline.mp4"
        transition = self.video_config.transition.lower().strip()
        transition_dur = 0.5  # seconds

        if len(clip_paths) == 1:
            # Single clip -- just copy
            self._copy_file(clip_paths[0], out_path)
            return out_path

        # ---- xfade-based transitions (crossfade, slide_left, slide_right) ----
        if transition in ("crossfade", "slide_left", "slide_right"):
            xfade_type = {
                "crossfade": "fade",
                "slide_left": "slideleft",
                "slide_right": "slideright",
            }[transition]

            streams = [ffmpeg.input(str(p)) for p in clip_paths]
            result = streams[0]
            offset_acc = durations[0] - transition_dur

            for i in range(1, len(streams)):
                result = ffmpeg.filter(
                    [result, streams[i]],
                    "xfade",
                    transition=xfade_type,
                    duration=transition_dur,
                    offset=max(0, offset_acc),
                )
                if i < len(streams) - 1:
                    # Next offset accumulates (current segment minus overlap)
                    offset_acc += durations[i] - transition_dur

            try:
                (
                    result
                    .output(
                        str(out_path),
                        vcodec="libx264",
                        crf="18",
                        preset="medium",
                        pix_fmt="yuv420p",
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            except ffmpeg.Error as exc:
                stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
                raise FFmpegError(f"Timeline xfade failed: {stderr}") from exc

            return out_path

        # ---- fade_black: per-clip fades then concat -------------------------
        if transition == "fade_black":
            faded_paths: list[Path] = []
            for i, (cp, dur) in enumerate(zip(clip_paths, durations)):
                faded_out = self.work_dir / f"faded_{i:03d}.mp4"
                stream = ffmpeg.input(str(cp))
                stream = stream.filter("fade", type="in", start_time=0, duration=0.4)
                fade_start = max(0.0, dur - 0.4)
                stream = stream.filter("fade", type="out", start_time=fade_start, duration=0.4)
                try:
                    (
                        stream
                        .output(
                            str(faded_out),
                            vcodec="libx264",
                            crf="18",
                            preset="fast",
                            pix_fmt="yuv420p",
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                except ffmpeg.Error as exc:
                    stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
                    raise FFmpegError(f"Fade-black failed on clip {i}: {stderr}") from exc
                faded_paths.append(faded_out)

            self._concat_clips(faded_paths, out_path)
            return out_path

        # ---- cut (default): simple concat -----------------------------------
        self._concat_clips(clip_paths, out_path)
        return out_path

    # ------------------------------------------------------------------
    # Internal: concat via ffmpeg concat demuxer
    # ------------------------------------------------------------------

    def _concat_clips(self, clip_paths: list[Path], output_path: Path) -> None:
        """Concatenate clips using the ffmpeg concat demuxer (no re-encode)."""
        concat_list = self.work_dir / "concat_list.txt"
        # Use absolute paths to avoid relative-path resolution issues
        lines = [f"file '{Path(p).resolve()}'" for p in clip_paths]
        concat_list.write_text("\n".join(lines), encoding="utf-8")

        try:
            (
                ffmpeg
                .input(str(concat_list), format="concat", safe=0)
                .output(
                    str(output_path),
                    vcodec="libx264",
                    crf="18",
                    preset="medium",
                    pix_fmt="yuv420p",
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(f"Clip concatenation failed: {stderr}") from exc

    # ------------------------------------------------------------------
    # Internal: mux video + audio
    # ------------------------------------------------------------------

    def _mux_video_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> None:
        """Combine a video stream (no audio) with an audio file."""
        video_stream = ffmpeg.input(str(video_path))
        audio_stream = ffmpeg.input(str(audio_path))

        try:
            (
                ffmpeg
                .output(
                    video_stream.video,
                    audio_stream.audio,
                    str(output_path),
                    vcodec="copy",
                    acodec="aac",
                    audio_bitrate="192k",
                    shortest=None,
                    movflags="+faststart",
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            raise FFmpegError(f"Video+audio mux failed: {stderr}") from exc

    # ------------------------------------------------------------------
    # Internal: caption style resolution
    # ------------------------------------------------------------------

    def _resolve_caption_style(self) -> dict:
        """Build a caption style dict from the VideoConfig."""
        return {
            "font_name": self.video_config.caption_font,
            "font_size": self.video_config.caption_font_size,
            "primary_color": self.video_config.caption_color,
            "outline_color": self.video_config.caption_outline_color,
            "bold": True,
        }

    def _resolve_caption_animation(self) -> str:
        """Choose caption animation based on caption_style config."""
        style = self.video_config.caption_style.lower()
        if style == "karaoke":
            return "karaoke"
        if style in ("pop_in", "pop-in", "popin"):
            return "pop_in"
        return "none"

    # ------------------------------------------------------------------
    # Internal: section title overlays
    # ------------------------------------------------------------------

    def _burn_section_titles(
        self,
        video_path: Path,
        headings: list[str],
        starts: list[float],
        durations: list[float],
    ) -> Path:
        """Burn section heading titles onto the video using drawtext.

        Each title appears for 3 seconds at the start of its section,
        fading in over 0.3s and fading out over 0.5s.  Displayed as
        large bold white text with a dark semi-transparent background box.

        Returns:
            Path to the video with titles burned in.
        """
        import subprocess

        out_path = self.work_dir / "timeline_titled.mp4"

        # Build a chain of drawtext filters -- one per section heading
        # Account for xfade overlaps: accumulate actual start positions
        transition_dur = 0.5
        actual_starts: list[float] = [0.0]
        for i in range(1, len(durations)):
            actual_starts.append(actual_starts[-1] + durations[i - 1] - transition_dur)

        filters: list[str] = []
        for i, heading in enumerate(headings):
            if not heading or not heading.strip():
                continue

            # Escape text for ffmpeg drawtext
            safe_text = (
                heading
                .replace("\\", "\\\\")
                .replace("'", "\u2019")  # smart quote
                .replace(":", "\\:")
                .replace("%", "%%")
            )

            t_start = actual_starts[i] if i < len(actual_starts) else starts[i]
            t_end = t_start + 3.0  # show for 3 seconds
            fade_in_end = t_start + 0.3
            fade_out_start = t_end - 0.5

            # drawtext with background box, fade in/out via alpha
            filters.append(
                f"drawtext=text='{safe_text}'"
                f":fontsize=52"
                f":fontcolor=white"
                f":fontfile=/System/Library/Fonts/Helvetica.ttc"
                f":x=(w-text_w)/2"
                f":y=h*0.15"
                f":box=1"
                f":boxcolor=black@0.6"
                f":boxborderw=20"
                f":enable='between(t,{t_start:.2f},{t_end:.2f})'"
                f":alpha='if(lt(t,{fade_in_end:.2f}),(t-{t_start:.2f})/0.3,"
                f"if(gt(t,{fade_out_start:.2f}),({t_end:.2f}-t)/0.5,1))'"
            )

        if not filters:
            return video_path

        filter_chain = ",".join(filters)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", filter_chain,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(out_path),
        ]

        logger.info("Burning %d section titles", len(filters))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("Title overlay failed, using video without titles: %s",
                          result.stderr[-300:] if result.stderr else "unknown")
            return video_path

        logger.info("Section titles burned: %s", out_path)
        return out_path

    # ------------------------------------------------------------------
    # Internal: file copy
    # ------------------------------------------------------------------

    @staticmethod
    def _copy_file(src: Path, dst: Path) -> None:
        """Copy a file from *src* to *dst*, re-encoding lightly with ffmpeg."""
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
            raise FFmpegError(f"File copy failed ({src} -> {dst}): {stderr}") from exc

    # ------------------------------------------------------------------
    # Internal: watermark overlay
    # ------------------------------------------------------------------

    def _apply_watermark(self, video_path: Path, output_path: Path) -> Path:
        """Overlay the AIVIDIO logo as a semi-transparent watermark.

        The logo is placed in the bottom-right corner with 20px padding,
        scaled to 80px height, and rendered at 30% opacity.

        If the logo file does not exist, the video is returned unchanged.

        Returns:
            Path to the watermarked video (or the original if no logo).
        """
        # Resolve logo path relative to the project assets directory
        logo_path = Path(__file__).resolve().parents[3] / "assets" / "aividio-logo.png"
        if not logo_path.exists():
            logger.warning("AIVIDIO logo not found at %s; skipping watermark", logo_path)
            return video_path

        logger.info("Applying AIVIDIO watermark from %s", logo_path)

        video_stream = ffmpeg.input(str(video_path))
        logo_stream = (
            ffmpeg
            .input(str(logo_path))
            .filter("scale", -1, 80)  # scale to 80px height, preserve aspect ratio
            .filter("colorchannelmixer", aa=0.3)  # 30% opacity
        )

        overlay = ffmpeg.overlay(
            video_stream,
            logo_stream,
            x="W-w-20",  # 20px from right edge
            y="H-h-20",  # 20px from bottom edge
        )

        try:
            (
                overlay
                .output(
                    str(output_path),
                    vcodec="libx264",
                    crf="18",
                    preset="fast",
                    pix_fmt="yuv420p",
                    acodec="copy",
                )
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
            logger.warning("Watermark overlay failed, using video without watermark: %s",
                          stderr[-300:] if stderr else "unknown")
            return video_path

        logger.info("Watermark applied: %s", output_path)
        return output_path
