"""Job worker — polls the database for queued jobs and executes them."""

from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from aividio.config.profiles import ChannelProfile, load_profile
from aividio.config.settings import Settings, get_settings
from aividio.db.engine import get_session, init_db
from aividio.db.repos import ChannelRepo, JobRepo, VideoRepo
from aividio.models.job import Job, JobStatus, JobType
from aividio.models.video import VideoStatus
from aividio.pipeline.context import PipelineContext
from aividio.pipeline.orchestrator import PipelineOrchestrator
from aividio.pipeline.stages import STAGE_REGISTRY
from aividio.utils.files import get_work_dir

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Map job types to the subset of stages they should run
_JOB_TYPE_STAGES: dict[JobType, list[str]] = {
    JobType.FULL_PIPELINE: [name for name, _ in STAGE_REGISTRY],
    JobType.SCRIPT_ONLY: ["script_generation"],
    JobType.TTS_ONLY: ["tts"],
    JobType.VIDEO_ONLY: ["media_sourcing", "video_assembly"],
    JobType.UPLOAD_ONLY: ["upload"],
    JobType.THUMBNAIL_ONLY: ["thumbnail"],
}


class JobWorker:
    """Single-threaded job worker that polls the DB for queued jobs.

    Usage::

        worker = JobWorker()
        worker.run_forever()       # blocks until SIGTERM / SIGINT
    """

    def __init__(
        self,
        settings: Settings | None = None,
        poll_interval: float = 5.0,
    ) -> None:
        self.settings = settings or get_settings()
        self.poll_interval = poll_interval
        self._running = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run_forever(self) -> None:
        """Poll for queued jobs and execute them.  Blocks until shutdown."""
        self._running = True
        self._install_signal_handlers()

        init_db()
        logger.info(
            "Worker started — polling every %.1fs (Ctrl+C to stop)",
            self.poll_interval,
        )

        while self._running:
            try:
                job = self._claim_next_job()
                if job:
                    self._execute_job(job)
                else:
                    time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received — shutting down")
                break
            except Exception:
                logger.error("Unexpected worker error", exc_info=True)
                time.sleep(self.poll_interval)

        logger.info("Worker stopped")

    def shutdown(self) -> None:
        """Signal the worker to stop after the current job finishes."""
        logger.info("Shutdown requested")
        self._running = False

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------

    def _claim_next_job(self) -> Job | None:
        """Atomically claim the next queued job from the database."""
        session = get_session()
        try:
            repo = JobRepo(session)
            job = repo.claim_next()
            return job
        except Exception:
            logger.error("Error claiming job", exc_info=True)
            return None
        finally:
            session.close()

    def _execute_job(self, job: Job) -> None:
        """Build context and run the pipeline for a single job."""
        logger.info("Executing job %s (type=%s, video=%s)", job.id, job.job_type.value, job.video_id)

        session = get_session()
        try:
            # Mark job as running with a start time
            job_repo = JobRepo(session)
            db_job = job_repo.get(job.id)
            if db_job:
                db_job.started_at = datetime.now(timezone.utc)
                session.commit()

            # Load related data
            video_repo = VideoRepo(session)
            video = video_repo.get(job.video_id)
            if not video:
                self._fail_job(session, job.id, "Video record not found")
                return

            channel_repo = ChannelRepo(session)
            channel = channel_repo.get(video.channel_id)
            if not channel:
                self._fail_job(session, job.id, "Channel record not found")
                return

            # Load channel profile
            profile = self._load_channel_profile(channel.profile_path)

            # Update video status
            video.status = VideoStatus.GENERATING
            session.commit()

            # Build pipeline context
            work_dir = get_work_dir(video.id)
            ctx = PipelineContext(
                video_id=video.id,
                channel_profile=profile,
                topic=video.topic_prompt,
                format=video.format,
                work_dir=work_dir,
            )

            # Determine which stages to run
            stages = self._get_stages_for_job(job)

            # Build and run orchestrator
            orchestrator = PipelineOrchestrator(
                stages=stages,
                settings=self.settings,
            )

            start_from = job.resume_from_stage if job.resume_from_stage else None

            orchestrator.run(ctx, job_id=job.id, start_from=start_from)

            # Update video with results
            self._update_video_results(session, video.id, ctx)

            logger.info("Job %s completed successfully", job.id)

        except Exception as exc:
            logger.error("Job %s failed: %s", job.id, exc, exc_info=True)
            # Failure is already recorded by the orchestrator; log and move on
        finally:
            session.close()

    def _get_stages_for_job(self, job: Job) -> list[tuple[str, callable]]:
        """Return the filtered stage list based on job type."""
        allowed = _JOB_TYPE_STAGES.get(job.job_type, [name for name, _ in STAGE_REGISTRY])
        return [(name, fn) for name, fn in STAGE_REGISTRY if name in allowed]

    def _load_channel_profile(self, profile_path: str) -> ChannelProfile:
        """Load a channel profile, falling back to default."""
        from aividio.config.profiles import get_default_profile

        try:
            return load_profile(profile_path)
        except FileNotFoundError:
            logger.warning(
                "Profile not found at %s, using defaults", profile_path
            )
            return get_default_profile()

    def _update_video_results(
        self,
        session,
        video_id: str,
        ctx: PipelineContext,
    ) -> None:
        """Write pipeline outputs back to the Video record."""
        video_repo = VideoRepo(session)
        updates: dict = {}

        if ctx.script:
            updates["title"] = ctx.script.get("title", "")
            updates["description"] = ctx.script.get("description", "")
            updates["tags"] = ctx.script.get("tags", [])
            updates["script_json"] = ctx.script

        if ctx.final_video_path:
            updates["file_path"] = str(ctx.final_video_path)

        if ctx.thumbnail_path:
            updates["thumbnail_path"] = str(ctx.thumbnail_path)

        if ctx.voiceover_duration:
            updates["duration_seconds"] = ctx.voiceover_duration

        video_repo.update_status(video_id, VideoStatus.READY, **updates)

    def _fail_job(self, session, job_id: str, error: str) -> None:
        """Mark a job as failed before pipeline execution."""
        job_repo = JobRepo(session)
        job = job_repo.get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error_detail = error
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        logger.error("Job %s failed: %s", job_id, error)

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _install_signal_handlers(self) -> None:
        """Install handlers for graceful shutdown."""
        def _handler(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info("Received %s — requesting graceful shutdown", sig_name)
            self._running = False

        signal.signal(signal.SIGTERM, _handler)
        signal.signal(signal.SIGINT, _handler)
