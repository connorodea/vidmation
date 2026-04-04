"""Task creation helpers — enqueue work for the job worker."""

from __future__ import annotations

import logging

from vidmation.db.engine import get_session, init_db
from vidmation.db.repos import ChannelRepo, JobRepo, VideoRepo
from vidmation.models.job import Job, JobStatus, JobType
from vidmation.models.video import Video, VideoFormat, VideoStatus

logger = logging.getLogger(__name__)


def enqueue_video(
    topic: str,
    channel_name: str = "default",
    format: str | VideoFormat = VideoFormat.LANDSCAPE,
    job_type: str | JobType = JobType.FULL_PIPELINE,
) -> tuple[Video, Job]:
    """Create a Video + Job record pair and return them.

    The worker will pick up the queued job automatically on its next poll.

    Args:
        topic: The video topic / prompt.
        channel_name: Name of the channel to use.  Must already exist in DB.
        format: Video format (landscape / portrait / short).
        job_type: Pipeline scope (full_pipeline, script_only, etc.).

    Returns:
        A ``(Video, Job)`` tuple with the newly created records.

    Raises:
        ValueError: If the channel is not found.
    """
    init_db()

    # Normalise enums
    if isinstance(format, str):
        format = VideoFormat(format)
    if isinstance(job_type, str):
        job_type = JobType(job_type)

    session = get_session()
    try:
        # Resolve channel
        channel_repo = ChannelRepo(session)
        channel = channel_repo.get_by_name(channel_name)
        if channel is None:
            raise ValueError(
                f"Channel '{channel_name}' not found.  "
                f"Create it first with:  vidmation channel add --name '{channel_name}'"
            )

        # Create video
        video_repo = VideoRepo(session)
        video = video_repo.create(
            channel_id=channel.id,
            topic_prompt=topic,
            format=format,
            status=VideoStatus.DRAFT,
        )

        # Create job
        job_repo = JobRepo(session)
        job = job_repo.create(
            video_id=video.id,
            job_type=job_type,
            status=JobStatus.QUEUED,
        )

        logger.info(
            "Enqueued %s job %s for video %s (topic=%r, channel=%s)",
            job_type.value,
            job.id,
            video.id,
            topic,
            channel_name,
        )

        return video, job

    finally:
        session.close()


def enqueue_retry(
    job_id: str,
    resume_from: str | None = None,
) -> Job:
    """Re-queue a failed job, optionally resuming from a specific stage.

    Args:
        job_id: The ID of the original failed job.
        resume_from: Stage name to resume from.  If *None*, the job's
            ``current_stage`` (where it failed) is used.

    Returns:
        The newly created retry Job record.

    Raises:
        ValueError: If the original job is not found or not in a retryable state.
    """
    init_db()

    session = get_session()
    try:
        job_repo = JobRepo(session)
        original = job_repo.get(job_id)

        if original is None:
            raise ValueError(f"Job '{job_id}' not found")

        if original.status not in (JobStatus.FAILED, JobStatus.CANCELLED):
            raise ValueError(
                f"Job '{job_id}' is in state '{original.status.value}' — "
                f"only FAILED or CANCELLED jobs can be retried"
            )

        # Determine resume point
        stage = resume_from or original.current_stage or None

        new_job = job_repo.create(
            video_id=original.video_id,
            job_type=original.job_type,
            status=JobStatus.QUEUED,
            resume_from_stage=stage,
        )

        # Reset the video status so the pipeline can proceed
        video_repo = VideoRepo(session)
        video_repo.update_status(original.video_id, VideoStatus.DRAFT)

        logger.info(
            "Retry job %s created for video %s (resume_from=%s)",
            new_job.id,
            original.video_id,
            stage,
        )

        return new_job

    finally:
        session.close()
