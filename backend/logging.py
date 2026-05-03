"""
backend/logging.py

Structured logging setup for DocOracle.

Call setup_logging() once at app startup (done in main.py).
Every module then just does:

    import logging
    logger = logging.getLogger(__name__)
    logger.info("something happened")

Log levels:
    DEBUG   — verbose, dev only
    INFO    — normal operation (ingestion steps, requests)
    WARNING — non-fatal issues (KG failed, model slow)
    ERROR   — something broke but app is still running
    CRITICAL — app cannot continue
"""

import logging
import logging.config
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Log file location — docoracle/logs/docoracle.log
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "docoracle.log"


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
CONSOLE_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FILE_FMT    = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
DATE_FMT    = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Config dict — two handlers: console + rotating file
# ---------------------------------------------------------------------------
LOGGING_CONFIG = {
    "version":                  1,
    "disable_existing_loggers": False,

    "formatters": {
        "console": {
            "format":  CONSOLE_FMT,
            "datefmt": DATE_FMT,
        },
        "file": {
            "format":  FILE_FMT,
            "datefmt": DATE_FMT,
        },
    },

    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "stream":    "ext://sys.stdout",
            "formatter": "console",
            "level":     "INFO",
        },
        "file": {
            "class":       "logging.handlers.RotatingFileHandler",
            "filename":    str(LOG_FILE),
            "maxBytes":    10 * 1024 * 1024,   # 10 MB per file
            "backupCount": 3,                   # keep last 3 rotated files
            "formatter":   "file",
            "level":       "DEBUG",
            "encoding":    "utf-8",
        },
    },

    # root logger — catches everything not handled by a named logger
    "root": {
        "handlers": ["console", "file"],
        "level":    "DEBUG",
    },

    # quieten noisy third-party libraries
    "loggers": {
        "uvicorn":              {"level": "INFO",    "propagate": True},
        "uvicorn.error":        {"level": "INFO",    "propagate": True},
        "uvicorn.access":       {"level": "WARNING", "propagate": True},  # mute per-request noise
        "sqlalchemy.engine":    {"level": "WARNING", "propagate": True},  # set INFO to see SQL
        "httpx":                {"level": "WARNING", "propagate": True},
        "multipart":            {"level": "WARNING", "propagate": True},
    },
}


def setup_logging(debug: bool = False) -> None:
    """
    Apply logging config. Call once at startup.

    Parameters
    ----------
    debug : if True, sets console handler to DEBUG level too.
    """
    if debug:
        LOGGING_CONFIG["handlers"]["console"]["level"] = "DEBUG"

    logging.config.dictConfig(LOGGING_CONFIG)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialised — file: {LOG_FILE} | debug={debug}")