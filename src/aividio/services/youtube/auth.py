"""YouTube OAuth 2.0 authentication and token management.

Supports two modes:

1. **Global (legacy)** — a single token file on disk, used by
   ``get_credentials(token_path, client_secret_path)``.
2. **Per-channel (multi-channel SaaS)** — each channel stores its OAuth
   token JSON in the database.  Used by ``get_credentials_for_channel()``
   and ``store_credentials_for_channel()``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger("aividio.services.youtube.auth")

# Scopes required for video upload + thumbnail management.
_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


# ---------------------------------------------------------------------------
# Legacy single-channel helpers
# ---------------------------------------------------------------------------

def get_credentials(
    token_path: Path,
    client_secret_path: Path,
    scopes: list[str] | None = None,
) -> Credentials:
    """Obtain valid YouTube API credentials (global / single-channel).

    Workflow:
    1. If a saved token exists at *token_path*, load and refresh it.
    2. If refresh fails or no token exists, run the interactive OAuth
       browser flow using the *client_secret_path* JSON file.
    3. Save the refreshed / new token back to *token_path*.

    Args:
        token_path: Path to the cached OAuth token JSON file.
        client_secret_path: Path to the ``client_secret_*.json`` from
            Google Cloud Console.
        scopes: OAuth scopes to request (defaults to upload + manage).

    Returns:
        A valid ``google.oauth2.credentials.Credentials`` object.
    """
    scopes = scopes or _SCOPES
    creds: Credentials | None = None

    # -- 1. Load existing token ---
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            logger.info("Loaded cached token from %s", token_path)
        except Exception:
            logger.warning("Failed to load cached token; will re-authenticate")
            creds = None

    # -- 2. Refresh or re-authenticate ---
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            logger.info("Token refreshed successfully")
        except Exception as exc:
            logger.warning("Token refresh failed (%s); will re-authenticate", exc)
            creds = None

    if not creds or not creds.valid:
        if not client_secret_path.exists():
            raise FileNotFoundError(
                f"YouTube client secret file not found: {client_secret_path}. "
                "Download it from the Google Cloud Console."
            )

        logger.info("Starting interactive OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret_path),
            scopes=scopes,
        )
        creds = flow.run_local_server(
            port=8090,
            prompt="consent",
            access_type="offline",
        )
        logger.info("OAuth flow completed successfully")

    # -- 3. Save token ---
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    logger.info("Token saved to %s", token_path)

    return creds


# ---------------------------------------------------------------------------
# Multi-channel (SaaS) helpers — credentials stored in the DB
# ---------------------------------------------------------------------------

def _credentials_from_json(token_json: str, scopes: list[str] | None = None) -> Credentials:
    """Deserialise a ``Credentials`` object from a JSON string."""
    scopes = scopes or _SCOPES
    info = json.loads(token_json)
    return Credentials.from_authorized_user_info(info, scopes)


def get_credentials_for_channel(
    channel_id: str,
    client_secret_path: Path,
    scopes: list[str] | None = None,
) -> Credentials:
    """Obtain valid YouTube API credentials for a specific channel.

    The OAuth token is loaded from the channel's database record.  If the
    token is expired it is refreshed and saved back.  If no token exists,
    the interactive OAuth flow is run and the resulting token is persisted
    to the channel record.

    Args:
        channel_id: The internal UUID of the :class:`Channel` record.
        client_secret_path: Path to the ``client_secret_*.json`` from
            Google Cloud Console.
        scopes: OAuth scopes to request (defaults to upload + manage).

    Returns:
        A valid ``google.oauth2.credentials.Credentials`` object.

    Raises:
        ValueError: If the channel does not exist in the database.
        FileNotFoundError: If *client_secret_path* does not exist and a
            new OAuth flow is required.
    """
    from aividio.db.engine import get_session
    from aividio.db.repos import ChannelRepo

    scopes = scopes or _SCOPES
    creds: Credentials | None = None

    session = get_session()
    try:
        repo = ChannelRepo(session)
        channel = repo.get(channel_id)

        if channel is None:
            raise ValueError(f"Channel not found: {channel_id}")

        # -- 1. Load existing token from DB ---
        if channel.oauth_token_json:
            try:
                creds = _credentials_from_json(channel.oauth_token_json, scopes)
                logger.info(
                    "Loaded OAuth token from DB for channel %s (%s)",
                    channel.name,
                    channel_id[:8],
                )
            except Exception:
                logger.warning(
                    "Failed to load OAuth token from DB for channel %s; will re-authenticate",
                    channel.name,
                )
                creds = None

        # -- 2. Refresh or re-authenticate ---
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Token refreshed for channel %s", channel.name)
                # Save the refreshed token back to DB
                store_credentials_for_channel(channel_id, creds, session=session)
            except Exception as exc:
                logger.warning(
                    "Token refresh failed for channel %s (%s); will re-authenticate",
                    channel.name,
                    exc,
                )
                creds = None

        if not creds or not creds.valid:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"YouTube client secret file not found: {client_secret_path}. "
                    "Download it from the Google Cloud Console."
                )

            logger.info(
                "Starting interactive OAuth flow for channel %s...",
                channel.name,
            )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path),
                scopes=scopes,
            )
            creds = flow.run_local_server(
                port=8090,
                prompt="consent",
                access_type="offline",
            )
            logger.info("OAuth flow completed for channel %s", channel.name)

            # Save to DB
            store_credentials_for_channel(channel_id, creds, session=session)

        return creds
    finally:
        session.close()


def store_credentials_for_channel(
    channel_id: str,
    credentials: Credentials,
    *,
    session: "Session | None" = None,  # noqa: F821 — optional caller-provided session
) -> None:
    """Persist OAuth credentials to a channel's database record.

    Args:
        channel_id: The internal UUID of the :class:`Channel` record.
        credentials: The Google OAuth ``Credentials`` to store.
        session: An existing SQLAlchemy session.  If ``None`` a new one
            is created (and committed/closed internally).
    """
    from aividio.db.engine import get_session as _get_session
    from aividio.db.repos import ChannelRepo

    own_session = session is None
    if own_session:
        session = _get_session()

    try:
        repo = ChannelRepo(session)
        channel = repo.get(channel_id)
        if channel is None:
            raise ValueError(f"Channel not found: {channel_id}")

        channel.oauth_token_json = credentials.to_json()
        channel.oauth_connected_at = datetime.now(timezone.utc)

        if own_session:
            session.commit()
        else:
            # Let the caller's session handle the commit.
            session.flush()

        logger.info(
            "OAuth token saved to DB for channel %s (%s)",
            channel.name,
            channel_id[:8],
        )
    finally:
        if own_session:
            session.close()


def fetch_youtube_channel_info(credentials: Credentials) -> dict:
    """Fetch the authenticated user's YouTube channel info.

    Returns a dict with keys: ``id``, ``title``, ``subscriber_count``,
    ``video_count``, ``thumbnail_url``.
    """
    from googleapiclient.discovery import build

    service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = (
        service.channels()
        .list(part="snippet,statistics", mine=True)
        .execute()
    )

    items = response.get("items", [])
    if not items:
        return {}

    ch = items[0]
    snippet = ch.get("snippet", {})
    stats = ch.get("statistics", {})

    return {
        "id": ch["id"],
        "title": snippet.get("title", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
    }
