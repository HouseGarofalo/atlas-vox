"""Structured logging setup with structlog."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings

# Module-level reference to the LogStreamMonitor instance.
# Set by the self-healing engine at startup so the structlog processor
# can feed error events without a circular import.
_log_stream_monitor: Any = None


def set_log_stream_monitor(monitor: Any) -> None:
    """Register the LogStreamMonitor so structlog feeds errors into it."""
    global _log_stream_monitor
    _log_stream_monitor = monitor


def _healing_log_processor(
    logger_instance: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that feeds error-level events to LogStreamMonitor.

    This processor is added to the shared processor chain so that every
    error/critical/exception log event is captured by the self-healing
    system's LogStreamMonitor for anomaly detection.
    """
    if _log_stream_monitor is not None and method_name in (
        "error",
        "critical",
        "exception",
    ):
        _log_stream_monitor.ingest(
            level=method_name,
            event=event_dict.get("event", ""),
            logger_name=event_dict.get("logger", ""),
            error=event_dict.get("error", None),
        )
    return event_dict


def setup_logging() -> None:
    """Configure structlog with JSON or console output."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _healing_log_processor,
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Quiet noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
