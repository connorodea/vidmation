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

    # --- Paths ---
    data_dir: Path = Path("data")
    assets_dir: Path = Path("assets")
    output_dir: Path = Path("output")
    profiles_dir: Path = Path("channel_profiles")


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
