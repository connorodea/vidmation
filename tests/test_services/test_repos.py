"""Tests for database repository pattern — ChannelRepo, VideoRepo, JobRepo."""

import pytest

from aividio.db.repos import ChannelRepo, JobRepo, VideoRepo
from aividio.models.job import JobStatus, JobType
from aividio.models.video import VideoFormat, VideoStatus


class TestChannelRepo:
    def test_channel_repo_create_sets_id(self, db_session):
        repo = ChannelRepo(db_session)
        channel = repo.create(name="Test Channel")
        assert channel.id is not None
        assert len(channel.id) == 36  # UUID format

    def test_channel_repo_create_sets_name(self, db_session):
        repo = ChannelRepo(db_session)
        channel = repo.create(name="My Channel")
        assert channel.name == "My Channel"

    def test_channel_repo_create_defaults_active(self, db_session):
        repo = ChannelRepo(db_session)
        channel = repo.create(name="Active Channel")
        assert channel.is_active is True

    def test_channel_repo_get_returns_channel(self, db_session):
        repo = ChannelRepo(db_session)
        created = repo.create(name="Get Test")
        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Get Test"

    def test_channel_repo_get_returns_none_for_missing(self, db_session):
        repo = ChannelRepo(db_session)
        assert repo.get("nonexistent-id") is None

    def test_channel_repo_get_by_name(self, db_session):
        repo = ChannelRepo(db_session)
        repo.create(name="Unique Channel")
        found = repo.get_by_name("Unique Channel")
        assert found is not None
        assert found.name == "Unique Channel"

    def test_channel_repo_get_by_name_returns_none(self, db_session):
        repo = ChannelRepo(db_session)
        assert repo.get_by_name("No Such Channel") is None

    def test_channel_repo_list_all_returns_active(self, db_session):
        repo = ChannelRepo(db_session)
        repo.create(name="Channel A")
        repo.create(name="Channel B")
        channels = repo.list_all(active_only=True)
        assert len(channels) == 2

    def test_channel_repo_list_all_includes_inactive(self, db_session):
        repo = ChannelRepo(db_session)
        repo.create(name="Active Channel")
        repo.create(name="Inactive Channel", is_active=False)
        active_only = repo.list_all(active_only=True)
        all_channels = repo.list_all(active_only=False)
        assert len(active_only) == 1
        assert len(all_channels) == 2


class TestVideoRepo:
    @pytest.fixture
    def channel(self, db_session):
        repo = ChannelRepo(db_session)
        return repo.create(name="Video Test Channel")

    def test_video_repo_create_sets_id(self, db_session, channel):
        repo = VideoRepo(db_session)
        video = repo.create(
            channel_id=channel.id,
            topic_prompt="Test topic",
        )
        assert video.id is not None
        assert len(video.id) == 36

    def test_video_repo_create_default_status(self, db_session, channel):
        repo = VideoRepo(db_session)
        video = repo.create(
            channel_id=channel.id,
            topic_prompt="Test topic",
        )
        assert video.status == VideoStatus.DRAFT

    def test_video_repo_list_by_channel(self, db_session, channel):
        repo = VideoRepo(db_session)
        repo.create(channel_id=channel.id, topic_prompt="Topic 1")
        repo.create(channel_id=channel.id, topic_prompt="Topic 2")
        repo.create(channel_id=channel.id, topic_prompt="Topic 3")
        videos = repo.list_by_channel(channel.id)
        assert len(videos) == 3

    def test_video_repo_list_by_channel_empty(self, db_session, channel):
        repo = VideoRepo(db_session)
        videos = repo.list_by_channel(channel.id)
        assert videos == []

    def test_video_repo_update_status(self, db_session, channel):
        repo = VideoRepo(db_session)
        video = repo.create(
            channel_id=channel.id,
            topic_prompt="Status test",
        )
        updated = repo.update_status(video.id, VideoStatus.GENERATING)
        assert updated is not None
        assert updated.status == VideoStatus.GENERATING

    def test_video_repo_update_status_with_kwargs(self, db_session, channel):
        repo = VideoRepo(db_session)
        video = repo.create(
            channel_id=channel.id,
            topic_prompt="Error test",
        )
        updated = repo.update_status(
            video.id,
            VideoStatus.FAILED,
            error_message="Something went wrong",
        )
        assert updated is not None
        assert updated.status == VideoStatus.FAILED
        assert updated.error_message == "Something went wrong"

    def test_video_repo_update_status_missing_id(self, db_session):
        repo = VideoRepo(db_session)
        result = repo.update_status("nonexistent-id", VideoStatus.READY)
        assert result is None


class TestJobRepo:
    @pytest.fixture
    def video(self, db_session):
        ch_repo = ChannelRepo(db_session)
        channel = ch_repo.create(name="Job Test Channel")
        v_repo = VideoRepo(db_session)
        return v_repo.create(channel_id=channel.id, topic_prompt="Job topic")

    def test_job_repo_create_sets_id(self, db_session, video):
        repo = JobRepo(db_session)
        job = repo.create(video_id=video.id)
        assert job.id is not None
        assert len(job.id) == 36

    def test_job_repo_create_default_status(self, db_session, video):
        repo = JobRepo(db_session)
        job = repo.create(video_id=video.id)
        assert job.status == JobStatus.QUEUED

    def test_job_repo_create_default_type(self, db_session, video):
        repo = JobRepo(db_session)
        job = repo.create(video_id=video.id)
        assert job.job_type == JobType.FULL_PIPELINE

    def test_job_repo_claim_next_returns_oldest_queued(self, db_session, video):
        repo = JobRepo(db_session)
        job1 = repo.create(video_id=video.id)
        job2 = repo.create(video_id=video.id)
        claimed = repo.claim_next()
        assert claimed is not None
        assert claimed.id == job1.id
        assert claimed.status == JobStatus.RUNNING

    def test_job_repo_claim_next_returns_none_when_empty(self, db_session):
        repo = JobRepo(db_session)
        assert repo.claim_next() is None

    def test_job_repo_claim_next_skips_running_jobs(self, db_session, video):
        repo = JobRepo(db_session)
        job1 = repo.create(video_id=video.id)
        # Claim the first job (sets it to RUNNING)
        repo.claim_next()
        job2 = repo.create(video_id=video.id)
        claimed = repo.claim_next()
        assert claimed is not None
        assert claimed.id == job2.id

    def test_job_repo_list_all_returns_jobs(self, db_session, video):
        repo = JobRepo(db_session)
        repo.create(video_id=video.id)
        repo.create(video_id=video.id)
        jobs = repo.list_all()
        assert len(jobs) == 2

    def test_job_repo_list_all_with_status_filter(self, db_session, video):
        repo = JobRepo(db_session)
        repo.create(video_id=video.id)
        repo.create(video_id=video.id)
        # Claim one to make it RUNNING
        repo.claim_next()

        queued = repo.list_all(status=JobStatus.QUEUED)
        running = repo.list_all(status=JobStatus.RUNNING)
        assert len(queued) == 1
        assert len(running) == 1
