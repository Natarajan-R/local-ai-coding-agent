"""Reference: FastAPI/Starlette middleware — in-memory rate limiting + structured logging.

Pattern to mimic: subclass BaseHTTPMiddleware and implement `dispatch`. The rate
limiter keeps a sliding window of request timestamps per client and returns HTTP 429
when exceeded (use Redis for production/multi-process). The logger records method,
path, status and duration. Adapt names/limits to your spec.
"""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits[client]
        while hits and hits[0] <= now - self.window:      # drop timestamps outside the window
            hits.popleft()
        if len(hits) >= self.max_requests:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        hits.append(now)
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger=None) -> None:
        super().__init__(app)
        import logging
        self.logger = logger or logging.getLogger("api")

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        self.logger.info("%s %s -> %s (%.1fms)",
                         request.method, request.url.path, response.status_code, elapsed_ms)
        return response
