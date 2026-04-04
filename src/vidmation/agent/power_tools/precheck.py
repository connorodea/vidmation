"""Pre-flight checks for CLI tool availability.

Run these checks at startup to know which CLI tools the PowerToolsAgent
can use.  Missing optional tools degrade gracefully; missing core tools
(ffmpeg, magick) raise warnings.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess

logger = logging.getLogger(__name__)

# Core tools -- the agent needs these for most operations.
CORE_TOOLS: dict[str, str] = {
    "magick": "ImageMagick",
    "ffmpeg": "FFmpeg",
    "ffprobe": "FFprobe",
}

# Optional tools -- nice to have, but the agent can work without them.
OPTIONAL_TOOLS: dict[str, str] = {
    "sox": "SoX",
    "exiftool": "ExifTool",
    "gifsicle": "Gifsicle",
    "optipng": "OptiPNG",
    "pngquant": "pngquant",
    "jpegoptim": "jpegoptim",
}


def _get_version(tool: str) -> str:
    """Try to extract a version string from a CLI tool."""
    version_flags = {
        "magick": ["magick", "--version"],
        "ffmpeg": ["ffmpeg", "-version"],
        "ffprobe": ["ffprobe", "-version"],
        "sox": ["sox", "--version"],
        "exiftool": ["exiftool", "-ver"],
        "gifsicle": ["gifsicle", "--version"],
        "optipng": ["optipng", "--version"],
        "pngquant": ["pngquant", "--version"],
        "jpegoptim": ["jpegoptim", "--version"],
    }
    args = version_flags.get(tool, [tool, "--version"])
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() or result.stderr.strip()
        # Return first non-empty line (most tools print version on line 1).
        for line in output.splitlines():
            line = line.strip()
            if line:
                return line
        return "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def check_all_tools() -> dict[str, dict]:
    """Check which CLI tools are installed and their versions.

    Returns a dict like::

        {
            "magick": {"installed": True, "version": "ImageMagick 7.1...", "path": "/usr/local/bin/magick", "core": True},
            "sox":    {"installed": False, "version": "", "path": "", "core": False},
            ...
        }
    """
    results: dict[str, dict] = {}

    for tool, label in {**CORE_TOOLS, **OPTIONAL_TOOLS}.items():
        path = shutil.which(tool)
        is_core = tool in CORE_TOOLS

        if path:
            version = _get_version(tool)
            results[tool] = {
                "installed": True,
                "version": version,
                "path": path,
                "label": label,
                "core": is_core,
            }
            logger.debug("%s found: %s (%s)", label, path, version)
        else:
            results[tool] = {
                "installed": False,
                "version": "",
                "path": "",
                "label": label,
                "core": is_core,
            }
            if is_core:
                logger.warning(
                    "%s (%s) not found -- many PowerToolsAgent operations will be unavailable",
                    label,
                    tool,
                )
            else:
                logger.info("%s (%s) not found -- optional", label, tool)

    return results


def get_missing_tools() -> dict[str, dict]:
    """Return only the tools that are missing."""
    return {k: v for k, v in check_all_tools().items() if not v["installed"]}


def get_installed_tools() -> dict[str, dict]:
    """Return only the tools that are installed."""
    return {k: v for k, v in check_all_tools().items() if v["installed"]}


def install_missing_tools() -> dict[str, str]:
    """Return platform-appropriate install commands for missing tools.

    Returns a dict of ``{tool_name: install_command}``.
    """
    missing = get_missing_tools()
    if not missing:
        return {}

    system = platform.system().lower()
    suggestions: dict[str, str] = {}

    # Mapping of tool binary name -> package name per manager.
    brew_packages = {
        "magick": "imagemagick",
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffmpeg",
        "sox": "sox",
        "exiftool": "exiftool",
        "gifsicle": "gifsicle",
        "optipng": "optipng",
        "pngquant": "pngquant",
        "jpegoptim": "jpegoptim",
    }
    apt_packages = {
        "magick": "imagemagick",
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffmpeg",
        "sox": "sox",
        "exiftool": "libimage-exiftool-perl",
        "gifsicle": "gifsicle",
        "optipng": "optipng",
        "pngquant": "pngquant",
        "jpegoptim": "jpegoptim",
    }

    for tool in missing:
        if system == "darwin":
            pkg = brew_packages.get(tool, tool)
            suggestions[tool] = f"brew install {pkg}"
        elif system == "linux":
            pkg = apt_packages.get(tool, tool)
            suggestions[tool] = f"sudo apt-get install -y {pkg}"
        else:
            suggestions[tool] = f"Install {missing[tool]['label']} manually"

    return suggestions


def get_imagemagick_delegates() -> list[str]:
    """Check ImageMagick's compiled delegates (webp, heic, png, jpeg, etc.).

    Returns a list of delegate names, e.g. ``["png", "jpeg", "webp", "heic", "freetype"]``.
    Returns an empty list if ImageMagick is not installed.
    """
    if not shutil.which("magick"):
        return []

    try:
        result = subprocess.run(
            ["magick", "-list", "delegate"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        delegates: list[str] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            # ImageMagick lists delegates in a table: "delegate   command"
            # We want the first column.
            if line and not line.startswith("-") and not line.lower().startswith("delegate"):
                parts = line.split()
                if parts:
                    delegates.append(parts[0].lower())
        return delegates
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def get_imagemagick_formats() -> list[str]:
    """List image formats ImageMagick supports.

    Returns a list like ``["PNG", "JPEG", "WEBP", "GIF", ...]``.
    """
    if not shutil.which("magick"):
        return []

    try:
        result = subprocess.run(
            ["magick", "-list", "format"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        formats: list[str] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            # Lines look like: "PNG* PNG  rw-  ..."
            if line and not line.startswith("-"):
                parts = line.split()
                if parts and len(parts) >= 2:
                    fmt = parts[0].rstrip("*").upper()
                    if fmt.isalpha():
                        formats.append(fmt)
        return sorted(set(formats))
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def preflight_report() -> str:
    """Generate a human-readable report of tool availability."""
    tools = check_all_tools()
    lines = ["VIDMATION Power Tools -- Pre-flight Check", "=" * 50, ""]

    # Core tools first.
    lines.append("CORE TOOLS (required):")
    for tool, info in tools.items():
        if info["core"]:
            status = "OK" if info["installed"] else "MISSING"
            version = f" -- {info['version']}" if info["version"] else ""
            lines.append(f"  [{status:>7}] {info['label']:20s}{version}")

    lines.append("")
    lines.append("OPTIONAL TOOLS:")
    for tool, info in tools.items():
        if not info["core"]:
            status = "OK" if info["installed"] else "MISSING"
            version = f" -- {info['version']}" if info["version"] else ""
            lines.append(f"  [{status:>7}] {info['label']:20s}{version}")

    # ImageMagick delegates.
    delegates = get_imagemagick_delegates()
    if delegates:
        lines.append("")
        lines.append(f"ImageMagick delegates: {', '.join(delegates)}")

    # Install suggestions for missing.
    suggestions = install_missing_tools()
    if suggestions:
        lines.append("")
        lines.append("Install missing tools:")
        for tool, cmd in suggestions.items():
            lines.append(f"  {cmd}")

    return "\n".join(lines)
