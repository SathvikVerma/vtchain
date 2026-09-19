"""Shared retry-with-backoff wrapper for Gemini calls.

Google's free tier is 5 requests/minute per model — with negotiation using
up to 4 calls plus the auditor using 1 more, a single pipeline run can sit
right at that ceiling, and two runs close together WILL trip a 429. This
wrapper retries transient 429 (RESOURCE_EXHAUSTED) errors with backoff
instead of letting one rate-limit blip kill the whole demo live in front of
judges. It respects the server's own suggested retry delay when the error
message includes one (Gemini's 429 errors do), otherwise falls back to
simple exponential backoff.
"""
from __future__ import annotations

import asyncio
import re

MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 5


def _extract_retry_delay(exc: Exception) -> float | None:
    """Gemini 429 errors embed a suggested delay like "retryDelay': '24s'"
    or "Please retry in 24.76s" — use it directly when present so we wait
    exactly as long as Google says to, not more, not less."""
    text = str(exc)
    match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", text)
    if not match:
        match = re.search(r"retry in\s+(\d+(?:\.\d+)?)s", text)
    if match:
        return float(match.group(1))
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


async def call_with_retry(fn, *args, **kwargs):
    """Call an async Gemini function, retrying transient 429s with backoff.

    `fn` is called as `await fn(*args, **kwargs)`. Non-rate-limit errors
    are raised immediately (no point retrying a bad prompt or auth error).
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — we re-raise below if not rate-limit
            if not _is_rate_limit_error(exc) or attempt == MAX_ATTEMPTS:
                raise
            last_exc = exc
            delay = _extract_retry_delay(exc) or (DEFAULT_BACKOFF_SECONDS * attempt)
            await asyncio.sleep(delay)
    # unreachable in practice, but keeps type-checkers happy
    if last_exc:
        raise last_exc
