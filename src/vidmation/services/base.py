"""Base service class with common logging and settings access."""

from __future__ import annotations

import logging
from abc import ABC

from vidmation.config.settings import Settings, get_settings


class BaseService(ABC):
    """Abstract base for every external-API service.

    Provides:
    * A per-class logger (``self.logger``).
    * Access to the global ``Settings`` singleton (``self.settings``).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(
            f"vidmation.services.{self.__class__.__name__}"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
