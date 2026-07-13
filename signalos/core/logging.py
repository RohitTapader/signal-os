from __future__ import annotations

import json
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

LOG_DIR = Path("logs")

_logger = logging.getLogger("signalos")
_logger.setLevel(logging.INFO)

try:
    # Serverless platforms (Vercel, etc.) mount a read-only filesystem outside
    # /tmp, so a local logs/ directory isn't writable there. Structured logs
    # still reach the platform's log capture via the console handler below,
    # so this file handler is a local-dev convenience, not load-bearing.
    LOG_DIR.mkdir(exist_ok=True)
    _file_handler = TimedRotatingFileHandler(
        LOG_DIR / "signalos.log",
        when="W0",
        backupCount=8,
        encoding="utf-8",
    )
    _file_handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_file_handler)
except OSError:
    pass

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("%(message)s"))
_logger.addHandler(_console)


def log_json(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    _logger.info(json.dumps(payload, ensure_ascii=False, default=str))
