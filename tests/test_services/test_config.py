"""Tests for configuration system — Settings and ChannelProfile."""

from pathlib import Path

import pytest
import yaml

from vidmation.config.profiles import (
    ChannelProfile,
    ContentConfig,
    MusicConfig,
    ThumbnailConfig,
    VideoConfig,
    VoiceConfig,
    YouTubeConfig,
    get_default_profile,
    load_profile,
)
from vidmation.config.settings import Settings


class TestSettings:
    def test_settings_loads_defaults(self):
        settings = Settings()
        assert settings.database_url == "sqlite:///data/vidmation.db"
        assert settings.web_port == 8000
        assert settings.default_llm_provider == "claude"
        assert settings.default_tts_provider == "elevenlabs"
        assert settings.default_video_format == "landscape"
        assert settings.use_redis is False

    def test_settings_default_paths(self):
        settings = Settings()
        assert settings.data_dir == Path("data")
        assert settings.output_dir == Path("output")
        assert settings.profiles_dir == Path("channel_profiles")

    def test_settings_default_budget(self):
        settings = Settings()
        assert settings.monthly_budget == 100.0


class TestChannelProfileDefaults:
    def test_default_name(self):
        profile = ChannelProfile()
        assert profile.name == "Default Channel"

    def test_default_niche(self):
        profile = ChannelProfile()
        assert profile.niche == "general"

    def test_default_voice_config(self):
        profile = ChannelProfile()
        assert isinstance(profile.voice, VoiceConfig)
        assert profile.voice.provider == "elevenlabs"
        assert profile.voice.stability == 0.5

    def test_default_video_config(self):
        profile = ChannelProfile()
        assert isinstance(profile.video, VideoConfig)
        assert profile.video.format == "landscape"
        assert profile.video.resolution == "1920x1080"

    def test_default_content_config(self):
        profile = ChannelProfile()
        assert isinstance(profile.content, ContentConfig)
        assert profile.content.script_style == "listicle"

    def test_default_music_config(self):
        profile = ChannelProfile()
        assert isinstance(profile.music, MusicConfig)
        assert profile.music.genre == "ambient"
        assert profile.music.volume == 0.15

    def test_default_thumbnail_config(self):
        profile = ChannelProfile()
        assert isinstance(profile.thumbnail, ThumbnailConfig)
        assert profile.thumbnail.provider == "dalle"

    def test_default_youtube_config(self):
        profile = ChannelProfile()
        assert isinstance(profile.youtube, YouTubeConfig)
        assert profile.youtube.visibility == "public"
        assert profile.youtube.category_id == "22"


class TestLoadProfile:
    def test_load_default_profile_from_yaml(self):
        yaml_path = Path(__file__).resolve().parents[2] / "channel_profiles" / "default.yml"
        if not yaml_path.exists():
            pytest.skip("default.yml not found at expected path")
        profile = load_profile(yaml_path)
        assert profile.name == "Default Channel"
        assert profile.niche == "educational"
        assert profile.video.format == "landscape"
        assert profile.voice.provider == "elevenlabs"

    def test_load_profile_from_custom_yaml(self, tmp_dir):
        custom = {
            "name": "Science Channel",
            "niche": "science",
            "target_audience": "Curious minds",
            "voice": {"provider": "openai", "speed": 1.2},
            "video": {"format": "portrait"},
        }
        yaml_path = tmp_dir / "custom.yml"
        yaml_path.write_text(yaml.dump(custom), encoding="utf-8")

        profile = load_profile(yaml_path)
        assert profile.name == "Science Channel"
        assert profile.niche == "science"
        assert profile.voice.provider == "openai"
        assert profile.voice.speed == 1.2
        assert profile.video.format == "portrait"

    def test_load_profile_skips_unknown_keys(self, tmp_dir):
        data = {
            "name": "Unknown Keys Channel",
            "niche": "test",
            "brand_kit": {"logo_path": "/tmp/logo.png"},
            "export_platforms": ["youtube", "tiktok"],
            "some_future_setting": True,
        }
        yaml_path = tmp_dir / "unknown_keys.yml"
        yaml_path.write_text(yaml.dump(data), encoding="utf-8")

        profile = load_profile(yaml_path)
        assert profile.name == "Unknown Keys Channel"
        assert profile.niche == "test"
        # Should not raise and unknown fields are silently ignored

    def test_load_profile_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_profile("/nonexistent/path/profile.yml")


class TestGetDefaultProfile:
    def test_returns_valid_profile(self):
        profile = get_default_profile()
        assert isinstance(profile, ChannelProfile)
        assert profile.name == "Default Channel"
        assert profile.niche == "general"
        assert isinstance(profile.voice, VoiceConfig)
        assert isinstance(profile.video, VideoConfig)
