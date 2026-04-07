"""Application settings loaded from environment variables and .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VIDMATION_",
        env_file_encoding="utf-8",
    )

    # --- LLM Providers ---
    anthropic_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")

    # --- TTS ---
    elevenlabs_api_key: SecretStr = SecretStr("")

    # --- AI Model Platforms ---
    replicate_api_token: SecretStr = SecretStr("")
    fal_key: SecretStr = SecretStr("")

    # --- Stock Media ---
    pexels_api_key: SecretStr = SecretStr("")
    pixabay_api_key: SecretStr = SecretStr("")

    # --- Database ---
    database_url: str = "sqlite:///data/vidmation.db"

    # --- Web ---
    secret_key: SecretStr = SecretStr("change-me-in-production")
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # --- Queue ---
    use_redis: bool = False
    redis_url: str = "redis://localhost:6379/0"

    # --- Defaults ---
    default_llm_provider: Literal["claude", "openai"] = "claude"
    default_tts_provider: Literal["elevenlabs", "openai"] = "elevenlabs"
    default_image_provider: Literal["dalle", "replicate", "fal"] = "dalle"
    default_video_format: Literal["landscape", "portrait"] = "landscape"

    # --- Notifications ---
    email_provider: Literal["resend", "smtp"] = "resend"
    email_from: str = "noreply@vidmation.io"
    email_to: str = ""  # comma-separated
    resend_api_key: SecretStr = SecretStr("")
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    discord_webhook_url: str = ""
    slack_webhook_url: str = ""

    # --- Social Publishing ---
    tiktok_access_token: SecretStr = SecretStr("")
    instagram_access_token: SecretStr = SecretStr("")
    instagram_account_id: str = ""
    public_base_url: str = ""  # for Instagram video hosting

    # --- JWT / Auth ---
    jwt_secret: SecretStr = SecretStr("change-me-in-production-use-openssl-rand")
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # --- Cost Budget ---
    monthly_budget: float = 100.0  # USD, for cost alerts

    # --- Paths ---
    data_dir: Path = Path("data")
    assets_dir: Path = Path("assets")
    output_dir: Path = Path("output")
    profiles_dir: Path = Path("channel_profiles")


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
