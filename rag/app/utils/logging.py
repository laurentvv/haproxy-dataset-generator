"""Logging configuration for HAProxy Chatbot."""

import logging
import logging_config


def setup_logging(name: str, log_file: str | None = None) -> logging.Logger:
    """Configure le logging pour un module.

    Args:
        name: Nom du module
        log_file: Fichier de log optionnel

    Returns:
        Instance de logger configurée
    """
    return logging_config.setup_logging(name, log_file=log_file)
