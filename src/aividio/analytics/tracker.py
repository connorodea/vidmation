"""Usage tracker - records all API calls and computes costs."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from aividio.db.engine import get_session
from aividio.models.analytics import CostSummary, UsageEvent

logger = logging.getLogger("aividio.analytics.tracker")

_tracker_instance: UsageTracker | None = None


class UsageTracker:
    """Tracks all API usage and costs for transparency.

    Call ``get_tracker()`` to obtain the singleton instance.
    """

    # Cost per unit for each service. Values are in USD.
    COST_TABLE: dict[str, dict[str, float]] = {
        "claude": {"input_token": 0.000003, "output_token": 0.000015},
        "openai_gpt4o": {"input_token": 0.0000025, "output_token": 0.00001},
        "elevenlabs": {"character": 0.00003},
        "openai_tts": {"character": 0.000015},
        "dalle3": {"image_1024": 0.04, "image_1792": 0.08},
        "replicate_flux": {"image": 0.003},
        "replicate_kling": {"second": 0.05},
        "fal_flux": {"image": 0.0025},
        "fal_kling": {"second": 0.04},
        "whisper_local": {"minute": 0.0},
        "whisper_replicate": {"minute": 0.006},
        "pexels": {"request": 0.0},
        "pixabay": {"request": 0.0},
        "youtube_upload": {"upload": 0.0},
    }

    # ---------- Core tracking ----------

    def track(
        self,
        service: str,
        operation: str,
        cost_usd: float | None = None,
        video_id: str | None = None,
        job_id: str | None = None,
        tokens_used: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        duration_seconds: float | None = None,
        characters: int | None = None,
        images: int | None = None,
        image_size: str | None = None,
        model_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UsageEvent:
        """Log a usage event to the database.

        If *cost_usd* is not provided, it is automatically estimated from
        the COST_TABLE using the supplied quantity parameters.
        """
        if cost_usd is None:
            cost_usd = self._estimate_cost(
                service=service,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                tokens_used=tokens_used,
                duration_seconds=duration_seconds,
                characters=characters,
                images=images,
                image_size=image_size,
            )

        # Combine input + output tokens if both given
        total_tokens = tokens_used
        if total_tokens is None and (input_tokens or output_tokens):
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        now = datetime.now(timezone.utc)

        session = get_session()
        try:
            event = UsageEvent(
                timestamp=now,
                service=service,
                operation=operation,
                video_id=video_id,
                job_id=job_id,
                tokens_used=total_tokens,
                duration_seconds=duration_seconds,
                cost_usd=cost_usd,
                model_name=model_name,
                metadata_json=metadata,
            )
            session.add(event)
            session.commit()
            session.refresh(event)

            logger.info(
                "Tracked: %s/%s cost=$%.4f video=%s",
                service,
                operation,
                cost_usd,
                video_id[:8] if video_id else "n/a",
            )
            return event
        except Exception:
            session.rollback()
            logger.exception("Failed to track usage event")
            raise
        finally:
            session.close()

    # ---------- Cost estimation ----------

    def _estimate_cost(
        self,
        service: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        tokens_used: int | None = None,
        duration_seconds: float | None = None,
        characters: int | None = None,
        images: int | None = None,
        image_size: str | None = None,
    ) -> float:
        """Estimate the cost of an API call from the COST_TABLE."""
        rates = self.COST_TABLE.get(service)
        if not rates:
            return 0.0

        cost = 0.0

        # LLM token-based pricing
        if input_tokens and "input_token" in rates:
            cost += input_tokens * rates["input_token"]
        if output_tokens and "output_token" in rates:
            cost += output_tokens * rates["output_token"]
        if tokens_used and "input_token" in rates and not input_tokens:
            # Approximate: assume 70% input, 30% output
            cost += tokens_used * 0.7 * rates["input_token"]
            cost += tokens_used * 0.3 * rates.get("output_token", rates["input_token"])

        # TTS character-based pricing
        if characters and "character" in rates:
            cost += characters * rates["character"]

        # Image generation pricing
        if images:
            if image_size and f"image_{image_size}" in rates:
                cost += images * rates[f"image_{image_size}"]
            elif "image" in rates:
                cost += images * rates["image"]
            elif "image_1024" in rates:
                cost += images * rates["image_1024"]

        # Duration-based pricing (video gen, transcription)
        if duration_seconds:
            if "second" in rates:
                cost += duration_seconds * rates["second"]
            elif "minute" in rates:
                cost += (duration_seconds / 60.0) * rates["minute"]

        # Flat per-request pricing
        if "request" in rates and not any([
            input_tokens, output_tokens, tokens_used,
            characters, images, duration_seconds,
        ]):
            cost += rates["request"]

        if "upload" in rates and not any([
            input_tokens, output_tokens, tokens_used,
            characters, images, duration_seconds,
        ]):
            cost += rates["upload"]

        return round(cost, 6)

    def estimate_video_cost(
        self,
        profile_name: str = "default",
        duration_minutes: float = 10.0,
        llm_provider: str = "claude",
        tts_provider: str = "elevenlabs",
        image_provider: str = "dalle3",
        num_images: int = 15,
        include_thumbnail: bool = True,
    ) -> dict[str, Any]:
        """Pre-calculate expected cost for a video before generation.

        Returns a breakdown dict with per-service costs and total.
        """
        breakdown: dict[str, float] = {}
        duration_seconds = duration_minutes * 60

        # Script generation: ~2000 input tokens, ~4000 output tokens
        script_input = 2000
        script_output = 4000
        breakdown["script_gen"] = self._estimate_cost(
            service=llm_provider,
            input_tokens=script_input,
            output_tokens=script_output,
        )

        # TTS: ~150 words/min, ~5 chars/word = ~750 chars/min
        total_chars = int(duration_minutes * 750)
        breakdown["tts"] = self._estimate_cost(
            service=tts_provider,
            characters=total_chars,
        )

        # Image generation
        breakdown["images"] = self._estimate_cost(
            service=image_provider,
            images=num_images,
        )

        # Thumbnail
        if include_thumbnail:
            breakdown["thumbnail"] = self._estimate_cost(
                service=image_provider,
                images=1,
            )
        else:
            breakdown["thumbnail"] = 0.0

        # Transcription for caption alignment (local whisper = free)
        breakdown["transcription"] = self._estimate_cost(
            service="whisper_local",
            duration_seconds=duration_seconds,
        )

        # Stock media search (free)
        breakdown["stock_media"] = 0.0

        # YouTube upload (free)
        breakdown["upload"] = 0.0

        total = sum(breakdown.values())

        return {
            "profile": profile_name,
            "estimated_duration_minutes": duration_minutes,
            "breakdown": breakdown,
            "total_usd": round(total, 4),
            "llm_provider": llm_provider,
            "tts_provider": tts_provider,
            "image_provider": image_provider,
        }

    # ---------- Summaries ----------

    def get_daily_summary(self, target_date: date | None = None) -> dict[str, Any]:
        """Get cost breakdown for a specific day."""
        if target_date is None:
            target_date = date.today()

        day_start = datetime(
            target_date.year, target_date.month, target_date.day,
            tzinfo=timezone.utc,
        )
        day_end = day_start + timedelta(days=1)

        session = get_session()
        try:
            stmt = (
                select(
                    UsageEvent.service,
                    func.count(UsageEvent.id).label("calls"),
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.coalesce(func.sum(UsageEvent.tokens_used), 0).label("tokens"),
                    func.coalesce(func.sum(UsageEvent.duration_seconds), 0.0).label("duration"),
                )
                .where(UsageEvent.timestamp >= day_start)
                .where(UsageEvent.timestamp < day_end)
                .group_by(UsageEvent.service)
            )
            rows = session.execute(stmt).all()

            by_service = {}
            total_cost = 0.0
            total_calls = 0
            for row in rows:
                by_service[row.service] = {
                    "calls": row.calls,
                    "cost_usd": round(float(row.cost), 4),
                    "tokens": row.tokens,
                    "duration_seconds": round(float(row.duration), 2),
                }
                total_cost += float(row.cost)
                total_calls += row.calls

            return {
                "date": target_date.isoformat(),
                "total_cost_usd": round(total_cost, 4),
                "total_calls": total_calls,
                "by_service": by_service,
            }
        finally:
            session.close()

    def get_monthly_summary(self, year: int, month: int) -> dict[str, Any]:
        """Get cost breakdown for a month."""
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        session = get_session()
        try:
            # Per-service breakdown
            stmt = (
                select(
                    UsageEvent.service,
                    func.count(UsageEvent.id).label("calls"),
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.coalesce(func.sum(UsageEvent.tokens_used), 0).label("tokens"),
                    func.coalesce(func.sum(UsageEvent.duration_seconds), 0.0).label("duration"),
                )
                .where(UsageEvent.timestamp >= month_start)
                .where(UsageEvent.timestamp < month_end)
                .group_by(UsageEvent.service)
            )
            rows = session.execute(stmt).all()

            by_service = {}
            total_cost = 0.0
            total_calls = 0
            for row in rows:
                by_service[row.service] = {
                    "calls": row.calls,
                    "cost_usd": round(float(row.cost), 4),
                    "tokens": row.tokens,
                    "duration_seconds": round(float(row.duration), 2),
                }
                total_cost += float(row.cost)
                total_calls += row.calls

            # Daily breakdown for charting
            daily_stmt = (
                select(
                    func.date(UsageEvent.timestamp).label("day"),
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.count(UsageEvent.id).label("calls"),
                )
                .where(UsageEvent.timestamp >= month_start)
                .where(UsageEvent.timestamp < month_end)
                .group_by(func.date(UsageEvent.timestamp))
                .order_by(func.date(UsageEvent.timestamp))
            )
            daily_rows = session.execute(daily_stmt).all()

            daily = [
                {
                    "date": str(row.day),
                    "cost_usd": round(float(row.cost), 4),
                    "calls": row.calls,
                }
                for row in daily_rows
            ]

            return {
                "year": year,
                "month": month,
                "total_cost_usd": round(total_cost, 4),
                "total_calls": total_calls,
                "by_service": by_service,
                "daily": daily,
            }
        finally:
            session.close()

    def get_video_cost(self, video_id: str) -> dict[str, Any]:
        """Get total cost breakdown for a specific video."""
        session = get_session()
        try:
            stmt = (
                select(
                    UsageEvent.service,
                    UsageEvent.operation,
                    func.count(UsageEvent.id).label("calls"),
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.coalesce(func.sum(UsageEvent.tokens_used), 0).label("tokens"),
                    func.coalesce(func.sum(UsageEvent.duration_seconds), 0.0).label("duration"),
                )
                .where(UsageEvent.video_id == video_id)
                .group_by(UsageEvent.service, UsageEvent.operation)
            )
            rows = session.execute(stmt).all()

            by_operation: dict[str, dict] = {}
            total_cost = 0.0
            total_calls = 0
            for row in rows:
                key = f"{row.service}/{row.operation}"
                by_operation[key] = {
                    "service": row.service,
                    "operation": row.operation,
                    "calls": row.calls,
                    "cost_usd": round(float(row.cost), 4),
                    "tokens": row.tokens,
                    "duration_seconds": round(float(row.duration), 2),
                }
                total_cost += float(row.cost)
                total_calls += row.calls

            # Also get individual events for a detailed timeline
            events_stmt = (
                select(UsageEvent)
                .where(UsageEvent.video_id == video_id)
                .order_by(UsageEvent.timestamp.asc())
            )
            events = session.scalars(events_stmt).all()

            timeline = [
                {
                    "timestamp": ev.timestamp.isoformat() if hasattr(ev.timestamp, "isoformat") else str(ev.timestamp),
                    "service": ev.service,
                    "operation": ev.operation,
                    "cost_usd": round(ev.cost_usd, 4),
                    "model": ev.model_name,
                }
                for ev in events
            ]

            return {
                "video_id": video_id,
                "total_cost_usd": round(total_cost, 4),
                "total_calls": total_calls,
                "by_operation": by_operation,
                "timeline": timeline,
            }
        finally:
            session.close()

    def get_recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get the most recent usage events."""
        session = get_session()
        try:
            stmt = (
                select(UsageEvent)
                .order_by(UsageEvent.timestamp.desc())
                .limit(limit)
            )
            events = session.scalars(stmt).all()

            return [
                {
                    "id": ev.id,
                    "timestamp": ev.timestamp.isoformat() if hasattr(ev.timestamp, "isoformat") else str(ev.timestamp),
                    "service": ev.service,
                    "operation": ev.operation,
                    "cost_usd": round(ev.cost_usd, 4),
                    "tokens_used": ev.tokens_used,
                    "duration_seconds": round(ev.duration_seconds, 2) if ev.duration_seconds else None,
                    "model_name": ev.model_name,
                    "video_id": ev.video_id,
                    "job_id": ev.job_id,
                }
                for ev in events
            ]
        finally:
            session.close()

    # ---------- Aggregation ----------

    def rebuild_cost_summaries(self, period_type: str = "daily") -> int:
        """Rebuild aggregated cost summaries from raw events.

        Returns the number of summary rows created/updated.
        """
        session = get_session()
        try:
            if period_type == "daily":
                stmt = (
                    select(
                        func.date(UsageEvent.timestamp).label("day"),
                        UsageEvent.service,
                        func.count(UsageEvent.id).label("calls"),
                        func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                        func.coalesce(func.sum(UsageEvent.tokens_used), 0).label("tokens"),
                        func.coalesce(func.sum(UsageEvent.duration_seconds), 0.0).label("duration"),
                    )
                    .group_by(func.date(UsageEvent.timestamp), UsageEvent.service)
                )
                rows = session.execute(stmt).all()

                # Clear existing daily summaries
                session.query(CostSummary).filter(
                    CostSummary.period_type == "daily"
                ).delete()

                count = 0
                for row in rows:
                    day = row.day
                    if isinstance(day, str):
                        day_dt = datetime.fromisoformat(day)
                    else:
                        day_dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)

                    summary = CostSummary(
                        period_type="daily",
                        period_start=day_dt,
                        period_end=day_dt + timedelta(days=1),
                        service=row.service,
                        total_cost_usd=round(float(row.cost), 4),
                        total_calls=row.calls,
                        total_tokens=row.tokens or 0,
                        total_duration_seconds=round(float(row.duration), 2),
                    )
                    session.add(summary)
                    count += 1

                session.commit()
                logger.info("Rebuilt %d daily cost summaries", count)
                return count

            return 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_tracker() -> UsageTracker:
    """Get the singleton UsageTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = UsageTracker()
    return _tracker_instance
