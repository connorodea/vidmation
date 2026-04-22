"""Pipeline orchestrator — runs stages in order with persistence and resume."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from aividio.config.settings import Settings, get_settings
from aividio.db.engine import get_session
from aividio.db.repos import JobRepo, VideoRepo
from aividio.models.job import JobStatus
from aividio.models.video import VideoStatus
from aividio.pipeline.stages import STAGE_REGISTRY

if TYPE_CHECKING:
    from aividio.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: str, original: Exception) -> None:
        self.stage = stage
        self.original = original
        super().__init__(f"Pipeline failed at stage '{stage}': {original}")


class PipelineOrchestrator:
    """Runs the video-generation pipeline stages sequentially.

    Features:
    * Ordered execution of registered stages.
    * Resume from a specific stage (skip earlier stages).
    * Context serialisation after each stage for crash recovery.
    * DB updates: Job progress / Video status.
    """

    def __init__(
        self,
        stages: list[tuple[str, Callable]] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.stages = stages or list(STAGE_REGISTRY)
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        context: PipelineContext,
        *,
        job_id: str | None = None,
        start_from: str | None = None,
    ) -> PipelineContext:
        """Execute pipeline stages on *context*.

        Args:
            context: The mutable pipeline context.
            job_id: Optional Job ID for DB progress tracking.
            start_from: If given, skip stages before this one (resume).

        Returns:
            The context after all stages have completed.

        Raises:
            PipelineError: On any stage failure (context is saved first).
        """
        total = len(self.stages)
        skipping = start_from is not None

        logger.info(
            "Pipeline starting for video=%s (%d stages%s)",
            context.video_id,
            total,
            f", resume from '{start_from}'" if start_from else "",
        )

        for idx, (name, stage_fn) in enumerate(self.stages, 1):
            # Handle resume — skip stages until we reach start_from
            if skipping:
                if name == start_from:
                    skipping = False
                else:
                    logger.debug("Skipping stage '%s' (resume mode)", name)
                    continue

            context.current_stage = name
            progress_pct = int((idx / total) * 100)

            self._update_job(job_id, stage=name, progress=progress_pct)
            logger.info(
                "=== Stage %d/%d: %s [%d%%] ===", idx, total, name, progress_pct
            )

            t0 = time.monotonic()
            try:
                stage_fn(context, self.settings)
            except Exception as exc:
                logger.error("Stage '%s' failed: %s", name, exc, exc_info=True)
                # Save context for post-mortem / resume
                self._save_context(context)
                self._record_failure(job_id, context.video_id, name, exc)
                raise PipelineError(name, exc) from exc

            elapsed = time.monotonic() - t0
            context.completed_stages.append(name)

            # Persist context after each stage for crash recovery
            self._save_context(context)

            logger.info("Stage '%s' completed in %.1fs", name, elapsed)

        # All stages done
        self._mark_complete(job_id, context.video_id)
        logger.info("Pipeline completed for video=%s", context.video_id)

        return context

    def get_stages_from(self, start_from: str) -> list[str]:
        """Return the list of stage names starting from *start_from*."""
        names = [name for name, _ in self.stages]
        if start_from not in names:
            raise ValueError(
                f"Unknown stage '{start_from}'. Available: {names}"
            )
        start_idx = names.index(start_from)
        return names[start_idx:]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save_context(self, context: PipelineContext) -> None:
        """Persist pipeline context to disk."""
        try:
            context.save()
        except Exception:
            logger.warning("Failed to save pipeline context", exc_info=True)

    def _update_job(
        self,
        job_id: str | None,
        *,
        stage: str,
        progress: int,
    ) -> None:
        """Update Job record with current stage and progress."""
        if not job_id:
            return
        try:
            session = get_session()
            repo = JobRepo(session)
            job = repo.get(job_id)
            if job:
                job.current_stage = stage
                job.progress_pct = progress
                session.commit()
            session.close()
        except Exception:
            logger.warning("Failed to update job progress", exc_info=True)

    def _record_failure(
        self,
        job_id: str | None,
        video_id: str,
        stage: str,
        exc: Exception,
    ) -> None:
        """Record pipeline failure in both Job and Video records."""
        try:
            session = get_session()
            error_msg = f"Failed at stage '{stage}': {exc}"

            if job_id:
                job_repo = JobRepo(session)
                job = job_repo.get(job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.error_detail = error_msg
                    job.completed_at = datetime.now(timezone.utc)

            video_repo = VideoRepo(session)
            video_repo.update_status(
                video_id,
                VideoStatus.FAILED,
                error_message=error_msg,
            )

            session.commit()
            session.close()
        except Exception:
            logger.warning("Failed to record pipeline failure in DB", exc_info=True)

    def _mark_complete(self, job_id: str | None, video_id: str) -> None:
        """Mark both Job and Video as completed."""
        try:
            session = get_session()

            if job_id:
                job_repo = JobRepo(session)
                job = job_repo.get(job_id)
                if job:
                    job.status = JobStatus.COMPLETED
                    job.progress_pct = 100
                    job.current_stage = "done"
                    job.completed_at = datetime.now(timezone.utc)

            video_repo = VideoRepo(session)
            video_repo.update_status(video_id, VideoStatus.READY)

            session.commit()
            session.close()
        except Exception:
            logger.warning("Failed to mark pipeline complete in DB", exc_info=True)
