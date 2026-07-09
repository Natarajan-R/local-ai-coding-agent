"""Logging setup: Rich console output plus a structured file log.

The file log can be plain text or JSON lines (``json_logs=True``) for ingestion
by log aggregators. Every record carries a ``run_id`` field (``-`` when outside
a task run) so logs can be correlated with the audit trail.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from rich.logging import RichHandler


class _DefaultFieldsFilter(logging.Filter):
    """Ensure every record has a ``run_id`` so formatters never KeyError."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "run_id": getattr(record, "run_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    json_logs: bool = False,
) -> logging.Logger:
    level = getattr(logging, log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Reset handlers so repeated setup (tests, multiple runs) doesn't duplicate.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    default_filter = _DefaultFieldsFilter()

    console_handler = RichHandler(rich_tracebacks=True, show_time=True, show_path=False)
    console_handler.setLevel(level)
    console_handler.addFilter(default_filter)
    root.addHandler(console_handler)

    if log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
        if json_logs:
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | run=%(run_id)s | %(name)s | %(message)s"
                )
            )
        file_handler.addFilter(default_filter)
        file_handler.setLevel(logging.DEBUG)
        root.addHandler(file_handler)

    # Third-party libraries are noisy at INFO; quiet them down.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logging.getLogger("agent")
