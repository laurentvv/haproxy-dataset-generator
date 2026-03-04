"""
Script d'évaluation du chunking parent/child.

Ce script évalue la qualité du chunking hiérarchique.
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_rag.config_agentic import CHUNKING_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def evaluate_chunking() -> None:
    """
    Évalue la qualité du chunking parent/child.
    """
    logger.info("Début de l'évaluation du chunking")
    logger.info(f'Paramètres: {CHUNKING_CONFIG}')

    # TODO: Implémenter l'évaluation
    # from agentic_rag.evaluation.chunking_evaluator import ChunkingEvaluator
    # evaluator = ChunkingEvaluator()
    # results = evaluator.evaluate()

    logger.info('Évaluation terminée')


def main() -> None:
    """
    Point d'entrée principal.
    """
    evaluate_chunking()


if __name__ == '__main__':
    main()
