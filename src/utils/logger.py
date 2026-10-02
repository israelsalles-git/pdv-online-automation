"""Logging do framework: tudo sai em logs/test_execution.log (e propaga para o pytest)."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from config.settings import PROJECT_ROOT

LOG_FILE = PROJECT_ROOT / "logs" / "test_execution.log"
_ROOT_NAME = "pdv"
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configure() -> logging.Logger:
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:
        return root
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").strip().upper())
    # Bibliotecas HTTP/Selenium são verbosas demais em DEBUG.
    for noisy in ("urllib3", "selenium", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return root


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
