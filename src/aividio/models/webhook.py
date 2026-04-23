"""Webhook model - stores registered webhook endpoints."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from aividio.models.base import Base, TimestampMixin, UUIDMixin


class Webhook(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "webhooks"

    url: Mapped[str] = mapped_column(String(2048), doc="Endpoint URL to receive events")
    events: Mapped[list] = mapped_column(
        JSON, default=list, doc="List of event types this webhook subscribes to"
    )
    secret: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="HMAC signing secret (stored encrypted)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(500), default="")

    def __repr__(self) -> str:
        return f"<Webhook {self.url} ({self.id[:8]})>"
