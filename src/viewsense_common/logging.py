from __future__ import annotations

import contextvars
import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "viewsense_request_id", default=None
)


class JsonFormatter(logging.Formatter):
    """Stable JSON-line formatter intended for stdout log collectors and SIEM pipelines."""

    fields = (
        "event",
        "request_id",
        "traceparent",
        "tenant_id",
        "http_method",
        "http_path",
        "http_status",
        "duration_ms",
        "principal",
        "audience",
        "outcome",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": os.getenv("VS_SERVICE_NAME", os.getenv("VS_APP_MODULE", "viewsense")),
            "environment": os.getenv("VS_ENVIRONMENT", "development"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self.fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "viewsense_common.logging.JsonFormatter"}},
    "handlers": {"stdout": {"class": "logging.StreamHandler", "formatter": "json", "stream": "ext://sys.stdout"}},
    "root": {"handlers": ["stdout"], "level": os.getenv("VS_LOG_LEVEL", "INFO")},
    "loggers": {
        "uvicorn": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
    },
}


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", "").strip()[:128] or str(uuid.uuid4())
        traceparent = request.headers.get("traceparent", "").strip()[:256] or None
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500
        outcome = "error"
        try:
            response = await call_next(request)
            status_code = response.status_code
            if status_code < 400:
                outcome = "success"
            elif status_code in (401, 403):
                outcome = "denied"
            else:
                outcome = "error"
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            logging.getLogger("viewsense.http").info(
                "request_completed",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "traceparent": traceparent,
                    "tenant_id": getattr(request.state, "tenant_id", None),
                    "principal": getattr(request.state, "principal", None),
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                    "outcome": outcome,
                },
            )
            request_id_context.reset(token)
