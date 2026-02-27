"""
logging_config.py - Configuration centralisée du logging

Usage:
    from logging_config import setup_logging
    logger = setup_logging(__name__)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str,
    log_file: Optional[str] = None,
    log_level: Optional[str] = None,
) -> logging.Logger:
    """
    Configure logging with environment-based log level.

    Args:
        name: Logger name (typically __name__)
        log_file: Optional log file path (default: no file logging)
        log_level: Optional log level override (default: LOG_LEVEL env var or INFO)

    Returns:
        Configured logger instance
    """
    # Get log level from environment or parameter
    if log_level:
        level_name = log_level.upper()
    else:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()

    level = getattr(logging, level_name, logging.INFO)

    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Console handler with colored output (if supported)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Check if terminal supports colors
    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        # ANSI color codes
        COLORS = {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[35m",  # Magenta
            "RESET": "\033[0m",  # Reset
        }

        def colored_format(record: logging.LogRecord) -> str:
            color = COLORS.get(record.levelname, COLORS["RESET"])
            reset = COLORS["RESET"]
            return f"{color}{record.asctime} - {record.name} - {record.levelname}{reset} - {record.message}\n"

        console_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        console_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


# Default logger for the application
default_logger = setup_logging("haproxy_rag")
