"""Logging configuration.

Development: readable single-line logs. Production: one JSON object per line.
Attach structured context with `logger.info("message", extra={"key": value})`. Log lines written
while a request is handled automatically include its `request_id`.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import request_id

# Attributes every LogRecord has; anything else on a record was passed via `extra=`.
_RESERVED_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {key: value for key, value in vars(record).items() if key not in _RESERVED_ATTRS}


class RequestIdFilter(logging.Filter):
    """Adds the id of the request being handled, so log lines can be traced to one request."""

    def filter(self, record: logging.LogRecord) -> bool:
        current = request_id.get()
        if current is not None and not hasattr(record, "request_id"):
            record.request_id = current
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_extra_fields(record),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    def formatMessage(self, record: logging.LogRecord) -> str:
        line = super().formatMessage(record)
        extras = " ".join(f"{key}={value}" for key, value in _extra_fields(record).items())
        return f"{line} {extras}" if extras else line


def configure_logging(level: str, *, json_output: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_output else TextFormatter())
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
