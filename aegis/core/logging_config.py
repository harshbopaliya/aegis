"""
Structured logging configuration for production.

Supports JSON-formatted output for log aggregation systems
and structured context logging via RequestContextLogger.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from aegis.config import settings

_SETUP_DONE = False


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields
        for key in (
            "request_id",
            "actor_id",
            "method",
            "path",
            "status",
            "duration_ms",
            "client_host",
            "environment",
            "error",
        ):
            val = getattr(record, key, None)
            if val is not None:
                log_data[key] = val

        if record.exc_info and record.exc_info[1]:
            log_data["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_data, default=str)


class StandardFormatter(logging.Formatter):
    """Standard readable formatter."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging() -> None:
    """Configure application-wide logging."""
    global _SETUP_DONE
    if _SETUP_DONE:
        return
    _SETUP_DONE = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        console.setFormatter(StructuredFormatter())
    else:
        console.setFormatter(StandardFormatter())
    root.addHandler(console)

    # File handler (if log_dir is set)
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "aegis.log",
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(StructuredFormatter())
    root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(name)


class RequestContextLogger:
    """Context manager that adds request_id and actor_id to log records."""

    def __init__(self, request_id: str, actor_id: str | None = None):
        self.request_id = request_id
        self.actor_id = actor_id
        self.logger = logging.getLogger("aegis.request")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def _extra(self, extra: dict | None = None) -> dict:
        base = {"request_id": self.request_id}
        if self.actor_id:
            base["actor_id"] = self.actor_id
        if extra:
            base.update(extra)
        return base

    def info(self, msg: str, extra: dict | None = None):
        self.logger.info(msg, extra=self._extra(extra))

    def warning(self, msg: str, extra: dict | None = None):
        self.logger.warning(msg, extra=self._extra(extra))

    def error(self, msg: str, extra: dict | None = None, exc_info=False):
        self.logger.error(msg, extra=self._extra(extra), exc_info=exc_info)

    def debug(self, msg: str, extra: dict | None = None):
        self.logger.debug(msg, extra=self._extra(extra))
