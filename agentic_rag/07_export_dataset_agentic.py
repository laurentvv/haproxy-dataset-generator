"""
Script d'export du dataset Q&A.

Ce script exporte le dataset Q&A pour l'entraînement.
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_rag.config_agentic import EXPORT_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def export_dataset() -> None:
    """
    Exporte le dataset Q&A.
    """
    logger.info("Début de l'export du dataset")
    logger.info(f'Format: {EXPORT_CONFIG["output_format"]}')

    # TODO: Implémenter l'export
    # from agentic_rag.export.dataset_exporter import DatasetExporter
    # exporter = DatasetExporter()
    # exporter.export()

    logger.info('Export terminé')


def main() -> None:
    """
    Point d'entrée principal.
    """
    export_dataset()


if __name__ == '__main__':
    main()
