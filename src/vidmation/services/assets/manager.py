"""AssetManager — upload, organise, query, and resolve custom media assets.

Assets are stored under ``{assets_dir}/uploads/{type}/{uuid}{ext}`` and tracked
in the database via the :class:`~vidmation.models.asset.Asset` model.
"""

from __future__ import annotations

import logging
import mimetypes
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from vidmation.config.settings import Settings, get_settings
from vidmation.db.engine import get_session
from vidmation.models.asset import Asset, AssetSource, AssetType

logger = logging.getLogger(__name__)

# Asset types that users can upload via this manager.
UPLOADABLE_TYPES: set[str] = {
    AssetType.TRANSITION.value,
    AssetType.OVERLAY.value,
    AssetType.MUSIC.value,
    AssetType.SOUND_EFFECT.value,
    AssetType.INTRO.value,
    AssetType.OUTRO.value,
    AssetType.WATERMARK.value,
}


class AssetManager:
    """High-level facade for custom asset CRUD and file management.

    Parameters
    ----------
    session:
        An optional SQLAlchemy session.  When ``None`` a new session is
        created via :func:`get_session`.
    settings:
        Application settings.  Defaults to the cached singleton.
    """

    def __init__(
        self,
        session: Session | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._session = session
        self._owns_session = session is None

    # -- Session management ---------------------------------------------------

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_session()
            self._owns_session = True
        return self._session

    def close(self) -> None:
        """Close the session if we created it ourselves."""
        if self._owns_session and self._session is not None:
            self._session.close()
            self._session = None

    # -- Storage helpers ------------------------------------------------------

    def _uploads_dir(self, asset_type: str) -> Path:
        """Return (and ensure) the upload directory for a given asset type."""
        base = self.settings.assets_dir / "uploads" / asset_type
        base.mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def _detect_mime(path: Path) -> str:
        """Best-effort MIME type detection."""
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"

    @staticmethod
    def _probe_duration(path: Path) -> float | None:
        """Use ffprobe to get duration for audio/video files.  Returns None on failure."""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            logger.debug("ffprobe duration detection failed for %s", path)
        return None

    # -- CRUD -----------------------------------------------------------------

    def upload(
        self,
        file_path: Path,
        asset_type: str,
        name: str,
        user_id: str | None = None,
        tags: list[str] | None = None,
        is_public: bool = False,
    ) -> Asset:
        """Move *file_path* into organised storage and create a DB record.

        Parameters
        ----------
        file_path:
            Path to the source file on disk (will be **moved**, not copied).
        asset_type:
            One of the uploadable asset types (transition, overlay, ...).
        name:
            Human-readable display name.
        user_id:
            Owner.  ``None`` for built-in/public assets.
        tags:
            Optional list of categorisation tags.
        is_public:
            Whether the asset should be visible to all users.

        Returns
        -------
        Asset
            The persisted database record.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {file_path}")

        # Validate asset type
        asset_type_lower = asset_type.lower()
        if asset_type_lower not in UPLOADABLE_TYPES:
            raise ValueError(
                f"Invalid asset type '{asset_type}'. "
                f"Must be one of: {', '.join(sorted(UPLOADABLE_TYPES))}"
            )

        asset_enum = AssetType(asset_type_lower)

        # Generate a unique filename, preserving original extension
        ext = file_path.suffix.lower() or ""
        unique_name = f"{uuid.uuid4()}{ext}"
        dest_dir = self._uploads_dir(asset_type_lower)
        dest_path = dest_dir / unique_name

        # Move file into managed storage
        shutil.move(str(file_path), str(dest_path))
        logger.info("Asset file stored: %s -> %s", file_path, dest_path)

        # Gather metadata
        file_size = dest_path.stat().st_size
        mime_type = self._detect_mime(dest_path)
        duration = self._probe_duration(dest_path) if mime_type and (
            mime_type.startswith("audio/") or mime_type.startswith("video/")
        ) else None

        # Persist
        asset = Asset(
            user_id=user_id,
            name=name,
            asset_type=asset_enum,
            source=AssetSource.UPLOAD,
            file_path=str(dest_path),
            file_size=file_size,
            mime_type=mime_type,
            duration=duration,
            is_public=is_public,
            tags=tags or [],
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)

        logger.info("Asset created: %s (id=%s)", name, asset.id)
        return asset

    def list_assets(
        self,
        asset_type: str | None = None,
        user_id: str | None = None,
        include_public: bool = True,
    ) -> list[Asset]:
        """Return assets matching the given filters.

        Parameters
        ----------
        asset_type:
            Optional filter by type (e.g. ``"transition"``).
        user_id:
            Show assets belonging to this user.
        include_public:
            When ``True``, also include assets where ``is_public=True``.
        """
        stmt = select(Asset).order_by(Asset.created_at.desc())

        # Type filter
        if asset_type:
            stmt = stmt.where(Asset.asset_type == AssetType(asset_type.lower()))

        # Ownership filter: user's own assets + optionally public ones
        if user_id and include_public:
            stmt = stmt.where(
                (Asset.user_id == user_id) | (Asset.is_public == True)  # noqa: E712
            )
        elif user_id:
            stmt = stmt.where(Asset.user_id == user_id)
        elif include_public:
            stmt = stmt.where(Asset.is_public == True)  # noqa: E712

        return list(self.session.scalars(stmt).all())

    def get_asset(self, asset_id: str) -> Asset | None:
        """Fetch a single asset by ID."""
        return self.session.get(Asset, asset_id)

    def delete_asset(self, asset_id: str) -> None:
        """Delete an asset record and remove its file from disk."""
        asset = self.session.get(Asset, asset_id)
        if asset is None:
            raise ValueError(f"Asset not found: {asset_id}")

        # Remove file from disk
        fp = Path(asset.file_path)
        if fp.exists():
            fp.unlink()
            logger.info("Deleted file: %s", fp)

        # Remove thumbnail if present
        if asset.thumbnail_path:
            tp = Path(asset.thumbnail_path)
            if tp.exists():
                tp.unlink()

        self.session.delete(asset)
        self.session.commit()
        logger.info("Asset deleted: %s (id=%s)", asset.name, asset_id)

    # -- Convenience resolvers ------------------------------------------------

    def _resolve_by_type_and_name(
        self,
        asset_type: AssetType,
        name: str | None,
        user_id: str | None = None,
    ) -> Path | None:
        """Find a single asset file by type and optional name."""
        stmt = select(Asset).where(Asset.asset_type == asset_type)

        if name:
            stmt = stmt.where(Asset.name == name)
        if user_id:
            stmt = stmt.where(
                (Asset.user_id == user_id) | (Asset.is_public == True)  # noqa: E712
            )
        else:
            stmt = stmt.where(Asset.is_public == True)  # noqa: E712

        stmt = stmt.order_by(Asset.created_at.desc()).limit(1)
        asset = self.session.scalars(stmt).first()

        if asset is None:
            return None

        path = Path(asset.file_path)
        return path if path.exists() else None

    def get_transition(self, name: str | None = None, user_id: str | None = None) -> Path | None:
        """Resolve a custom transition video file by name."""
        return self._resolve_by_type_and_name(AssetType.TRANSITION, name, user_id)

    def get_overlay(self, name: str | None = None, user_id: str | None = None) -> Path | None:
        """Resolve an overlay image/video file by name."""
        return self._resolve_by_type_and_name(AssetType.OVERLAY, name, user_id)

    def get_sound_effect(self, name: str | None = None, user_id: str | None = None) -> Path | None:
        """Resolve a sound-effect audio file by name."""
        return self._resolve_by_type_and_name(AssetType.SOUND_EFFECT, name, user_id)

    def get_intro(self, channel_name: str | None = None, user_id: str | None = None) -> Path | None:
        """Resolve a channel intro video.

        If *channel_name* is given it is used as the asset name; otherwise the
        most recent intro for the user (or public) is returned.
        """
        return self._resolve_by_type_and_name(AssetType.INTRO, channel_name, user_id)

    def get_outro(self, channel_name: str | None = None, user_id: str | None = None) -> Path | None:
        """Resolve a channel outro video.

        If *channel_name* is given it is used as the asset name; otherwise the
        most recent outro for the user (or public) is returned.
        """
        return self._resolve_by_type_and_name(AssetType.OUTRO, channel_name, user_id)
