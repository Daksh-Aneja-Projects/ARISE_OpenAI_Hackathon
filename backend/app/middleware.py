"""
Audit Middleware — intercepts all API mutations and logs them to the persistent audit trail.
Decodes JWT to extract real user identity for each logged event.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Only log API modifications (POST, PUT, PATCH, DELETE)
        if request.url.path.startswith("/api/"):
            try:
                from app.telemetry import telemetry

                telemetry.record_request()
                if response.status_code >= 500:
                    telemetry.record_error(
                        "api",
                        f"{request.method} {request.url.path} returned {response.status_code}",
                    )
            except Exception:
                pass

        if request.url.path.startswith("/api/") and request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            try:
                from app.api.audit import log_event

                # Extract real user info from JWT
                user_name = "System"
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        import jwt
                        from app.config import settings

                        token = auth_header.split(" ")[1]
                        payload = jwt.decode(
                            token, settings.JWT_SECRET, algorithms=["HS256"]
                        )
                        user_name = payload.get(
                            "name", payload.get("email", "Authenticated User")
                        )
                    except Exception:
                        user_name = "Authenticated User"

                # Extract bid_id from path if present
                bid_id = None
                parts = request.url.path.split("/")
                if "bids" in parts:
                    idx = parts.index("bids")
                    if idx + 1 < len(parts) and len(parts[idx + 1]) > 10:
                        bid_id = parts[idx + 1]

                log_event(
                    event_type="api_mutation",
                    event_detail=f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)",
                    bid_id=bid_id,
                    user_name=user_name,
                )
            except Exception as e:
                print(f"[AuditMiddleware] Failed to log event: {e}")

        return response
