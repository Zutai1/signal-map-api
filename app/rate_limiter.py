"""Simple in-memory rate limiter middleware.

Uses a sliding window counter per IP address.
Default: 30 requests per minute per IP.

For production, replace with Redis-backed rate limiting or nginx rate limits.
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self._requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/api/health":
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Also check X-API-Key for per-key limiting
        api_key = request.headers.get("X-API-Key", client_ip)
        key = f"{client_ip}:{api_key}"

        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        if len(self._requests[key]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._requests[key].append(now)
        return await call_next(request)
