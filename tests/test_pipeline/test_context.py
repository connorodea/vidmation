"""Tests for PipelineContext — shared mutable state flowing through pipeline stages."""

import json
from pathlib import Path

import pytest

from aividio.config.profiles import ChannelProfile
from aividio.models.video import VideoFormat
from aividio.pipeline.context import PipelineContext


@pytest.fixture
def context(tmp_dir):
    """Create a minimal PipelineContext for testing."""
    return PipelineContext(
        video_id="test-video-001",
        channel_profile=ChannelProfile(name="Test Channel"),
        topic="5 Signs of Spiritual Awakening",
        format=VideoFormat.LANDSCAPE,
        work_dir=tmp_dir,
    )


class TestPipelineContextCreation:
    def test_creation_with_required_fields(self, context):
        assert context.video_id == "test-video-001"
        assert context.topic == "5 Signs of Spiritual Awakening"
        assert context.format == VideoFormat.LANDSCAPE
        assert context.channel_profile.name == "Test Channel"

    def test_default_optional_fields_are_none(self, context):
        assert context.script is None
        assert context.voiceover_path is None
        assert context.voiceover_duration is None
        assert context.word_timestamps is None
        assert context.media_clips is None
        assert context.music_path is None
        assert context.final_video_path is None
        assert context.thumbnail_path is None

    def test_default_stage_tracking(self, context):
        assert context.current_stage == ""
        assert context.completed_stages == []


class TestPipelineContextToDict:
    def test_to_dict_contains_required_keys(self, context):
        d = context.to_dict()
        assert d["video_id"] == "test-video-001"
        assert d["topic"] == "5 Signs of Spiritual Awakening"

    def test_to_dict_converts_paths_to_strings(self, context, tmp_dir):
        d = context.to_dict()
        assert isinstance(d["work_dir"], str)
        assert d["work_dir"] == str(tmp_dir)

    def test_to_dict_converts_voiceover_path(self, context, tmp_dir):
        context.voiceover_path = tmp_dir / "voiceover.mp3"
        d = context.to_dict()
        assert isinstance(d["voiceover_path"], str)

    def test_to_dict_serialises_format_enum(self, context):
        d = context.to_dict()
        # The format should be serialisable as dict (asdict converts enum)
        assert d["format"] is not None

    def test_to_json_returns_valid_json(self, context):
        json_str = context.to_json()
        parsed = json.loads(json_str)
        assert parsed["video_id"] == "test-video-001"
        assert parsed["topic"] == "5 Signs of Spiritual Awakening"


class TestPipelineContextSave:
    def test_save_creates_file_in_work_dir(self, context, tmp_dir):
        saved_path = context.save()
        assert saved_path.exists()
        assert saved_path == tmp_dir / "pipeline_context.json"

    def test_save_writes_valid_json(self, context):
        saved_path = context.save()
        content = saved_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["video_id"] == "test-video-001"

    def test_save_to_custom_path(self, context, tmp_dir):
        custom = tmp_dir / "custom" / "state.json"
        saved_path = context.save(path=custom)
        assert saved_path == custom
        assert custom.exists()

    def test_save_creates_parent_directories(self, context, tmp_dir):
        nested = tmp_dir / "a" / "b" / "c" / "context.json"
        context.save(path=nested)
        assert nested.exists()

    def test_saved_file_can_be_loaded_as_json(self, context):
        saved_path = context.save()
        data = json.loads(saved_path.read_text(encoding="utf-8"))
        assert data["video_id"] == context.video_id
        assert data["topic"] == context.topic


class TestPipelineContextCompletedStages:
    def test_completed_stages_starts_empty(self, context):
        assert context.completed_stages == []

    def test_track_completed_stage(self, context):
        context.completed_stages.append("script_generation")
        assert "script_generation" in context.completed_stages

    def test_track_multiple_stages(self, context):
        stages = ["script_generation", "tts", "media_fetch", "assembly"]
        for stage in stages:
            context.current_stage = stage
            context.completed_stages.append(stage)
        assert context.completed_stages == stages
        assert context.current_stage == "assembly"

    def test_completed_stages_persist_through_save(self, context):
        context.completed_stages.append("script_generation")
        context.completed_stages.append("tts")
        saved_path = context.save()
        data = json.loads(saved_path.read_text(encoding="utf-8"))
        assert data["completed_stages"] == ["script_generation", "tts"]
