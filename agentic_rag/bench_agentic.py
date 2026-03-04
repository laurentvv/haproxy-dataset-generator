"""
Script de benchmark comparatif pour le système RAG agentic.

Ce script compare les performances du système agentic avec le système standard.
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_rag.config_agentic import BENCHMARK_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def run_benchmark() -> None:
    """
    Exécute les benchmarks comparatifs.
    """
    logger.info('Début des benchmarks agentic')
    logger.info(f'Nombre de questions: {BENCHMARK_CONFIG["num_questions"]}')
    logger.info(f'Métriques: {BENCHMARK_CONFIG["metrics"]}')

    # TODO: Implémenter le benchmark
    # from agentic_rag.benchmarks.benchmark_runner import BenchmarkRunner
    # runner = BenchmarkRunner()
    # results = runner.run()

    logger.info('Benchmark terminé')


def main() -> None:
    """
    Point d'entrée principal.
    """
    run_benchmark()


if __name__ == '__main__':
    main()
