from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging() -> None:
    """
    Configure structlog with JSON output.

    Defaults to WARNING in production. Set LOG_LEVEL=INFO or LOG_LEVEL=DEBUG
    in the environment to increase verbosity during development.

    Emits only:
      ERROR   — hard failures (DB down, embedding API errors)
      WARNING — degraded operations (Qdrant fallback to graph, model retry)
      INFO    — startup/shutdown only (guarded by LOG_LEVEL=info)
    """
    level_name = os.environ.get("LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
