"""
Production-grade logging configuration with JSON formatting and structured output.
"""

from __future__ import annotations

import json
import logging
import logging.config
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request tracking if available
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "actor_id"):
            log_entry["actor_id"] = record.actor_id

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra context
        if record.__dict__.get("extra"):
            log_entry.update(record.__dict__["extra"])

        return json.dumps(log_entry)


def setup_logging() -> None:
    """Configure logging for production deployment."""
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Format timestamp for daily log rotation
    log_file = log_dir / f"gateway-{datetime.now().strftime('%Y-%m-%d')}.log"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "standard": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_file),
                "maxBytes": 104857600,  # 100MB
                "backupCount": 10,
                "formatter": "json",
                "level": "DEBUG",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_dir / "gateway-error.log"),
                "maxBytes": 104857600,
                "backupCount": 5,
                "formatter": "json",
                "level": "ERROR",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": "DEBUG",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["file"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.LoggerAdapter:
    """Get a logger with request tracking capability."""
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {"request_id": "N/A"})


class RequestContextLogger:
    """Context manager for request-scoped logging."""

    def __init__(self, request_id: str, actor_id: str | None = None):
        self.request_id = request_id
        self.actor_id = actor_id
        self._logger = logging.getLogger("app")

    def __enter__(self):
        self._original_filters = self._logger.filters.copy()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def info(self, msg: str, extra: dict[str, Any] | None = None) -> None:
        """Log info message with context."""
        log_extra = {"request_id": self.request_id}
        if self.actor_id:
            log_extra["actor_id"] = self.actor_id
        if extra:
            log_extra.update(extra)
        self._logger.info(msg, extra=log_extra)

    def error(self, msg: str, extra: dict[str, Any] | None = None, exc_info: bool = False) -> None:
        """Log error message with context."""
        log_extra = {"request_id": self.request_id}
        if self.actor_id:
            log_extra["actor_id"] = self.actor_id
        if extra:
            log_extra.update(extra)
        self._logger.error(msg, extra=log_extra, exc_info=exc_info)

    def warning(self, msg: str, extra: dict[str, Any] | None = None) -> None:
        """Log warning message with context."""
        log_extra = {"request_id": self.request_id}
        if self.actor_id:
            log_extra["actor_id"] = self.actor_id
        if extra:
            log_extra.update(extra)
        self._logger.warning(msg, extra=log_extra)

    def debug(self, msg: str, extra: dict[str, Any] | None = None) -> None:
        """Log debug message with context."""
        log_extra = {"request_id": self.request_id}
        if self.actor_id:
            log_extra["actor_id"] = self.actor_id
        if extra:
            log_extra.update(extra)
        self._logger.debug(msg, extra=log_extra)
