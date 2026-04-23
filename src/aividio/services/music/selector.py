"""Music selection service -- finds or downloads royalty-free background music.

Strategy:
1. Check ``assets/music/`` for local music files (mp3/wav/ogg/m4a).
2. If none found, download a royalty-free ambient track from Pixabay's
   free music library (no API key required for their CDN-hosted tracks).
3. Cache downloaded tracks in ``assets/music/`` so subsequent runs are instant.

The selector picks a track based on the channel profile's ``music.genre``
setting.  If no genre-specific track is available, it falls back to a
generic ambient track.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from aividio.config.profiles import ChannelProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bundled royalty-free music tracks (Pixabay CDN -- all CC0 / Pixabay License)
#
# These are direct-download URLs for tracks hosted on Pixabay's CDN.
# Pixabay License: free for commercial use, no attribution required.
# Tracks were hand-picked for common faceless YouTube video genres.
# ---------------------------------------------------------------------------

_MUSIC_CATALOG: dict[str, list[dict[str, str]]] = {
    "ambient": [
        {
            "name": "ambient-calm-atmosphere",
            "url": "https://cdn.pixabay.com/audio/2024/11/28/audio_3a4b7e2f77.mp3",
            "filename": "ambient_calm_atmosphere.mp3",
        },
        {
            "name": "documentary-atmosphere",
            "url": "https://cdn.pixabay.com/audio/2024/02/14/audio_8747098e0c.mp3",
            "filename": "documentary_atmosphere.mp3",
        },
    ],
    "cinematic": [
        {
            "name": "cinematic-ambient",
            "url": "https://cdn.pixabay.com/audio/2024/05/16/audio_16e08667b3.mp3",
            "filename": "cinematic_ambient.mp3",
        },
    ],
    "lofi": [
        {
            "name": "lofi-chill-medium-version",
            "url": "https://cdn.pixabay.com/audio/2024/09/10/audio_6e1cbe51b5.mp3",
            "filename": "lofi_chill_medium.mp3",
        },
    ],
    "electronic": [
        {
            "name": "electronic-future-beats",
            "url": "https://cdn.pixabay.com/audio/2023/10/24/audio_3f8a57e990.mp3",
            "filename": "electronic_future_beats.mp3",
        },
    ],
}

# Fallback genre when the requested genre has no catalog entries
_DEFAULT_GENRE = "ambient"

# Audio file extensions we recognise as music
_MUSIC_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}


class MusicSelector:
    """Selects background music for a video based on the channel profile.

    Usage::

        selector = MusicSelector(assets_dir=Path("assets"))
        music_path = selector.select_music(profile=profile, work_dir=work_dir)
    """

    def __init__(self, assets_dir: Path | None = None) -> None:
        self._assets_dir = Path(assets_dir) if assets_dir else Path("assets")
        self._music_dir = self._assets_dir / "music"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_music(
        self,
        profile: ChannelProfile,
        work_dir: Path,
    ) -> Path | None:
        """Find or download a background music track.

        Parameters:
            profile: The channel profile (uses ``profile.music.genre``).
            work_dir: Pipeline working directory (used as fallback cache).

        Returns:
            Path to a music file, or ``None`` if nothing could be obtained.
        """
        genre = profile.music.genre.lower() if profile.music.genre else _DEFAULT_GENRE

        # 1. Check for local music files in assets/music/
        local = self._find_local_music()
        if local:
            chosen = random.choice(local)
            logger.info("[music] Using local music file: %s", chosen.name)
            return chosen

        # 2. Download from bundled catalog
        downloaded = self._download_from_catalog(genre, work_dir)
        if downloaded:
            return downloaded

        logger.warning("[music] No music available for genre=%r", genre)
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_local_music(self) -> list[Path]:
        """Scan ``assets/music/`` for existing audio files."""
        if not self._music_dir.exists():
            return []

        files = [
            f for f in self._music_dir.iterdir()
            if f.is_file() and f.suffix.lower() in _MUSIC_EXTENSIONS
        ]
        if files:
            logger.debug("[music] Found %d local music files in %s", len(files), self._music_dir)
        return files

    def _download_from_catalog(
        self,
        genre: str,
        work_dir: Path,
    ) -> Path | None:
        """Download a track from the bundled catalog.

        Downloads are cached in ``assets/music/`` so they persist across runs.
        """
        # Get tracks for the requested genre, fall back to ambient
        tracks = _MUSIC_CATALOG.get(genre, _MUSIC_CATALOG.get(_DEFAULT_GENRE, []))
        if not tracks:
            logger.warning("[music] No catalog tracks for genre=%r", genre)
            return None

        track = random.choice(tracks)

        # Check if already cached
        self._music_dir.mkdir(parents=True, exist_ok=True)
        cached_path = self._music_dir / track["filename"]
        if cached_path.exists() and cached_path.stat().st_size > 0:
            logger.info("[music] Using cached track: %s", cached_path.name)
            return cached_path

        # Also check work_dir as secondary cache
        work_music = work_dir / "music" / track["filename"]
        if work_music.exists() and work_music.stat().st_size > 0:
            logger.info("[music] Using work-dir cached track: %s", work_music.name)
            return work_music

        # Download
        logger.info(
            "[music] Downloading %r (%s) -> %s",
            track["name"],
            genre,
            cached_path,
        )

        try:
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                response = client.get(track["url"])
                response.raise_for_status()

                cached_path.write_bytes(response.content)
                logger.info(
                    "[music] Downloaded %s (%.1f MB)",
                    cached_path.name,
                    len(response.content) / (1024 * 1024),
                )
                return cached_path

        except httpx.HTTPError as exc:
            logger.warning("[music] Download failed for %r: %s", track["name"], exc)

            # Try a different track from the same genre as fallback
            remaining = [t for t in tracks if t["name"] != track["name"]]
            if remaining:
                fallback = random.choice(remaining)
                return self._try_single_download(fallback, cached_path.parent)

        except Exception as exc:
            logger.error("[music] Unexpected error downloading music: %s", exc)

        return None

    def _try_single_download(self, track: dict[str, str], dest_dir: Path) -> Path | None:
        """Attempt to download a single track. Returns path on success, None on failure."""
        dest = dest_dir / track["filename"]
        if dest.exists() and dest.stat().st_size > 0:
            return dest

        try:
            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                response = client.get(track["url"])
                response.raise_for_status()
                dest.write_bytes(response.content)
                logger.info("[music] Fallback download succeeded: %s", dest.name)
                return dest
        except Exception as exc:
            logger.warning("[music] Fallback download also failed: %s", exc)
            return None
