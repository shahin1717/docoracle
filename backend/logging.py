# backend/logging.py
import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """
    Configure structured logging for the entire app.
    Call once at startup in main.py.

    Format:
        2024-01-15 10:23:45 | INFO     | backend.api.documents | upload: saved file.pdf
    """
    level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)

    # avoid adding duplicate handlers on reload (uvicorn --reload)
    if not root.handlers:
        root.addHandler(handler)

    # quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)