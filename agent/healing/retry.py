"""Retry with exponential backoff + full jitter."""
import asyncio
import logging
import random

from config import config

logger = logging.getLogger(__name__)


def _max_retries() -> int:
    return getattr(config, "healing_retry_max", 3)


def _base_ms() -> int:
    return getattr(config, "healing_backoff_base_ms", 200)


def backoff_delay(attempt: int) -> float:
    """Seconds to wait before attempt N (0-indexed). Full jitter."""
    base = _base_ms() / 1000.0
    ceiling = base * (2 ** attempt)
    return random.uniform(0, ceiling)


async def retry_async(coro_factory, max_retries: int = None, label: str = ""):
    """Call coro_factory() up to max_retries+1 times with backoff between failures."""
    max_retries = max_retries if max_retries is not None else _max_retries()
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            last_exc = e
            if attempt >= max_retries:
                break
            delay = backoff_delay(attempt)
            logger.debug(f"[healing/retry] {label} attempt {attempt+1} failed, backoff {delay:.2f}s: {e}")
            await asyncio.sleep(delay)
    raise last_exc
