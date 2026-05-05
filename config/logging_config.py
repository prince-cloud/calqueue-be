"""
Loguru configuration for the Django project.
Intercepts standard logging and routes it through loguru.
"""

import logging
import sys
from pathlib import Path

from loguru import logger


def setup_loguru():
    """Configure loguru for the application."""
    # Remove default handler
    logger.remove()

    # Add stderr handler with format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
    )

    # Add file handler for persistent logs
    log_path = Path(__file__).resolve().parent.parent / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


def configure_stdlib_logging():
    """Intercept standard library logging and route to loguru."""

    # Intercept handler for stdlib logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)
    for name in logging.root.manager.loggerDict:
        if name != "loguru":
            logging.getLogger(name).handlers = [InterceptHandler()]
            logging.getLogger(name).propagate = False
