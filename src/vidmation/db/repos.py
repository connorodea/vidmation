"""Repository pattern for database CRUD operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vidmation.models.channel import Channel
from vidmation.models.job import Job, JobStatus
from vidmation.models.video import Video, VideoStatus


class ChannelRepo:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> Channel:
        channel = Channel(**kwargs)
        self.session.add(channel)
        self.session.commit()
        self.session.refresh(channel)
        return channel

    def get(self, channel_id: str) -> Channel | None:
        return self.session.get(Channel, channel_id)

    def get_by_name(self, name: str) -> Channel | None:
        stmt = select(Channel).where(Channel.name == name)
        return self.session.scalars(stmt).first()

    def list_all(self, active_only: bool = True) -> list[Channel]:
        stmt = select(Channel).order_by(Channel.created_at.desc())
        if active_only:
            stmt = stmt.where(Channel.is_active.is_(True))
        return list(self.session.scalars(stmt).all())


class VideoRepo:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> Video:
        video = Video(**kwargs)
        self.session.add(video)
        self.session.commit()
        self.session.refresh(video)
        return video

    def get(self, video_id: str) -> Video | None:
        return self.session.get(Video, video_id)

    def list_by_channel(self, channel_id: str) -> list[Video]:
        stmt = (
            select(Video)
            .where(Video.channel_id == channel_id)
            .order_by(Video.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_all(self, status: VideoStatus | None = None, limit: int = 50) -> list[Video]:
        stmt = select(Video).order_by(Video.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(Video.status == status)
        return list(self.session.scalars(stmt).all())

    def update_status(self, video_id: str, status: VideoStatus, **kwargs) -> Video | None:
        video = self.get(video_id)
        if video:
            video.status = status
            for key, value in kwargs.items():
                setattr(video, key, value)
            self.session.commit()
            self.session.refresh(video)
        return video


class JobRepo:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> Job:
        job = Job(**kwargs)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.session.get(Job, job_id)

    def claim_next(self) -> Job | None:
        """Atomically claim the next queued job."""
        stmt = (
            select(Job)
            .where(Job.status == JobStatus.QUEUED)
            .order_by(Job.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = self.session.scalars(stmt).first()
        if job:
            job.status = JobStatus.RUNNING
            self.session.commit()
            self.session.refresh(job)
        return job

    def list_all(self, status: JobStatus | None = None, limit: int = 50) -> list[Job]:
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(Job.status == status)
        return list(self.session.scalars(stmt).all())
