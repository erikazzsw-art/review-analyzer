"""Analytics middleware for FastAPI.

Records API call metrics (path, method, status, latency) per authenticated user.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend_api.app.services.analytics import track_event

logger = logging.getLogger(__name__)

SKIP_PATHS = {"/health", "/favicon.ico", "/docs", "/openapi.json", "/redoc"}


class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response: Response = await call_next(request)
        latency_ms = int((time.time() - start) * 1000)

        path = request.url.path
        if path in SKIP_PATHS or path.startswith("/_next"):
            return response

        user_id = getattr(request.state, "user_id", None)
        if user_id:
            try:
                track_event(user_id, "api_call", {
                    "path": path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                })
            except Exception as e:
                logger.debug("analytics middleware error: %s", e)

        return response
