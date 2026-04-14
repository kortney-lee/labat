"""
Verbose Request Logger Middleware
Logs every HTTP request and response with full detail.

Sends structured logs to:
  1. Python logger (Cloud Logging / stdout)
  2. Remote debug session (services.wihy.ai/api/debug-sessions) when available

Apply to any FastAPI app:
    from src.middleware.request_logger import VerboseRequestLoggerMiddleware
    app.add_middleware(VerboseRequestLoggerMiddleware)
"""

import json
import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Routes to log at DEBUG level (noisy health-check traffic)
_QUIET_ROUTES = frozenset(("/", "/health", "/api/status", "/favicon.ico", "/robots.txt"))

# Sensitive headers to redact
_REDACTED_HEADERS = frozenset((
    "authorization", "x-client-secret", "cookie", "set-cookie",
))

# Max body bytes to capture in the log (prevents OOM on large uploads)
_MAX_BODY_LOG = 2048


def _safe_headers(request: Request) -> dict:
    """Extract headers, redacting sensitive values."""
    out = {}
    for k, v in request.headers.items():
        k_lower = k.lower()
        if k_lower in _REDACTED_HEADERS:
            out[k] = "***"
        else:
            out[k] = v
    return out


def _source_site(request: Request) -> str:
    """Infer source site from headers."""
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    for url in (origin, referer):
        if "communitygroceries" in url.lower():
            return "communitygroceries.com"
        if "wihy" in url.lower():
            return "wihy.ai"
    ua = request.headers.get("user-agent", "").lower()
    if "wihy-ios" in ua or "wihy/ios" in ua:
        return "wihy-mobile-ios"
    if "wihy-android" in ua or "wihy/android" in ua:
        return "wihy-mobile-android"
    return "api"


class VerboseRequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every request/response pair with:
      - method, path, query params
      - source site, client IP
      - request body summary (truncated)
      - response status, latency
      - headers (sensitive values redacted)

    Also pushes structured log entries to the remote debug logger
    (services.wihy.ai) if available, so they appear alongside
    RequestTracer steps in the debug dashboard.
    """

    def __init__(self, app, service_name: str = "wihy-ml"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        request_id = str(uuid.uuid4())[:12]
        method = request.method
        path = request.url.path
        query_string = str(request.url.query) if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"
        source = _source_site(request)

        # ── Capture request body (only for POST/PUT/PATCH) ──
        body_summary: Optional[str] = None
        body_data: Optional[dict] = None
        if method in ("POST", "PUT", "PATCH"):
            try:
                raw = await request.body()
                if raw:
                    text = raw[:_MAX_BODY_LOG].decode("utf-8", errors="replace")
                    body_summary = text[:500]  # short version for log line
                    try:
                        body_data = json.loads(raw[:_MAX_BODY_LOG])
                        # Redact sensitive fields
                        for key in ("password", "token", "secret", "x-client-secret"):
                            if key in body_data:
                                body_data[key] = "***"
                        # Truncate large content fields
                        for key in ("message", "query", "content"):
                            if key in body_data and isinstance(body_data[key], str) and len(body_data[key]) > 300:
                                body_data[key] = body_data[key][:300] + "…"
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body_data = {"_raw_preview": text[:200]}
            except Exception:
                body_summary = "<unreadable>"

        # ── Call the actual route ──
        status_code = 500
        error_detail: Optional[str] = None
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            error_detail = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            latency_ms = int((time.time() - start) * 1000)

            # Build structured log payload
            log_payload = {
                "request_id": request_id,
                "service": self.service_name,
                "method": method,
                "path": path,
                "query_string": query_string,
                "status": status_code,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
                "source_site": source,
                "user_agent": request.headers.get("user-agent", "")[:200],
                "has_auth": bool(request.headers.get("authorization")),
                "has_client_id": bool(request.headers.get("x-client-id")),
            }

            if body_data:
                log_payload["body"] = body_data
            if error_detail:
                log_payload["error"] = error_detail

            # ── Log level selection ──
            is_quiet = path in _QUIET_ROUTES
            is_error = status_code >= 500
            is_warn = status_code >= 400

            if is_error:
                log_line = f"[ERR] {method} {path} -> {status_code} ({latency_ms}ms) src={source} ip={client_ip}"
                if error_detail:
                    log_line += f" err={error_detail[:120]}"
                logger.error(log_line)
            elif is_warn:
                logger.warning(
                    f"[WARN] {method} {path} -> {status_code} ({latency_ms}ms) src={source}"
                )
            elif is_quiet:
                logger.debug(
                    f"[QUIET] {method} {path} -> {status_code} ({latency_ms}ms)"
                )
            else:
                body_hint = ""
                if body_data:
                    if "message" in body_data:
                        body_hint = f" msg=\"{str(body_data['message'])[:80]}\""
                    elif "query" in body_data:
                        body_hint = f" q=\"{str(body_data['query'])[:80]}\""
                    elif "task" in body_data:
                        body_hint = f" task={body_data['task']}"
                logger.info(
                    f"[HTTP] {method} {path} -> {status_code} ({latency_ms}ms) src={source}{body_hint}"
                )

            # ── Verbose detail for non-quiet routes ──
            if not is_quiet:
                headers = _safe_headers(request)
                log_payload["headers"] = headers
                logger.info(
                    f"[HDR] {request_id} headers={json.dumps(headers, default=str)}"
                )
                if body_summary and method in ("POST", "PUT", "PATCH"):
                    logger.info(
                        f"[BODY] {request_id} body={body_summary[:300]}"
                    )

            # ── Push to remote debug logger (fire-and-forget) ──
            try:
                try:
    from src.services.debug_logger import _debug_logger
except ImportError:
    _debug_logger = None
                if _debug_logger and _debug_logger._session_created:
                    log_type = "error" if is_error else ("warn" if is_warn else "info")
                    _debug_logger.log(
                        log_type=log_type,
                        message=f"{method} {path} → {status_code} ({latency_ms}ms)",
                        page=path,
                        data=log_payload,
                    )
            except Exception:
                pass  # never let debug logging break the response

        return response
