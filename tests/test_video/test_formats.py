"""Tests for video format specifications."""

import pytest

from vidmation.video.formats import (
    FORMAT_REGISTRY,
    LANDSCAPE,
    PORTRAIT,
    SHORT,
    FormatSpec,
    get_format,
)


class TestLandscapeFormat:
    def test_landscape_width(self):
        assert LANDSCAPE.width == 1920

    def test_landscape_height(self):
        assert LANDSCAPE.height == 1080

    def test_landscape_resolution_string(self):
        assert LANDSCAPE.resolution == "1920x1080"

    def test_landscape_fps(self):
        assert LANDSCAPE.fps == 30

    def test_landscape_no_max_duration(self):
        assert LANDSCAPE.max_duration is None


class TestPortraitFormat:
    def test_portrait_width(self):
        assert PORTRAIT.width == 1080

    def test_portrait_height(self):
        assert PORTRAIT.height == 1920

    def test_portrait_resolution_string(self):
        assert PORTRAIT.resolution == "1080x1920"

    def test_portrait_fps(self):
        assert PORTRAIT.fps == 30

    def test_portrait_no_max_duration(self):
        assert PORTRAIT.max_duration is None


class TestShortFormat:
    def test_short_width(self):
        assert SHORT.width == 1080

    def test_short_height(self):
        assert SHORT.height == 1920

    def test_short_max_duration_60(self):
        assert SHORT.max_duration == 60.0

    def test_short_fps(self):
        assert SHORT.fps == 30

    def test_short_lower_bitrate(self):
        assert SHORT.video_bitrate == "6M"


class TestGetFormat:
    def test_get_format_landscape(self):
        fmt = get_format("landscape")
        assert fmt is LANDSCAPE

    def test_get_format_portrait(self):
        fmt = get_format("portrait")
        assert fmt is PORTRAIT

    def test_get_format_short(self):
        fmt = get_format("short")
        assert fmt is SHORT

    def test_get_format_case_insensitive(self):
        fmt = get_format("LANDSCAPE")
        assert fmt is LANDSCAPE

    def test_get_format_strips_whitespace(self):
        fmt = get_format("  portrait  ")
        assert fmt is PORTRAIT

    def test_get_format_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown video format"):
            get_format("invalid")

    def test_get_format_empty_string_raises(self):
        with pytest.raises(ValueError):
            get_format("")


class TestFormatSpec:
    def test_format_spec_is_frozen(self):
        with pytest.raises(AttributeError):
            LANDSCAPE.width = 3840  # type: ignore[misc]

    def test_ffmpeg_output_kwargs_keys(self):
        kwargs = LANDSCAPE.ffmpeg_output_kwargs()
        assert "vcodec" in kwargs
        assert "acodec" in kwargs
        assert "preset" in kwargs
        assert "crf" in kwargs

    def test_format_registry_has_three_entries(self):
        assert len(FORMAT_REGISTRY) == 3
        assert "landscape" in FORMAT_REGISTRY
        assert "portrait" in FORMAT_REGISTRY
        assert "short" in FORMAT_REGISTRY
