"""Retry decorator with exponential backoff for API calls."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries.
        exceptions: Tuple of exception types to catch and retry on.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            "Failed after %d attempts: %s", max_attempts, str(e)
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "Attempt %d/%d failed (%s), retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        str(e),
                        delay,
                    )
                    time.sleep(delay)
            raise last_exception  # type: ignore

        return wrapper

    return decorator
