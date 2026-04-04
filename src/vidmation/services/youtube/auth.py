"""YouTube OAuth 2.0 authentication and token management."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger("vidmation.services.youtube.auth")

# Scopes required for video upload + thumbnail management.
_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_credentials(
    token_path: Path,
    client_secret_path: Path,
    scopes: list[str] | None = None,
) -> Credentials:
    """Obtain valid YouTube API credentials.

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
