"""Async retry helper with exponential backoff and jitter."""
from __future__ import annotations

import asyncio
import logging
import random
from functools import wraps
from typing import Awaitable, Callable, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator that retries an async function with exponential backoff.

    Args:
        max_attempts: Total number of attempts before giving up.
        base_delay: Initial delay (seconds) between attempts.
        max_delay: Cap on the delay between attempts.
        backoff: Multiplier applied to the delay after each failure.
        jitter: When True, randomise the delay to avoid thundering herds.
        exceptions: Exception types that should trigger a retry.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = base_delay
            last_exc: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # retry semantics
                    last_exc = exc
                    if attempt >= max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        raise
                    sleep_for = min(delay, max_delay)
                    if jitter:
                        sleep_for *= 0.5 + random.random() / 2.0
                    logger.warning(
                        "%s failed (attempt %d/%d): %s -- retrying in %.2fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        sleep_for,
                    )
                    await asyncio.sleep(sleep_for)
                    delay *= backoff
            assert last_exc is not None  # pragma: no cover
            raise last_exc

        return wrapper

    return decorator
