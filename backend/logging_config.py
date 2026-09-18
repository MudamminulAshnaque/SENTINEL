"""
Minimal structured logging: every log line is a single JSON object to
stdout. No external deps (no python-json-logger) — for a hackathon-to-
production timeline, stdlib logging + json.dumps is fast to set up and
trivial for any log aggregator (Datadog, CloudWatch, etc.) to parse later.
"""

from __future__ import annotations

import json
import logging
import sys
import time


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Any extra fields passed via logger.info(msg, extra={...}) get merged in.
        for key, value in record.__dict__.items():
            if key not in payload and key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelno", "lineno", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName", "taskName",
            ):
                payload[key] = value
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:  # avoid duplicate handlers on reimport (e.g. reload in dev)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def now_ms() -> float:
    return time.perf_counter() * 1000
