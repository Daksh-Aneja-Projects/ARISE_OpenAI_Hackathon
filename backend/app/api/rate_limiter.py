"""
Per-user rate limiter middleware for the pipeline API.
Prevents a single user from spamming pipeline starts.

Default: 10 pipeline operations per minute per user (configurable via env).
Uses an in-memory sliding window counter — fast, zero dependencies.
For multi-process / multi-worker deployments, replace with Redis.
"""

import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class PipelineRateLimiter(BaseHTTPMiddleware):
    """
    Sliding window rate limiter for /api/pipeline/* endpoints.
    Limits per authenticated user (JWT sub), falls back to IP.
    """

    def __init__(self, app, max_calls: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_calls = max_calls
        self.window = window_seconds
        # {user_id: [timestamp, timestamp, ...]}
        self._calls: dict = defaultdict(list)

    def _get_identity(self, request: Request) -> str:
        """Extract user identity from JWT Bearer or fall back to IP."""
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            # Use the raw token as key (no decode needed — just rate-limit by token)
            return f"tok:{auth[7:40]}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only rate-limit pipeline endpoints
        if "/api/pipeline/" not in request.url.path:
            return await call_next(request)
        # Only rate-limit POST (start pipeline) — not status polls
        if request.method != "POST":
            return await call_next(request)

        identity = self._get_identity(request)
        now = time.time()
        window_start = now - self.window

        # Prune old timestamps
        self._calls[identity] = [t for t in self._calls[identity] if t > window_start]

        if len(self._calls[identity]) >= self.max_calls:
            oldest = min(self._calls[identity])
            retry_after = int(self.window - (now - oldest)) + 1
            return Response(
                content=f'{{"detail":"Rate limit exceeded. Try again in {retry_after}s."}}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_calls),
                    "X-RateLimit-Window": str(self.window),
                },
            )

        self._calls[identity].append(now)
        response = await call_next(request)
        # Add rate limit headers to all responses
        response.headers["X-RateLimit-Limit"] = str(self.max_calls)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_calls - len(self._calls[identity])
        )
        return response
