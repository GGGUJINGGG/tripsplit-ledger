import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.config import settings


# Fixed-window request counts per (scope, client IP). In-memory and
# process-local — sufficient for this app's single deployed instance,
# not for a multi-instance/load-balanced setup.
_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def reset_rate_limits() -> None:
    """Test-only helper to clear all rate-limit state between tests."""
    with _lock:
        _attempts.clear()


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    max_attempts: int,
    window_seconds: int,
) -> None:
    if not settings.rate_limit_enabled:
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"{scope}:{client_ip}"
    now = time.monotonic()

    with _lock:
        attempts = _attempts[key]
        while attempts and now - attempts[0] > window_seconds:
            attempts.popleft()

        if len(attempts) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
            )

        attempts.append(now)
