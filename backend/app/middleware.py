from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """A handful of response headers with no real downside that browsers use
    to reduce common attack surface — cheap insurance, not a substitute for
    the actual RBAC/CSRF/session work that carries the real security load."""

    def __init__(self, app, *, hsts: bool) -> None:
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if self._hsts:
            # Only sent over HTTPS (ENV=production, where Railway terminates
            # TLS) — sending this over plain HTTP in dev would be a no-op at
            # best and confusing at worst.
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
