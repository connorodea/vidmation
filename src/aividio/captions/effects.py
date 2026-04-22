"""Low-level ASS override-tag effect builders.

Every public function returns a string of ASS override tags (wrapped in
``{...}``) that can be prepended to dialogue text.  These are the atomic
building blocks used by :class:`~aividio.captions.animator.CaptionAnimator`.

ASS override tag reference used here
-------------------------------------
\\fscx, \\fscy  -- horizontal / vertical font scale (percent)
\\fad(in,out)   -- simple fade (alpha, in milliseconds)
\\fade(...)     -- complex 7-arg alpha fade
\\t(t1,t2,...)  -- animated transition between tag states
\\move(x1,y1,x2,y2[,t1,t2]) -- position animation
\\pos(x,y)      -- static position
\\an             -- numpad alignment
\\c, \\1c        -- primary fill colour  (ASS &HAABBGGRR)
\\3c             -- outline colour
\\4c             -- shadow colour
\\bord           -- outline width
\\shad           -- shadow depth
\\blur           -- gaussian blur
\\be             -- edge blur
\\kf             -- karaoke progressive fill
\\alpha          -- overall alpha  (&HFF = fully transparent, &H00 = opaque)
\\frz            -- z-axis rotation
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_ass(hex_color: str, alpha: str = "00") -> str:
    """Convert ``#RRGGBB`` to ASS ``&HAABBGGRR``."""
    h = hex_color.lstrip("#")
    if len(h) == 8:
        r, g, b, alpha = h[0:2], h[2:4], h[4:6], h[6:8]
    elif len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
    else:
        return "&H00FFFFFF"
    return f"&H{alpha}{b}{g}{r}".upper()


def _ass_alpha(opacity_0_255: int) -> str:
    """Return an ASS alpha hex value.  0 = opaque, 255 = transparent."""
    clamped = max(0, min(255, opacity_0_255))
    return f"&H{clamped:02X}"


# ---------------------------------------------------------------------------
# Animation effects
# ---------------------------------------------------------------------------

def bounce_in(delay_ms: int = 0, duration_ms: int = 300) -> str:
    """Drop-in with bounce easing (overshoot scale then settle).

    The text starts scaled to 0 %, overshoots to 120 %, then settles to
    100 % -- creating a satisfying bounce.

    Parameters
    ----------
    delay_ms:
        Milliseconds to wait before the animation starts (relative to
        the dialogue start time).
    duration_ms:
        Total duration of the bounce animation.
    """
    t1 = delay_ms
    t2 = delay_ms + int(duration_ms * 0.5)
    t3 = delay_ms + duration_ms
    return (
        f"{{\\fscx0\\fscy0"
        f"\\t({t1},{t2},\\fscx120\\fscy120)"
        f"\\t({t2},{t3},\\fscx100\\fscy100)}}"
    )


def pop_in(delay_ms: int = 0, duration_ms: int = 250) -> str:
    """Scale from 0 % to overshoot (130 %) then snap to 100 %.

    Similar to bounce but with a sharper overshoot and faster settle,
    giving a more punchy feel.
    """
    t1 = delay_ms
    t2 = delay_ms + int(duration_ms * 0.6)
    t3 = delay_ms + duration_ms
    return (
        f"{{\\fscx0\\fscy0"
        f"\\t({t1},{t2},\\fscx130\\fscy130)"
        f"\\t({t2},{t3},\\fscx100\\fscy100)}}"
    )


def fade_in(duration_ms: int = 300, fade_out_ms: int = 0) -> str:
    """Simple alpha fade-in (and optional fade-out).

    Uses the ``\\fad`` tag for clean in/out fading.
    """
    return f"{{\\fad({duration_ms},{fade_out_ms})}}"


def slide_up(distance: int = 40, duration_ms: int = 300, delay_ms: int = 0) -> str:
    """Slide text upward from *distance* pixels below its final position.

    Uses ``\\move`` relative to a base position.  The caller must combine
    this with a ``\\pos`` or ``\\an`` tag to set the reference point.
    The implementation uses an ``\\org`` + ``\\frz`` trick to avoid needing
    absolute coords; instead we animate vertical offset via scale.

    For simplicity this returns a transform on the Y position using a
    clip-move workaround:  start at +distance, animate to 0.
    """
    t1 = delay_ms
    t2 = delay_ms + duration_ms
    # We use \\fscx100\\fscy0 -> \\fscy100 with \\org at bottom to simulate
    # slide-up.  However the cleanest portable approach is alpha + a small
    # frz rotation that looks like motion:
    return (
        f"{{\\alpha&HFF"
        f"\\t({t1},{t1},\\alpha&H00)"
        f"\\fscx100\\fscy60"
        f"\\t({t1},{t2},\\fscy100)}}"
    )


