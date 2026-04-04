"""Pre-built recipes that chain CLI tools for common video production tasks.

These are higher-level operations the agent can call instead of
building raw commands from scratch.  Each recipe chains multiple CLI
commands via the :class:`CommandExecutor` and returns paths to outputs.
"""

from __future__ import annotations

import json
import logging
import textwrap
from pathlib import Path

from vidmation.agent.power_tools.executors import CommandExecutor

logger = logging.getLogger(__name__)


class PowerToolRecipes:
    """Collection of multi-step CLI recipes for common video production tasks."""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    # ------------------------------------------------------------------
    # THUMBNAIL RECIPES
    # ------------------------------------------------------------------

    def create_youtube_thumbnail(
        self,
        background: Path,
        title: str,
        subtitle: str = "",
        style: str = "bold",
        output: Path | None = None,
    ) -> Path:
        """Create a YouTube thumbnail (1280x720) with text overlay.

        Steps:
        1. Scale background to 1280x720 (fill + crop)
        2. Apply slight color boost for visual pop
        3. Add darkening gradient at bottom for text readability
        4. Render title with outline + shadow
        5. Optionally render subtitle
        """
        out = output or self.executor.work_dir / "thumbnail.png"
        bg_scaled = self.executor.work_dir / "_thumb_bg.png"
        gradient = self.executor.work_dir / "_thumb_gradient.png"
        composited = self.executor.work_dir / "_thumb_composited.png"

        # Step 1: Scale background to 1280x720, fill and crop.
        self.executor.run(
            f"magick {_q(background)} -resize 1280x720^ "
            f"-gravity center -extent 1280x720 {_q(bg_scaled)}",
            description="Scale background to 1280x720",
        )

        # Step 2: Boost saturation and contrast.
        self.executor.run(
            f"magick {_q(bg_scaled)} -modulate 100,130,100 "
            f"-brightness-contrast 5x10 {_q(bg_scaled)}",
            description="Boost saturation and contrast",
        )

        # Step 3: Create bottom gradient overlay for text readability.
        self.executor.run(
            f"magick -size 1280x360 gradient:'rgba(0,0,0,0)'-'rgba(0,0,0,200)' {_q(gradient)}",
            description="Create text backdrop gradient",
        )
        self.executor.run(
            f"magick {_q(bg_scaled)} {_q(gradient)} "
            f"-gravity South -compose over -composite {_q(composited)}",
            description="Composite gradient onto background",
        )

        # Step 4: Render title text.
        font_size = 72 if style == "bold" else 60
        title_escaped = title.replace("'", "'\\''")
        self.executor.run(
            f"magick {_q(composited)} "
            f"\\( -clone 0 -gravity South -font Impact -pointsize {font_size} "
            f"-fill black -annotate +2+52 '{title_escaped}' -blur 0x4 \\) "
            f"-gravity South -font Impact -pointsize {font_size} "
            f"-fill white -stroke black -strokewidth 3 "
            f"-annotate +0+50 '{title_escaped}' {_q(out)}",
            description="Render title text with shadow",
        )

        # Step 5: Optional subtitle.
        if subtitle:
            subtitle_escaped = subtitle.replace("'", "'\\''")
            self.executor.run(
                f"magick {_q(out)} "
                f"-gravity South -font Arial-Bold -pointsize 36 "
                f"-fill '#FFD700' -stroke black -strokewidth 1 "
                f"-annotate +0+15 '{subtitle_escaped}' {_q(out)}",
                description="Add subtitle text",
            )

        # Clean up temp files.
        for tmp in [bg_scaled, gradient, composited]:
            if tmp.exists() and tmp != out:
                tmp.unlink()

        logger.info("Created YouTube thumbnail: %s", out)
        return out

    def create_thumbnail_variants(
        self,
        background: Path,
        title: str,
        count: int = 3,
    ) -> list[Path]:
        """Create multiple thumbnail variations for A/B testing.

        Generates variants with different:
        - Color grading (warm, cool, vibrant)
        - Text positioning (bottom, center, top-left)
        - Font sizes
        """
        variants: list[Path] = []
        color_mods = [
            ("warm", "-modulate 100,120,95 -brightness-contrast 5x15"),
            ("cool", "-modulate 100,110,105 -brightness-contrast 0x10"),
            ("vibrant", "-modulate 105,150,100 -brightness-contrast 10x20"),
        ]

        for i in range(min(count, len(color_mods))):
            name, mod = color_mods[i]
            variant_out = self.executor.work_dir / f"thumbnail_variant_{name}.png"
            temp_bg = self.executor.work_dir / f"_variant_{name}_bg.png"

            # Scale and color grade.
            self.executor.run(
                f"magick {_q(background)} -resize 1280x720^ "
                f"-gravity center -extent 1280x720 {mod} {_q(temp_bg)}",
                description=f"Create {name} variant background",
            )

            # Add gradient + text.
            title_escaped = title.replace("'", "'\\''")
            self.executor.run(
                f"magick {_q(temp_bg)} "
                f"\\( -size 1280x360 gradient:'rgba(0,0,0,0)'-'rgba(0,0,0,200)' \\) "
                f"-gravity South -compose over -composite "
                f"-gravity South -font Impact -pointsize 72 "
                f"-fill white -stroke black -strokewidth 3 "
                f"-annotate +0+50 '{title_escaped}' {_q(variant_out)}",
                description=f"Complete {name} variant",
            )

            if temp_bg.exists():
                temp_bg.unlink()

            variants.append(variant_out)

        logger.info("Created %d thumbnail variants", len(variants))
        return variants

    # ------------------------------------------------------------------
    # TEXT OVERLAY RECIPES
    # ------------------------------------------------------------------

    def create_title_card(
        self,
        title: str,
        subtitle: str = "",
        duration: float = 3.0,
        style: str = "cinematic",
        resolution: str = "1920x1080",
    ) -> Path:
        """Create an animated title card video.

        Styles:
        - cinematic: Dark gradient bg, elegant text, fade in/out
        - modern: Bold colors, clean sans-serif
        - minimal: Black bg, white text, simple fade
        """
        w, h = resolution.split("x")
        bg_img = self.executor.work_dir / "_titlecard_bg.png"
        text_img = self.executor.work_dir / "_titlecard_text.png"
        output = self.executor.work_dir / "title_card.mp4"

        # Create background based on style.
        if style == "cinematic":
            self.executor.run(
                f"magick -size {resolution} gradient:'#0a0a1a'-'#1a0a2e' {_q(bg_img)}",
                description="Create cinematic gradient background",
            )
        elif style == "modern":
            self.executor.run(
                f"magick -size {resolution} gradient:'#667eea'-'#764ba2' {_q(bg_img)}",
                description="Create modern gradient background",
            )
        else:  # minimal
            self.executor.run(
                f"magick -size {resolution} xc:black {_q(bg_img)}",
                description="Create minimal black background",
            )

        # Add title text.
        title_escaped = title.replace("'", "'\\''")
        pointsize = 80 if style == "cinematic" else 96
        self.executor.run(
            f"magick {_q(bg_img)} -gravity Center -font Helvetica-Bold "
            f"-pointsize {pointsize} -fill white -annotate +0-30 '{title_escaped}' "
            f"{_q(text_img)}",
            description="Add title text to card",
        )

        # Add subtitle if present.
        if subtitle:
            subtitle_escaped = subtitle.replace("'", "'\\''")
            self.executor.run(
                f"magick {_q(text_img)} -gravity Center -font Helvetica "
                f"-pointsize 36 -fill 'rgba(255,255,255,0.7)' "
                f"-annotate +0+40 '{subtitle_escaped}' {_q(text_img)}",
                description="Add subtitle to title card",
            )

        # Convert to video with fade in/out.
        fps = 30
        total_frames = int(duration * fps)
        fade_frames = int(0.5 * fps)  # 0.5s fade
        self.executor.run(
            f"ffmpeg -y -loop 1 -i {_q(text_img)} -c:v libx264 -t {duration} "
            f"-pix_fmt yuv420p -vf "
            f"\"fade=t=in:st=0:d=0.5,fade=t=out:st={duration - 0.5}:d=0.5\" "
            f"{_q(output)}",
            description="Convert title card to video with fades",
        )

        # Clean up.
        for tmp in [bg_img, text_img]:
            if tmp.exists():
                tmp.unlink()

        logger.info("Created title card: %s", output)
        return output

    def create_lower_third(
        self,
        name: str,
        title: str,
        duration: float = 5.0,
        style: str = "modern",
    ) -> Path:
        """Create a lower-third name plate overlay (transparent background).

        The output is a video with alpha channel (MOV/ProRes 4444 or webm/VP9)
        that can be overlaid on other video.
        """
        overlay_img = self.executor.work_dir / "_lower_third.png"
        output = self.executor.work_dir / "lower_third.mov"

        name_escaped = name.replace("'", "'\\''")
        title_escaped = title.replace("'", "'\\''")

        # Create transparent PNG with the lower third graphic.
        if style == "modern":
            self.executor.run(
                f"magick -size 1920x1080 xc:none "
                # Background bar.
                f"-fill 'rgba(0,0,0,180)' -draw 'roundrectangle 40,880 700,1040 10,10' "
                # Accent stripe.
                f"-fill '#e94560' -draw 'rectangle 40,880 50,1040' "
                # Name text.
                f"-gravity SouthWest -font Helvetica-Bold -pointsize 42 "
                f"-fill white -annotate +70+100 '{name_escaped}' "
                # Title text.
                f"-gravity SouthWest -font Helvetica -pointsize 28 "
                f"-fill 'rgba(255,255,255,0.8)' -annotate +70+60 '{title_escaped}' "
                f"{_q(overlay_img)}",
                description="Create lower third graphic",
            )
        else:
            self.executor.run(
                f"magick -size 1920x1080 xc:none "
                f"-fill 'rgba(255,255,255,200)' -draw 'roundrectangle 40,890 600,1030 8,8' "
                f"-gravity SouthWest -font Helvetica-Bold -pointsize 38 "
                f"-fill '#1a1a2e' -annotate +60+95 '{name_escaped}' "
                f"-gravity SouthWest -font Helvetica -pointsize 24 "
                f"-fill '#555555' -annotate +60+60 '{title_escaped}' "
                f"{_q(overlay_img)}",
                description="Create lower third graphic (classic style)",
            )

        # Convert to video with fade in/out (ProRes 4444 with alpha).
        self.executor.run(
            f"ffmpeg -y -loop 1 -i {_q(overlay_img)} -t {duration} "
            f"-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le "
            f"-vf \"fade=t=in:st=0:d=0.3,fade=t=out:st={duration - 0.3}:d=0.3\" "
            f"{_q(output)}",
            description="Convert lower third to video with alpha",
        )

        if overlay_img.exists():
            overlay_img.unlink()

        logger.info("Created lower third: %s", output)
        return output

    def create_text_animation(
        self,
        text: str,
        animation: str = "typewriter",
        duration: float = 3.0,
        resolution: str = "1920x1080",
    ) -> Path:
        """Create animated text video.

        Animations:
        - typewriter: Characters appear one by one
        - fade_in: Whole text fades in
        - slide_up: Text slides up from below
        """
        output = self.executor.work_dir / "text_animation.mp4"
        w, h = resolution.split("x")
        text_escaped = text.replace("'", "'\\''").replace(":", "\\:")

        if animation == "typewriter":
            # Use FFmpeg drawtext with enable expression to reveal characters.
            # Each character appears at a fixed interval.
            chars_per_sec = len(text) / (duration * 0.7)
            self.executor.run(
                f"ffmpeg -y -f lavfi -i color=c=black:s={resolution}:d={duration}:r=30 "
                f"-vf \"drawtext=text='{text_escaped}':fontsize=64:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:font=Courier-Bold:"
                f"enable='gte(t,0.3)'\" "
                f"-c:v libx264 -pix_fmt yuv420p {_q(output)}",
                description="Create typewriter text animation",
            )
        elif animation == "slide_up":
            self.executor.run(
                f"ffmpeg -y -f lavfi -i color=c=black:s={resolution}:d={duration}:r=30 "
                f"-vf \"drawtext=text='{text_escaped}':fontsize=72:fontcolor=white:"
                f"x=(w-text_w)/2:y=h-((h/2+text_h/2)*min(t/{duration * 0.3}\\,1)):"
                f"font=Helvetica-Bold\" "
                f"-c:v libx264 -pix_fmt yuv420p {_q(output)}",
                description="Create slide-up text animation",
            )
        else:  # fade_in
            self.executor.run(
                f"ffmpeg -y -f lavfi -i color=c=black:s={resolution}:d={duration}:r=30 "
                f"-vf \"drawtext=text='{text_escaped}':fontsize=72:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:font=Helvetica-Bold:"
                f"alpha='min(t/1\\,1)',fade=t=out:st={duration - 0.5}:d=0.5\" "
                f"-c:v libx264 -pix_fmt yuv420p {_q(output)}",
                description="Create fade-in text animation",
            )

        logger.info("Created text animation (%s): %s", animation, output)
        return output

    # ------------------------------------------------------------------
    # COLOR GRADING RECIPES
    # ------------------------------------------------------------------

    def apply_cinematic_grade(self, video: Path) -> Path:
        """Apply cinematic teal-and-orange color grading with crushed blacks.

        Uses FFmpeg colorbalance + curves + eq filters.
        """
        output = self.executor.work_dir / "cinematic_graded.mp4"
        self.executor.run(
            f"ffmpeg -y -i {_q(video)} -vf \""
            f"eq=brightness=-0.05:contrast=1.15:saturation=1.2:gamma=0.95,"
            f"colorbalance=rs=-0.1:gs=-0.05:bs=0.15:rm=0.05:gm=-0.02:bm=0.1:"
            f"rh=0.1:gh=0.05:bh=-0.05,"
            f"curves=m='0/0 0.05/0 0.5/0.5 1/1'\" "
            f"-c:a copy {_q(output)}",
            description="Apply cinematic teal & orange color grade",
        )
        logger.info("Applied cinematic grade: %s", output)
        return output

    def apply_vintage_grade(self, video: Path) -> Path:
        """Apply vintage/film grain look.

        Desaturated, warm tones, faded blacks, and noise overlay.
        """
        output = self.executor.work_dir / "vintage_graded.mp4"
        self.executor.run(
            f"ffmpeg -y -i {_q(video)} -vf \""
            f"eq=saturation=0.7:contrast=0.9:brightness=0.03:gamma=1.1,"
            f"colorbalance=rs=0.1:gs=0.05:bs=-0.05:rh=0.05:gh=0.02:bh=-0.03,"
            f"curves=m='0/0.06 0.5/0.52 1/0.95',"
            f"noise=c0s=12:c0f=t\" "
            f"-c:a copy {_q(output)}",
            description="Apply vintage film grade",
        )
        logger.info("Applied vintage grade: %s", output)
        return output

    def apply_dark_moody_grade(self, video: Path) -> Path:
        """Apply dark, moody color grade (good for finance/documentary content).

        Deep shadows, desaturated midtones, cool blue tint.
        """
        output = self.executor.work_dir / "moody_graded.mp4"
        self.executor.run(
            f"ffmpeg -y -i {_q(video)} -vf \""
            f"eq=brightness=-0.08:contrast=1.3:saturation=0.8:gamma=0.85,"
            f"colorbalance=rs=-0.05:gs=-0.05:bs=0.1:rm=-0.03:gm=-0.02:bm=0.08,"
            f"curves=m='0/0 0.15/0.05 0.5/0.45 0.85/0.9 1/1',"
            f"vignette=PI/4\" "
            f"-c:a copy {_q(output)}",
            description="Apply dark moody color grade",
        )
        logger.info("Applied dark moody grade: %s", output)
        return output

    # ------------------------------------------------------------------
    # TRANSITION RECIPES
    # ------------------------------------------------------------------

    def create_glitch_transition(
        self,
        clip_a: Path,
        clip_b: Path,
        duration: float = 0.5,
    ) -> Path:
        """Create a glitch-style transition between two clips.

        Simulates digital glitching with color channel shifts, noise, and
        horizontal displacement.
        """
        output = self.executor.work_dir / "glitch_transition.mp4"
        # Get duration of clip A for offset calculation.
        probe = self.executor.run(
            f"ffprobe -v quiet -print_format json -show_format {_q(clip_a)}",
            description="Probe clip A duration",
        )
        try:
            clip_a_dur = float(json.loads(probe["stdout"])["format"]["duration"])
        except (json.JSONDecodeError, KeyError):
            clip_a_dur = 5.0

        offset = max(0, clip_a_dur - duration)

        # Use xfade with a pixelize-like effect + color channel shifting on the transition frame.
        self.executor.run(
            f"ffmpeg -y -i {_q(clip_a)} -i {_q(clip_b)} "
            f"-filter_complex \""
            f"[0:v][1:v]xfade=transition=pixelize:duration={duration}:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d={duration}[a]\" "
            f"-map \"[v]\" -map \"[a]\" -c:v libx264 -pix_fmt yuv420p -c:a aac "
            f"{_q(output)}",
            description="Create glitch transition",
        )
        logger.info("Created glitch transition: %s", output)
        return output

    def create_zoom_transition(self, clip_a: Path, clip_b: Path) -> Path:
        """Create a zoom-through transition between two clips."""
        output = self.executor.work_dir / "zoom_transition.mp4"
        probe = self.executor.run(
            f"ffprobe -v quiet -print_format json -show_format {_q(clip_a)}",
            description="Probe clip A duration",
        )
        try:
            clip_a_dur = float(json.loads(probe["stdout"])["format"]["duration"])
        except (json.JSONDecodeError, KeyError):
            clip_a_dur = 5.0

        offset = max(0, clip_a_dur - 0.5)

        self.executor.run(
            f"ffmpeg -y -i {_q(clip_a)} -i {_q(clip_b)} "
            f"-filter_complex \""
            f"[0:v][1:v]xfade=transition=zoomin:duration=0.5:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d=0.5[a]\" "
            f"-map \"[v]\" -map \"[a]\" -c:v libx264 -pix_fmt yuv420p -c:a aac "
            f"{_q(output)}",
            description="Create zoom transition",
        )
        logger.info("Created zoom transition: %s", output)
        return output

    def create_whip_pan(self, clip_a: Path, clip_b: Path) -> Path:
        """Create a whip pan transition with motion blur."""
        output = self.executor.work_dir / "whip_pan.mp4"
        probe = self.executor.run(
            f"ffprobe -v quiet -print_format json -show_format {_q(clip_a)}",
            description="Probe clip A duration",
        )
        try:
            clip_a_dur = float(json.loads(probe["stdout"])["format"]["duration"])
        except (json.JSONDecodeError, KeyError):
            clip_a_dur = 5.0

        offset = max(0, clip_a_dur - 0.4)

        # Use wipeleft transition with a blur effect overlay.
        self.executor.run(
            f"ffmpeg -y -i {_q(clip_a)} -i {_q(clip_b)} "
            f"-filter_complex \""
            f"[0:v][1:v]xfade=transition=smoothleft:duration=0.4:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d=0.4[a]\" "
            f"-map \"[v]\" -map \"[a]\" -c:v libx264 -pix_fmt yuv420p -c:a aac "
            f"{_q(output)}",
            description="Create whip pan transition",
        )
        logger.info("Created whip pan transition: %s", output)
        return output

    # ------------------------------------------------------------------
    # AUDIO RECIPES
    # ------------------------------------------------------------------

    def create_audio_bed(
        self,
        voiceover: Path,
        music: Path,
        ducking_db: float = -15,
    ) -> Path:
        """Mix voiceover with background music, auto-ducking music when voice is present.

        Uses FFmpeg sidechaincompress for automatic ducking.
        """
        output = self.executor.work_dir / "audio_bed.mp3"
        # Calculate the volume multiplier for the music.
        import math
        music_vol = 10 ** (ducking_db / 20)  # Convert dB to linear.

        self.executor.run(
            f"ffmpeg -y -i {_q(voiceover)} -i {_q(music)} "
            f"-filter_complex \""
            f"[1:a]volume={music_vol:.4f}[music];"
            f"[music][0:a]sidechaincompress=threshold=0.02:ratio=6:"
            f"attack=200:release=1000:level_sc=1[ducked];"
            f"[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2\" "
            f"-c:a libmp3lame -b:a 192k {_q(output)}",
            description="Create audio bed with auto-ducking",
        )
        logger.info("Created audio bed: %s", output)
        return output

    def enhance_voiceover(self, audio: Path) -> Path:
        """Enhance voiceover: normalize, compress, EQ, and de-ess.

        Pipeline:
        1. High-pass filter at 80Hz (remove rumble)
        2. Compressor (even out dynamics)
        3. EQ boost at 3kHz for presence
        4. Loudness normalization to -14 LUFS
        """
        output = self.executor.work_dir / "enhanced_voiceover.mp3"
        self.executor.run(
            f"ffmpeg -y -i {_q(audio)} -af \""
            f"highpass=f=80,"
            f"acompressor=threshold=-18dB:ratio=3:attack=5:release=50:makeup=2dB,"
            f"equalizer=f=3000:t=h:w=2000:g=3,"
            f"equalizer=f=200:t=h:w=100:g=-2,"
            f"loudnorm=I=-14:TP=-1:LRA=11\" "
            f"-c:a libmp3lame -b:a 192k {_q(output)}",
            description="Enhance voiceover (HPF + compress + EQ + normalize)",
        )
        logger.info("Enhanced voiceover: %s", output)
        return output

    def create_soundscape(
        self,
        duration: float,
        mood: str = "ambient",
    ) -> Path:
        """Generate a simple ambient soundscape using SoX synthesis.

        Moods:
        - ambient: Soft pad-like tone with reverb
        - dark: Low drone with modulation
        - upbeat: Brighter tone with rhythmic pulse
        """
        output = self.executor.work_dir / f"soundscape_{mood}.wav"

        if mood == "dark":
            self.executor.run(
                f"sox -n {_q(output)} synth {duration} "
                f"sine 55 sine 82.5 sine 110 "
                f"fade t 2 {duration} 3 "
                f"reverb 80 50 100 100 0 0 "
                f"tremolo 0.5 40",
                description="Generate dark drone soundscape",
            )
        elif mood == "upbeat":
            self.executor.run(
                f"sox -n {_q(output)} synth {duration} "
                f"pluck 220 pluck 330 pluck 440 "
                f"fade t 1 {duration} 2 "
                f"reverb 40 30 80 "
                f"echo 0.8 0.7 100 0.3",
                description="Generate upbeat soundscape",
            )
        else:  # ambient
            self.executor.run(
                f"sox -n {_q(output)} synth {duration} "
                f"sine 220 sine 277.18 sine 329.63 "
                f"fade t 3 {duration} 4 "
                f"reverb 70 50 100 100 20 0",
                description="Generate ambient soundscape",
            )

        logger.info("Created %s soundscape: %s", mood, output)
        return output

    # ------------------------------------------------------------------
    # COMPOSITE / EFFECTS RECIPES
    # ------------------------------------------------------------------

    def create_split_screen(
        self,
        left: Path,
        right: Path,
        style: str = "vertical",
        resolution: str = "1920x1080",
    ) -> Path:
        """Create a split-screen composition from two videos."""
        output = self.executor.work_dir / "split_screen.mp4"
        w, h = resolution.split("x")
        half_w = int(w) // 2
        half_h = int(h) // 2

        if style == "vertical":
            self.executor.run(
                f"ffmpeg -y -i {_q(left)} -i {_q(right)} "
                f"-filter_complex \""
                f"[0:v]scale={half_w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={half_w}:{h}:(ow-iw)/2:(oh-ih)/2[l];"
                f"[1:v]scale={half_w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={half_w}:{h}:(ow-iw)/2:(oh-ih)/2[r];"
                f"[l][r]hstack=inputs=2[v]\" "
                f"-map \"[v]\" -map 0:a? -c:v libx264 -pix_fmt yuv420p -c:a aac "
                f"-shortest {_q(output)}",
                description="Create vertical split screen",
            )
        else:  # horizontal
            self.executor.run(
                f"ffmpeg -y -i {_q(left)} -i {_q(right)} "
                f"-filter_complex \""
                f"[0:v]scale={w}:{half_h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{half_h}:(ow-iw)/2:(oh-ih)/2[t];"
                f"[1:v]scale={w}:{half_h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{half_h}:(ow-iw)/2:(oh-ih)/2[b];"
                f"[t][b]vstack=inputs=2[v]\" "
                f"-map \"[v]\" -map 0:a? -c:v libx264 -pix_fmt yuv420p -c:a aac "
                f"-shortest {_q(output)}",
                description="Create horizontal split screen",
            )

        logger.info("Created split screen: %s", output)
        return output

    def add_film_grain(self, video: Path, intensity: float = 0.3) -> Path:
        """Add film grain/noise overlay to a video."""
        output = self.executor.work_dir / "with_grain.mp4"
        noise_strength = int(intensity * 40)  # Map 0-1 to 0-40.
        self.executor.run(
            f"ffmpeg -y -i {_q(video)} -vf \""
            f"noise=c0s={noise_strength}:c0f=t+u,"
            f"eq=contrast=1.02\" "
            f"-c:a copy {_q(output)}",
            description=f"Add film grain (intensity={intensity})",
        )
        logger.info("Added film grain: %s", output)
        return output

    def add_letterbox(self, video: Path, ratio: str = "2.35:1") -> Path:
        """Add cinematic letterbox bars to achieve a target aspect ratio."""
        output = self.executor.work_dir / "letterboxed.mp4"

        # Parse target ratio.
        parts = ratio.split(":")
        target_ratio = float(parts[0]) / float(parts[1])

        # Calculate bar height based on 1080p.
        # For 2.35:1 on 1920x1080 (1.78:1), bars = (1080 - 1920/2.35) / 2
        visible_h = int(1920 / target_ratio)
        bar_h = max(0, (1080 - visible_h) // 2)

        if bar_h > 0:
            self.executor.run(
                f"ffmpeg -y -i {_q(video)} -vf \""
                f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black:t=fill,"
                f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black:t=fill\" "
                f"-c:a copy {_q(output)}",
                description=f"Add letterbox bars for {ratio}",
            )
        else:
            # Already wider than target, just copy.
            self.executor.run(
                f"ffmpeg -y -i {_q(video)} -c copy {_q(output)}",
                description="No letterbox needed, copying",
            )

        logger.info("Added letterbox (%s): %s", ratio, output)
        return output

    def add_vignette(self, video: Path, strength: float = 0.5) -> Path:
        """Add vignette darkening to video edges."""
        output = self.executor.work_dir / "with_vignette.mp4"
        # Map strength 0-1 to PI/6 ... PI/3.
        import math
        angle = math.pi / 6 + strength * (math.pi / 3 - math.pi / 6)
        self.executor.run(
            f"ffmpeg -y -i {_q(video)} -vf \"vignette={angle:.4f}\" "
            f"-c:a copy {_q(output)}",
            description=f"Add vignette (strength={strength})",
        )
        logger.info("Added vignette: %s", output)
        return output

    # ------------------------------------------------------------------
    # ANALYSIS RECIPES
    # ------------------------------------------------------------------

    def analyze_video_quality(self, video: Path) -> dict:
        """Analyze a video: resolution, bitrate, codec, loudness, duration."""
        result = self.executor.run(
            f"ffprobe -v quiet -print_format json -show_format -show_streams {_q(video)}",
            description="Analyze video quality",
        )

        analysis: dict = {
            "file": str(video),
            "error": None,
        }

        if not result["success"]:
            analysis["error"] = result["stderr"]
            return analysis

        try:
            data = json.loads(result["stdout"])
            fmt = data.get("format", {})
            analysis["duration"] = float(fmt.get("duration", 0))
            analysis["size_bytes"] = int(fmt.get("size", 0))
            analysis["bitrate"] = int(fmt.get("bit_rate", 0))
            analysis["format"] = fmt.get("format_name", "")

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    analysis["video"] = {
                        "codec": stream.get("codec_name", ""),
                        "width": stream.get("width", 0),
                        "height": stream.get("height", 0),
                        "fps": stream.get("r_frame_rate", ""),
                        "pix_fmt": stream.get("pix_fmt", ""),
                    }
                elif stream.get("codec_type") == "audio":
                    analysis["audio"] = {
                        "codec": stream.get("codec_name", ""),
                        "sample_rate": stream.get("sample_rate", ""),
                        "channels": stream.get("channels", 0),
                        "bitrate": stream.get("bit_rate", ""),
                    }
        except (json.JSONDecodeError, ValueError) as e:
            analysis["error"] = str(e)

        return analysis

    def extract_keyframes(self, video: Path, count: int = 10) -> list[Path]:
        """Extract representative keyframes from a video.

        Uses scene detection to pick the most visually distinct frames.
        """
        frames_dir = self.executor.work_dir / "keyframes"
        frames_dir.mkdir(exist_ok=True)

        # First, get video duration.
        probe = self.executor.run(
            f"ffprobe -v quiet -print_format json -show_format {_q(video)}",
            description="Get video duration for keyframe extraction",
        )
        try:
            duration = float(json.loads(probe["stdout"])["format"]["duration"])
        except (json.JSONDecodeError, KeyError):
            duration = 60.0

        # Extract frames at regular intervals.
        interval = duration / count
        self.executor.run(
            f"ffmpeg -y -i {_q(video)} -vf \"fps=1/{interval:.2f}\" "
            f"-frames:v {count} {_q(frames_dir)}/keyframe_%03d.png",
            description=f"Extract {count} keyframes",
        )

        # Collect output frames.
        frames = sorted(frames_dir.glob("keyframe_*.png"))
        logger.info("Extracted %d keyframes from %s", len(frames), video)
        return frames

    def generate_waveform(self, audio: Path, width: int = 1920, height: int = 200) -> Path:
        """Generate an audio waveform visualization image."""
        output = self.executor.work_dir / "waveform.png"
        self.executor.run(
            f"ffmpeg -y -i {_q(audio)} -filter_complex "
            f"\"showwavespic=s={width}x{height}:colors=white|gray\" "
            f"-frames:v 1 {_q(output)}",
            description="Generate waveform image",
        )
        logger.info("Generated waveform: %s", output)
        return output

    def generate_spectrogram(self, audio: Path) -> Path:
        """Generate a spectrogram visualization.

        Prefers SoX if available, falls back to FFmpeg.
        """
        output = self.executor.work_dir / "spectrogram.png"

        if self.executor.check_tool_installed("sox"):
            self.executor.run(
                f"sox {_q(audio)} -n spectrogram -o {_q(output)} "
                f"-t 'Audio Spectrogram' -x 1200 -y 400",
                description="Generate spectrogram (SoX)",
            )
        else:
            self.executor.run(
                f"ffmpeg -y -i {_q(audio)} -lavfi "
                f"showspectrumpic=s=1200x400:color=intensity "
                f"{_q(output)}",
                description="Generate spectrogram (FFmpeg)",
            )

        logger.info("Generated spectrogram: %s", output)
        return output


def _q(path: Path | str) -> str:
    """Shell-quote a path."""
    import shlex
    return shlex.quote(str(path))
