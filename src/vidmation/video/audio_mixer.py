"""Audio mixing module -- voiceover + background music composition.

All heavy lifting is done through ffmpeg-python so the pipeline stays
consistent with the rest of the video assembly engine.
"""

from __future__ import annotations

import logging
from pathlib import Path

import ffmpeg

from vidmation.utils.ffmpeg import FFmpegError, get_duration

logger = logging.getLogger(__name__)


def get_audio_duration(audio_path: Path) -> float:
    """Return the duration of an audio file in seconds.

    Convenience wrapper that delegates to :func:`vidmation.utils.ffmpeg.get_duration`.

    Raises:
        FileNotFoundError: If *audio_path* does not exist.
        FFmpegError: If the duration cannot be determined.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    return get_duration(audio_path)


def normalize_audio(
    audio_path: Path,
    target_lufs: float = -16.0,
    output_path: Path | None = None,
) -> Path:
    """Loudness-normalize an audio file to *target_lufs* using the EBU R128 two-pass method.

    Parameters:
        audio_path: Input audio file.
        target_lufs: Target integrated loudness in LUFS (default -16).
        output_path: Where to write the normalised file.  Defaults to
            ``<stem>_normalized<suffix>`` next to the original.

    Returns:
        Path to the normalised audio file.

    Raises:
        FileNotFoundError: If *audio_path* does not exist.
        FFmpegError: On ffmpeg failure.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if output_path is None:
        output_path = audio_path.with_stem(f"{audio_path.stem}_normalized")

    logger.info("Normalizing %s to %.1f LUFS -> %s", audio_path.name, target_lufs, output_path)

    try:
        (
            ffmpeg
            .input(str(audio_path))
            .filter(
                "loudnorm",
                I=target_lufs,
                TP=-1.5,
                LRA=11,
                print_format="summary",
            )
            .output(str(output_path), ar=44100, acodec="aac", audio_bitrate="192k")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else "unknown error"
        raise FFmpegError(f"Audio normalization failed: {stderr}") from exc

    logger.info("Normalization complete: %s", output_path)
    return output_path


def mix_voiceover_and_music(
    voiceover_path: Path,
    music_path: Path | None,
    music_volume: float = 0.15,
    output_path: Path | None = None,
    music_fade_in: float = 1.0,
    music_fade_out: float = 2.0,
) -> Path:
    """Mix a voiceover track with optional background music.

    Behaviour:
    - If *music_path* is ``None`` or does not exist, the voiceover is copied
      as-is (or re-encoded to AAC for consistency).
    - Music is looped if it is shorter than the voiceover.
    - Music volume is attenuated to *music_volume* (0.0 -- 1.0).
    - A fade-in and fade-out are applied to the music track.

    Parameters:
        voiceover_path: Path to the voiceover audio file.
        music_path: Optional path to the background music file.
        music_volume: Music loudness relative to full scale (0.0 -- 1.0).
        output_path: Destination for the mixed file.
        music_fade_in: Seconds of fade-in at the start of the music.
        music_fade_out: Seconds of fade-out at the end of the music.

    Returns:
        Path to the mixed audio file.

    Raises:
        FileNotFoundError: If *voiceover_path* does not exist.
        FFmpegError: On ffmpeg failure.
    """
    voiceover_path = Path(voiceover_path)
    if not voiceover_path.exists():
        raise FileNotFoundError(f"Voiceover not found: {voiceover_path}")

    if output_path is None:
        output_path = voiceover_path.with_stem(f"{voiceover_path.stem}_mixed")

    # --- No music -- just re-encode voiceover for format consistency ----------
    if music_path is None or not Path(music_path).exists():
        logger.info("No music track; copying voiceover -> %s", output_path)
        try:
            (
                ffmpeg
                .input(str(voiceover_path))
                .output(str(output_path), acodec="aac", audio_bitrate="192k", ar=44100)
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode(errors="replace") if exc.stderr else "unknown error"
            raise FFmpegError(f"Voiceover copy failed: {stderr}") from exc
        return output_path

    music_path = Path(music_path)
    logger.info(
        "Mixing voiceover (%s) + music (%s) at volume=%.2f",
        voiceover_path.name,
        music_path.name,
        music_volume,
    )

    vo_duration = get_audio_duration(voiceover_path)
    music_duration = get_audio_duration(music_path)

    # --- Build the music stream with looping, volume ducking, and fades ------
    # Loop the music enough times to cover the voiceover, then trim.
    loop_count = int(vo_duration / music_duration) + 1 if music_duration > 0 else 1

    music_stream = ffmpeg.input(str(music_path), stream_loop=loop_count)
    music_stream = music_stream.filter("atrim", duration=vo_duration)
    music_stream = music_stream.filter("asetpts", "PTS-STARTPTS")

    # Apply volume
    music_stream = music_stream.filter("volume", volume=music_volume)

    # Apply fade-in
    if music_fade_in > 0:
        music_stream = music_stream.filter(
            "afade", type="in", start_time=0, duration=music_fade_in,
        )

    # Apply fade-out
    if music_fade_out > 0:
        fade_start = max(0.0, vo_duration - music_fade_out)
        music_stream = music_stream.filter(
            "afade", type="out", start_time=fade_start, duration=music_fade_out,
        )

    # --- Voiceover stream ----------------------------------------------------
    vo_stream = ffmpeg.input(str(voiceover_path))

    # --- Merge ----------------------------------------------------------------
    try:
        (
            ffmpeg
            .filter([vo_stream, music_stream], "amix", inputs=2, duration="first", dropout_transition=0)
            .output(str(output_path), acodec="aac", audio_bitrate="192k", ar=44100)
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else "unknown error"
        raise FFmpegError(f"Audio mixing failed: {stderr}") from exc

    logger.info("Audio mix complete: %s (%.1fs)", output_path, vo_duration)
    return output_path
