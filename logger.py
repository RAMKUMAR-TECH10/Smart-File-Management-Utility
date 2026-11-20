"""Central application logging setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIRECTORY = Path(__file__).resolve().parent / "logs"
_LOGGERS: dict[str, logging.Logger] = {}


def setup_logger(name: str = "smart_file_manager", log_directory: Path | str | None = None) -> logging.Logger:
    """Return a logger writing to logs/app.log and to the console."""
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    directory = Path(log_directory) if log_directory else LOG_DIRECTORY
    try:
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(directory / "app.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    _LOGGERS[name] = logger
    return logger


def get_logger(name: str = "smart_file_manager") -> logging.Logger:
    return _LOGGERS.get(name) or setup_logger(name)
