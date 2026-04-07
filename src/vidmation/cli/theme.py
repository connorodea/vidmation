"""VIDMATION CLI design system — shared branding, colors, and styled components.

Provides a consistent, premium visual language across all CLI commands.
Inspired by modern CLIs (Vercel, Stripe, Railway).

Usage::

    from vidmation.cli.theme import (
        console, err, brand, success, error, warning, info,
        header, divider, kv, styled_table, LOGO,
    )
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------

# Matches the AIVidio logo gradient (#10a37f -> #0d8c6d)
ACCENT = "#10a37f"
ACCENT_DIM = "#0d8c6d"
HIGHLIGHT = "bright_cyan"
SUCCESS = "bright_green"
ERROR = "#ff5555"
WARN = "#f1c40f"
MUTED = "dim"
LABEL = "bold white"

# ---------------------------------------------------------------------------
# Custom Rich theme
# ---------------------------------------------------------------------------

_THEME = Theme({
    "accent": f"bold {ACCENT}",
    "accent.dim": ACCENT_DIM,
    "highlight": HIGHLIGHT,
    "success": f"bold {SUCCESS}",
    "error": f"bold {ERROR}",
    "warn": f"bold {WARN}",
    "muted": "dim",
    "label": "bold white",
    "value": "bright_white",
    "url": f"underline {ACCENT}",
    "path": "dim italic",
    "id": "dim cyan",
    "status.running": "bold bright_blue",
    "status.done": f"bold {SUCCESS}",
    "status.fail": f"bold {ERROR}",
    "status.pending": "bold yellow",
    "status.private": "bold red",
    "status.public": f"bold {SUCCESS}",
    "status.unlisted": "bold yellow",
})

# ---------------------------------------------------------------------------
# Console instances
# ---------------------------------------------------------------------------

console = Console(theme=_THEME)
err = Console(stderr=True, theme=_THEME)

# ---------------------------------------------------------------------------
# ASCII logo
# ---------------------------------------------------------------------------

LOGO = r"""[bold bright_green]
     _    ___  __     ___     _ _
    / \  |_ _| \ \   / (_) __| (_) ___
   / _ \  | |   \ \ / /| |/ _` | |/ _ \
  / ___ \ | |    \ V / | | (_| | | (_) |
 /_/   \_\___|    \_/  |_|\__,_|_|\___/[/bold bright_green]
"""

LOGO_COMPACT = "[bold bright_green]AIVidio[/bold bright_green]"

TAGLINE = "[dim]AI-powered faceless video automation[/dim]"

VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Branded output helpers
# ---------------------------------------------------------------------------


def brand(text: str = "") -> str:
    """Return the brand name with accent styling."""
    return f"[accent]{text or 'AIVidio'}[/accent]"


def header(
    title: str,
    subtitle: str = "",
    *,
    border_style: str = ACCENT,
    width: int | None = None,
) -> Panel:
    """Create a branded header panel.

    Args:
        title: Main title text.
        subtitle: Optional secondary text below the title.
        border_style: Rich color for the panel border.
        width: Fixed width (None = auto-fit).
    """
    content = f"[bold bright_white]{title}[/bold bright_white]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"

    if width:
        return Panel(
            content,
            border_style=border_style,
            padding=(0, 2),
            width=width,
        )
    return Panel.fit(
        content,
        border_style=border_style,
        padding=(0, 2),
    )


def result_panel(
    title: str,
    rows: list[tuple[str, str]],
    *,
    border_style: str = ACCENT,
    status: str = "success",
) -> Panel:
    """Create a results panel with key-value rows.

    Args:
        title: Panel title.
        rows: List of (label, value) tuples.
        border_style: Panel border color.
        status: 'success' | 'error' | 'warning' — sets header icon.
    """
    icons = {"success": "[success]\u2713[/success]", "error": "[error]\u2717[/error]", "warning": "[warn]\u26a0[/warn]"}
    icon = icons.get(status, "")

    lines: list[str] = [f"{icon} [bold bright_white]{title}[/bold bright_white]\n"]
    max_label = max((len(l) for l, _ in rows), default=0) + 1
    for label, value in rows:
        lines.append(f"  [label]{label:<{max_label}}[/label] {value}")

    return Panel.fit(
        "\n".join(lines),
        border_style=border_style,
        padding=(0, 2),
    )


def success(msg: str) -> None:
    """Print a success message with checkmark."""
    console.print(f"  [success]\u2713[/success] {msg}")


def error(msg: str) -> None:
    """Print an error message with X mark."""
    err.print(f"  [error]\u2717[/error] {msg}")


def warning(msg: str) -> None:
    """Print a warning message."""
    console.print(f"  [warn]\u26a0[/warn] {msg}")


def info(msg: str) -> None:
    """Print an info message with bullet."""
    console.print(f"  [accent]\u2022[/accent] {msg}")


def step(number: int, text: str) -> None:
    """Print a numbered step indicator."""
    console.print(f"\n  [accent]Step {number}[/accent]  {text}")


def divider(char: str = "\u2500", style: str = "dim") -> None:
    """Print a horizontal divider."""
    console.print(f"[{style}]{char * 60}[/{style}]")


def kv(label: str, value: str, indent: int = 2) -> None:
    """Print a key-value pair."""
    pad = " " * indent
    console.print(f"{pad}[label]{label}[/label]  {value}")


def status_badge(status_str: str) -> str:
    """Return a styled status badge string."""
    mapping = {
        "public": "[status.public]\u25cf public[/status.public]",
        "unlisted": "[status.unlisted]\u25cf unlisted[/status.unlisted]",
        "private": "[status.private]\u25cf private[/status.private]",
        "completed": "[status.done]\u25cf completed[/status.done]",
        "running": "[status.running]\u25cf running[/status.running]",
        "queued": "[status.pending]\u25cf queued[/status.pending]",
        "pending": "[status.pending]\u25cf pending[/status.pending]",
        "failed": "[status.fail]\u25cf failed[/status.fail]",
        "active": "[status.done]\u25cf active[/status.done]",
        "inactive": "[muted]\u25cf inactive[/muted]",
    }
    key = status_str.lower().strip()
    return mapping.get(key, f"[muted]\u25cf {status_str}[/muted]")


# ---------------------------------------------------------------------------
# Styled table builder
# ---------------------------------------------------------------------------


def styled_table(
    title: str = "",
    *,
    show_lines: bool = False,
    border_style: str = ACCENT_DIM,
    pad_edge: bool = True,
) -> Table:
    """Create a consistently-styled table.

    Args:
        title: Table title (displayed above).
        show_lines: Show row separators.
        border_style: Border color.
        pad_edge: Padding on left/right edges.
    """
    return Table(
        title=f"[bold bright_white]{title}[/bold bright_white]" if title else None,
        show_lines=show_lines,
        border_style=border_style,
        title_style="",
        header_style=f"bold {ACCENT}",
        pad_edge=pad_edge,
        row_styles=["", "dim"],  # alternating row shading
    )


# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------

def pipeline_progress():
    """Create a standardised pipeline progress bar."""
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    return Progress(
        SpinnerColumn("dots", style=f"bold {ACCENT}"),
        TextColumn("[bold bright_white]{task.description}[/bold bright_white]"),
        BarColumn(
            bar_width=30,
            complete_style=ACCENT,
            finished_style=SUCCESS,
        ),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def spinner(text: str = "Processing..."):
    """Create a branded spinner context manager."""
    return console.status(f"[accent]{text}[/accent]", spinner="dots")
