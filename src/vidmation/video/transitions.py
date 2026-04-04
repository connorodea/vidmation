"""Transition effects between clips using ffmpeg-python filter graphs.

Every public function in this module accepts ffmpeg stream nodes and returns
new stream nodes with the transition applied.  Nothing is rendered here --
the caller is responsible for piping the final graph into ``ffmpeg.output()``.
"""

from __future__ import annotations

import logging
from typing import Any

import ffmpeg

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_streams(
    clip_a: Any,
    clip_b: Any,
) -> tuple[Any, Any]:
    """Validate that both arguments look like ffmpeg stream objects."""
    if clip_a is None or clip_b is None:
        raise ValueError("Both clip_a and clip_b must be valid ffmpeg streams")
    return clip_a, clip_b


# ---------------------------------------------------------------------------
# Transition implementations
# ---------------------------------------------------------------------------

def crossfade(
    clip_a: Any,
    clip_b: Any,
    duration: float = 0.5,
) -> Any:
    """Apply a cross-dissolve between the tail of *clip_a* and the head of *clip_b*.

    Uses the ``xfade`` video filter (requires ffmpeg >= 4.3).

    Returns:
        A new ffmpeg stream node representing the joined output.
    """
    clip_a, clip_b = _ensure_streams(clip_a, clip_b)
    if duration <= 0:
        raise ValueError(f"Crossfade duration must be positive, got {duration}")

    logger.debug("Applying crossfade transition (%.2fs)", duration)
    return ffmpeg.filter(
        [clip_a, clip_b],
        "xfade",
        transition="fade",
        duration=duration,
        offset="placeholder",  # Caller must replace with actual offset
    )


def crossfade_with_offset(
    clip_a: Any,
    clip_b: Any,
    offset: float,
    duration: float = 0.5,
) -> Any:
    """Apply a cross-dissolve at the given *offset* (seconds from clip_a start).

    Parameters:
        clip_a: First clip stream.
        clip_b: Second clip stream.
        offset: Point in *clip_a* where the transition begins.
        duration: Length of the transition in seconds.
    """
    clip_a, clip_b = _ensure_streams(clip_a, clip_b)
    if duration <= 0:
        raise ValueError(f"Crossfade duration must be positive, got {duration}")

    logger.debug("Applying crossfade at offset=%.2f, duration=%.2f", offset, duration)
    return ffmpeg.filter(
        [clip_a, clip_b],
        "xfade",
        transition="fade",
        duration=duration,
        offset=offset,
    )


def fade_black(
    clip: Any,
    fade_in: float = 0.5,
    fade_out: float = 0.5,
    duration: float | None = None,
) -> Any:
    """Apply fade-from-black at the start and fade-to-black at the end of *clip*.

    Parameters:
        clip: The video stream to apply fades to.
        fade_in: Duration of the opening fade-in (0 to skip).
        fade_out: Duration of the closing fade-out (0 to skip).
        duration: Total clip duration (required for fade-out calculation).
                  If ``None``, fade-out is not applied.
    """
    if clip is None:
        raise ValueError("clip must be a valid ffmpeg stream")

    result = clip

    if fade_in > 0:
        logger.debug("Applying fade-in from black (%.2fs)", fade_in)
        result = result.filter("fade", type="in", start_time=0, duration=fade_in)

    if fade_out > 0 and duration is not None:
        start = max(0.0, duration - fade_out)
        logger.debug("Applying fade-out to black at %.2fs (%.2fs)", start, fade_out)
        result = result.filter("fade", type="out", start_time=start, duration=fade_out)

    return result


def cut(clip_a: Any, clip_b: Any) -> Any:
    """Hard cut -- simply concatenate *clip_a* and *clip_b* with no transition.

    Uses the ``concat`` filter.
    """
    clip_a, clip_b = _ensure_streams(clip_a, clip_b)
    logger.debug("Applying hard cut (concat)")
    return ffmpeg.concat(clip_a, clip_b, v=1, a=0)


def slide_left(
    clip_a: Any,
    clip_b: Any,
    offset: float,
    duration: float = 0.5,
) -> Any:
    """Slide *clip_b* in from the right, pushing *clip_a* to the left.

    Uses the ``xfade`` filter with the ``slideleft`` transition.
    """
    clip_a, clip_b = _ensure_streams(clip_a, clip_b)
    logger.debug("Applying slide-left transition at offset=%.2f (%.2fs)", offset, duration)
    return ffmpeg.filter(
        [clip_a, clip_b],
        "xfade",
        transition="slideleft",
        duration=duration,
        offset=offset,
    )


def slide_right(
    clip_a: Any,
    clip_b: Any,
    offset: float,
    duration: float = 0.5,
) -> Any:
    """Slide *clip_b* in from the left, pushing *clip_a* to the right.

    Uses the ``xfade`` filter with the ``slideright`` transition.
    """
    clip_a, clip_b = _ensure_streams(clip_a, clip_b)
    logger.debug("Applying slide-right transition at offset=%.2f (%.2fs)", offset, duration)
    return ffmpeg.filter(
        [clip_a, clip_b],
        "xfade",
        transition="slideright",
        duration=duration,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TRANSITION_REGISTRY: dict[str, Any] = {
    "crossfade": crossfade_with_offset,
    "fade_black": fade_black,
    "cut": cut,
    "slide_left": slide_left,
    "slide_right": slide_right,
    "none": cut,
}


def get_transition(name: str) -> Any:
    """Look up a transition function by name.

    Raises:
        ValueError: If *name* is not a recognised transition.
    """
    key = name.lower().strip()
    if key not in TRANSITION_REGISTRY:
        valid = ", ".join(sorted(TRANSITION_REGISTRY))
        raise ValueError(f"Unknown transition '{name}'. Valid: {valid}")
    return TRANSITION_REGISTRY[key]
