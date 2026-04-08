"""Report generator - produces cost, performance, efficiency, and content reports."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from vidmation.db.engine import get_session
from vidmation.models.analytics import UsageEvent, VideoAnalytics
from vidmation.models.video import Video, VideoStatus

logger = logging.getLogger("vidmation.analytics.reports")


class ReportGenerator:
    """Produces analytics reports for the dashboard and API."""

    # ---------- Cost Reports ----------

    def cost_report(self, period: str = "monthly") -> dict[str, Any]:
        """Generate a cost breakdown report.

        Args:
            period: ``"daily"`` (today), ``"weekly"`` (last 7 days),
                    or ``"monthly"`` (last 30 days).

        Returns:
            Dict with total cost, per-service breakdown, and daily trend data.
        """
        now = datetime.now(timezone.utc)
        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start = now - timedelta(days=7)
        else:  # monthly
            start = now - timedelta(days=30)

        session = get_session()
        try:
            # Per-service breakdown
            service_stmt = (
                select(
                    UsageEvent.service,
                    func.count(UsageEvent.id).label("calls"),
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.coalesce(func.sum(UsageEvent.tokens_used), 0).label("tokens"),
                )
                .where(UsageEvent.timestamp >= start)
                .group_by(UsageEvent.service)
                .order_by(func.sum(UsageEvent.cost_usd).desc())
            )
            service_rows = session.execute(service_stmt).all()

            by_service = [
                {
                    "service": row.service,
                    "calls": row.calls,
                    "cost_usd": round(float(row.cost), 4),
                    "tokens": row.tokens or 0,
                }
                for row in service_rows
            ]
            total_cost = sum(s["cost_usd"] for s in by_service)
            total_calls = sum(s["calls"] for s in by_service)

            # Daily trend
            daily_stmt = (
                select(
                    func.date(UsageEvent.timestamp).label("day"),
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.count(UsageEvent.id).label("calls"),
                )
                .where(UsageEvent.timestamp >= start)
                .group_by(func.date(UsageEvent.timestamp))
                .order_by(func.date(UsageEvent.timestamp))
            )
            daily_rows = session.execute(daily_stmt).all()

            daily_trend = [
                {
                    "date": str(row.day),
                    "cost_usd": round(float(row.cost), 4),
                    "calls": row.calls,
                }
                for row in daily_rows
            ]

            # Top 5 most expensive videos
            video_cost_stmt = (
                select(
                    UsageEvent.video_id,
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                    func.count(UsageEvent.id).label("calls"),
                )
                .where(UsageEvent.timestamp >= start)
                .where(UsageEvent.video_id.isnot(None))
                .group_by(UsageEvent.video_id)
                .order_by(func.sum(UsageEvent.cost_usd).desc())
                .limit(5)
            )
            video_cost_rows = session.execute(video_cost_stmt).all()

            top_videos = []
            for row in video_cost_rows:
                video = session.get(Video, row.video_id)
                top_videos.append({
                    "video_id": row.video_id,
                    "title": video.title if video else "Unknown",
                    "cost_usd": round(float(row.cost), 4),
                    "calls": row.calls,
                })

            return {
                "period": period,
                "start": start.isoformat(),
                "end": now.isoformat(),
                "total_cost_usd": round(total_cost, 4),
                "total_calls": total_calls,
                "by_service": by_service,
                "daily_trend": daily_trend,
                "top_expensive_videos": top_videos,
            }
        finally:
            session.close()

    # ---------- Performance Reports ----------

    def performance_report(self, channel_id: str | None = None) -> dict[str, Any]:
        """Generate video performance metrics report.

        Args:
            channel_id: Optional filter to a specific channel.

        Returns:
            Dict with per-video stats, totals, and rankings.
        """
        session = get_session()
        try:
            # Get the latest analytics snapshot for each video
            subquery = (
                select(
                    VideoAnalytics.video_id,
                    func.max(VideoAnalytics.fetched_at).label("latest"),
                )
                .group_by(VideoAnalytics.video_id)
                .subquery()
            )

            stmt = (
                select(VideoAnalytics)
                .join(
                    subquery,
                    (VideoAnalytics.video_id == subquery.c.video_id)
                    & (VideoAnalytics.fetched_at == subquery.c.latest),
                )
            )

            if channel_id:
                stmt = stmt.join(Video, VideoAnalytics.video_id == Video.id).where(
                    Video.channel_id == channel_id
                )

            analytics_rows = list(session.scalars(stmt).all())

            video_stats = []
            total_views = 0
            total_likes = 0
            total_watch_hours = 0.0
            total_subscribers = 0

            for a in analytics_rows:
                video = session.get(Video, a.video_id)
                video_stats.append({
                    "video_id": a.video_id,
                    "title": video.title if video else "Unknown",
                    "views": a.views,
                    "likes": a.likes,
                    "comments": a.comments,
                    "shares": a.shares,
                    "watch_time_hours": round(a.watch_time_hours, 2),
                    "avg_view_duration_seconds": round(a.avg_view_duration_seconds, 1),
                    "avg_view_percentage": round(a.avg_view_percentage, 1),
                    "click_through_rate": round(a.click_through_rate, 2),
                    "impressions": a.impressions,
                    "subscriber_gain": a.subscriber_gain,
                })
                total_views += a.views
                total_likes += a.likes
                total_watch_hours += a.watch_time_hours
                total_subscribers += a.subscriber_gain

            # Sort by views descending for best performing
            video_stats.sort(key=lambda x: x["views"], reverse=True)

            return {
                "channel_id": channel_id,
                "total_videos_tracked": len(video_stats),
                "total_views": total_views,
                "total_likes": total_likes,
                "total_watch_time_hours": round(total_watch_hours, 2),
                "total_subscriber_gain": total_subscribers,
                "avg_views_per_video": (
                    round(total_views / len(video_stats))
                    if video_stats
                    else 0
                ),
                "videos": video_stats,
                "top_5_by_views": video_stats[:5],
            }
        finally:
            session.close()

    # ---------- Efficiency Reports ----------

    def efficiency_report(self) -> dict[str, Any]:
        """Generate cost-per-performance metrics.

        Calculates ROI metrics by combining usage costs with YouTube performance.

        Returns:
            Dict with cost-per-view, cost-per-subscriber, and video-level ROI.
        """
        session = get_session()
        try:
            # Get per-video costs
            cost_stmt = (
                select(
                    UsageEvent.video_id,
                    func.coalesce(func.sum(UsageEvent.cost_usd), 0.0).label("cost"),
                )
                .where(UsageEvent.video_id.isnot(None))
                .group_by(UsageEvent.video_id)
            )
            cost_rows = session.execute(cost_stmt).all()
            cost_by_video = {row.video_id: float(row.cost) for row in cost_rows}

            # Get latest analytics per video
            subquery = (
                select(
                    VideoAnalytics.video_id,
                    func.max(VideoAnalytics.fetched_at).label("latest"),
                )
                .group_by(VideoAnalytics.video_id)
                .subquery()
            )

            analytics_stmt = (
                select(VideoAnalytics)
                .join(
                    subquery,
                    (VideoAnalytics.video_id == subquery.c.video_id)
                    & (VideoAnalytics.fetched_at == subquery.c.latest),
                )
            )
            analytics_rows = list(session.scalars(analytics_stmt).all())
            analytics_by_video = {a.video_id: a for a in analytics_rows}

            # Compute per-video efficiency
            video_efficiency = []
            total_cost = 0.0
            total_views = 0
            total_subscribers = 0

            for video_id, cost in cost_by_video.items():
                video = session.get(Video, video_id)
                analytics = analytics_by_video.get(video_id)

                views = analytics.views if analytics else 0
                subs = analytics.subscriber_gain if analytics else 0

                cost_per_view = round(cost / views, 4) if views > 0 else None
                cost_per_sub = round(cost / subs, 2) if subs > 0 else None

                video_efficiency.append({
                    "video_id": video_id,
                    "title": video.title if video else "Unknown",
                    "cost_usd": round(cost, 4),
                    "views": views,
                    "subscriber_gain": subs,
                    "cost_per_view": cost_per_view,
                    "cost_per_subscriber": cost_per_sub,
                })

                total_cost += cost
                total_views += views
                total_subscribers += subs

            # Sort by cost_per_view (best first, None at end)
            video_efficiency.sort(
                key=lambda x: x["cost_per_view"] if x["cost_per_view"] is not None else float("inf")
            )

            overall_cpv = round(total_cost / total_views, 4) if total_views > 0 else None
            overall_cps = round(total_cost / total_subscribers, 2) if total_subscribers > 0 else None

            return {
                "total_cost_usd": round(total_cost, 4),
                "total_views": total_views,
                "total_subscriber_gain": total_subscribers,
                "overall_cost_per_view": overall_cpv,
                "overall_cost_per_subscriber": overall_cps,
                "video_count": len(video_efficiency),
                "videos": video_efficiency,
                "most_efficient": video_efficiency[:5] if video_efficiency else [],
                "least_efficient": video_efficiency[-5:][::-1] if video_efficiency else [],
            }
        finally:
            session.close()

    # ---------- Content Reports ----------

    def content_report(self, channel_id: str | None = None) -> dict[str, Any]:
        """Analyze content performance patterns.

        Identifies best-performing topics, optimal posting times, and
        content category trends.

        Args:
            channel_id: Optional filter to a specific channel.

        Returns:
            Dict with topic performance, posting time analysis, and trends.
        """
        session = get_session()
        try:
            # Get all uploaded videos with their analytics
            video_stmt = (
                select(Video)
                .where(Video.status == VideoStatus.UPLOADED)
            )
            if channel_id:
                video_stmt = video_stmt.where(Video.channel_id == channel_id)

            videos = list(session.scalars(video_stmt).all())

            # Get latest analytics per video
            subquery = (
                select(
                    VideoAnalytics.video_id,
                    func.max(VideoAnalytics.fetched_at).label("latest"),
                )
                .group_by(VideoAnalytics.video_id)
                .subquery()
            )

            analytics_stmt = (
                select(VideoAnalytics)
                .join(
                    subquery,
                    (VideoAnalytics.video_id == subquery.c.video_id)
                    & (VideoAnalytics.fetched_at == subquery.c.latest),
                )
            )
            analytics_rows = list(session.scalars(analytics_stmt).all())
            analytics_by_video = {a.video_id: a for a in analytics_rows}

            # Analyze posting hours
            hour_performance: dict[int, dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "total_views": 0, "total_likes": 0}
            )

            # Analyze by day of week
            day_performance: dict[int, dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "total_views": 0, "total_likes": 0}
            )

            video_data = []
            for video in videos:
                analytics = analytics_by_video.get(video.id)
                views = analytics.views if analytics else 0
                likes = analytics.likes if analytics else 0

                if video.created_at:
                    hour = video.created_at.hour
                    day = video.created_at.weekday()  # 0=Monday

                    hour_performance[hour]["count"] += 1
                    hour_performance[hour]["total_views"] += views
                    hour_performance[hour]["total_likes"] += likes

                    day_performance[day]["count"] += 1
                    day_performance[day]["total_views"] += views
                    day_performance[day]["total_likes"] += likes

                video_data.append({
                    "video_id": video.id,
                    "title": video.title,
                    "topic": video.topic_prompt[:100] if video.topic_prompt else "",
                    "views": views,
                    "likes": likes,
                    "created_at": video.created_at.isoformat() if video.created_at else None,
                })

            # Calculate average views per hour
            best_hours = []
            for hour, data in sorted(hour_performance.items()):
                avg_views = data["total_views"] / data["count"] if data["count"] else 0
                best_hours.append({
                    "hour": hour,
                    "videos_posted": data["count"],
                    "avg_views": round(avg_views),
                    "total_views": data["total_views"],
                })
            best_hours.sort(key=lambda x: x["avg_views"], reverse=True)

            # Calculate average views per day of week
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            best_days = []
            for day, data in sorted(day_performance.items()):
                avg_views = data["total_views"] / data["count"] if data["count"] else 0
                best_days.append({
                    "day": day_names[day],
                    "day_num": day,
                    "videos_posted": data["count"],
                    "avg_views": round(avg_views),
                    "total_views": data["total_views"],
                })
            best_days.sort(key=lambda x: x["avg_views"], reverse=True)

            # Sort videos by views for top content
            video_data.sort(key=lambda x: x["views"], reverse=True)

            return {
                "channel_id": channel_id,
                "total_videos": len(video_data),
                "best_posting_hours": best_hours[:5],
                "best_posting_days": best_days[:3],
                "all_hour_performance": best_hours,
                "all_day_performance": best_days,
                "top_performing_videos": video_data[:10],
                "recent_videos": sorted(
                    video_data,
                    key=lambda x: x["created_at"] or "",
                    reverse=True,
                )[:10],
            }
        finally:
            session.close()