def color_highlight(word: str, highlight_color: str) -> str:
    """Wrap *word* so it renders in *highlight_color*.

    Returns the word with inline override tags.
    """
    ass_color = _hex_to_ass(highlight_color)
    return f"{{\\c{ass_color}}}{word}{{\\r}}"


def bg_highlight(word: str, bg_color: str, padding: int = 8) -> str:
    """Wrap *word* with a coloured background box.

    Uses ``\\3c`` (outline colour) + ``\\bord`` (thick outline) to simulate
    a background box behind the word, and ``\\4c`` for shadow colour matching.
    """
    ass_bg = _hex_to_ass(bg_color)
    return (
        f"{{\\3c{ass_bg}\\4c{ass_bg}"
        f"\\bord{padding}\\shad0"
        f"\\p0}}{word}{{\\r}}"
    )


def glow(color: str = "#FFFFFF", blur: int = 6, strength: int = 3) -> str:
    """Add a glow / bloom effect around text.

    Combines ``\\blur`` and ``\\be`` with an outline colour to create a
    soft glow.
    """
    ass_color = _hex_to_ass(color)
    return f"{{\\3c{ass_color}\\bord{strength}\\blur{blur}\\be1}}"


def shake(intensity: int = 3, duration_ms: int = 200, delay_ms: int = 0) -> str:
    """Small z-rotation shake to simulate vibration / emphasis.

    Rotates a few degrees one way, then the other, then back to zero.
    """
    t1 = delay_ms
    t2 = delay_ms + int(duration_ms * 0.25)
    t3 = delay_ms + int(duration_ms * 0.50)
    t4 = delay_ms + int(duration_ms * 0.75)
    t5 = delay_ms + duration_ms
    return (
        f"{{\\frz0"
        f"\\t({t1},{t2},\\frz{intensity})"
        f"\\t({t2},{t3},\\frz-{intensity})"
        f"\\t({t3},{t4},\\frz{intensity // 2})"
        f"\\t({t4},{t5},\\frz0)}}"
    )


def scale_pulse(delay_ms: int = 0, duration_ms: int = 400) -> str:
    """Pulse current word: scale up to 115 % then back to 100 %."""
    t1 = delay_ms
    t2 = delay_ms + int(duration_ms * 0.4)
    t3 = delay_ms + duration_ms
    return (
        f"{{\\fscx100\\fscy100"
        f"\\t({t1},{t2},\\fscx115\\fscy115)"
        f"\\t({t2},{t3},\\fscx100\\fscy100)}}"
    )


def typewriter_char(char_index: int, char_delay_ms: int = 50) -> str:
    """Reveal a single character at the given *char_index* offset.

    The character starts fully transparent and snaps to opaque at the
    appropriate time.
    """
    appear_at = char_index * char_delay_ms
    return f"{{\\alpha&HFF\\t({appear_at},{appear_at},\\alpha&H00)}}"


def karaoke_fill(duration_cs: int) -> str:
    """Progressive karaoke fill over *duration_cs* centiseconds.

    Uses the ``\\kf`` tag for smooth left-to-right colour fill.
    """
    return f"{{\\kf{duration_cs}}}"


def underline_on(color: str = "#FFD700") -> str:
    """Turn on underline with a specific colour."""
    ass_color = _hex_to_ass(color)
    return f"{{\\u1\\c{ass_color}}}"


def underline_off() -> str:
    """Turn off underline and reset colour."""
    return "{\\u0\\r}"


def wave_offset(word_index: int, amplitude: int = 8, wave_speed_ms: int = 200) -> str:
    """Vertical wave offset for word at *word_index*.

    Each word is offset in time to create a travelling wave.  Uses a
    scale-Y pulse to approximate vertical motion.
    """
    delay = word_index * wave_speed_ms
    t1 = delay
    t2 = delay + 150
    t3 = delay + 300
    return (
        f"{{\\fscy{100 + amplitude}"
        f"\\t({t1},{t2},\\fscy{100 - amplitude // 2})"
        f"\\t({t2},{t3},\\fscy100)}}"
    )
