"""
Centralized logging configuration with structured JSON output and request ID correlation.

Usage:
    from app.core.logging_config import configure_logging, request_id_var

    # Call once at app startup
    configure_logging(level="INFO")

    # Set request_id in middleware via contextvars
    token = request_id_var.set("some-uuid")
    # All loggers will now include request_id in their JSON output
"""

import logging
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

# Context variable for request ID propagation across async boundaries
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Logging filter that injects request_id from contextvars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("")
        return True


def configure_logging(level: str = "INFO") -> None:
    """
    Configure the root logger with JSON formatting and request ID injection.

    This replaces all existing handlers on the root logger with a single
    StreamHandler that outputs structured JSON including request_id.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicate output
    root_logger.handlers.clear()

    # Create JSON formatter with standard fields
    formatter = JsonFormatter(
        fmt="%(timestamp)s %(levelname)s %(name)s %(message)s",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
        timestamp=True,
    )

    # Create handler with JSON formatter and request ID filter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
