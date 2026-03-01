#!/usr/bin/env python3
"""Orchestrateur principal pour le système RAG agentic."""

import logging
import subprocess
import sys
from pathlib import Path

# Configurer l'encodage UTF-8 pour la sortie standard
if sys.platform == 'win32':
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def run_phase(phase_number: int, script_name: str) -> int:
    """Exécute une phase du pipeline.

    Args:
        phase_number: Numéro de la phase.
        script_name: Nom du script à exécuter.

    Returns:
        Code de retour (0 pour succès, 1 pour erreur).
    """
    print(f'\n{"=" * 60}')
    print(f'PHASE {phase_number}: {script_name}')
    print(f'{"=" * 60}\n')

    script_path = Path(__file__).parent / script_name

    try:
        # Execute as a script file, not as a module
        result = subprocess.run(
            ['uv', 'run', 'python', str(script_path)],
            cwd=Path(__file__).parent.parent,
            capture_output=False,
        )
    except FileNotFoundError:
        logger.error(f'Script non trouvé: {script_path}')
        return 1
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script: {e}")
        return 1

    if result.returncode != 0:
        print(f'\n❌ Phase {phase_number} échouée!')
        return 1

    print(f'\n✓ Phase {phase_number} terminée avec succès!')
    return 0


def main() -> int:
    """Point d'entrée principal.

    Returns:
        Code de retour (0 pour succès, 1 pour erreur).
    """
    print('=== Système RAG Agentic HAProxy 3.2 ===')
    print('Orchestrateur principal\n')

    phases = [
        (1, '01_scrape_verified.py', 'Scraping + Validation'),
        (2, '02_chunking_parent_child.py', 'Chunking Parent/Child'),
        (3, '03_indexing_chroma.py', 'Indexation ChromaDB'),
        (4, '04_agentic_chatbot.py', 'Chatbot (optionnel, ne pas exécuter automatiquement)'),
    ]

    for phase_num, script, description in phases:
        # Phase 4 (chatbot) est optionnelle - ne pas exécuter automatiquement
        if phase_num == 4:
            print(f'\n⏭️  Phase {phase_num} skipped (lancer manuellement: python {script})')
            continue

        print(f'\n>>> Démarrage: {description}')

        if run_phase(phase_num, script) != 0:
            print(f'\n❌ Arrêt du pipeline à la phase {phase_num}')
            return 1

        print('\n>>> Validation requise avant de continuer...')
        try:
            response = input('Continuer? (y/n): ').strip().lower()
            if response != 'y':
                print("\n⏸️ Pipeline interrompu par l'utilisateur")
                return 1
        except (EOFError, KeyboardInterrupt):
            print('\n\n⏸️ Pipeline interrompu')
            return 1

    print('\n' + '=' * 60)
    print('✓ Pipeline terminé avec succès!')
    print('=' * 60)
    print('\nProchaines étapes:')
    print('  1. Lancer le chatbot: uv run python 04_agentic_chatbot.py')
    print('  2. Exécuter les benchmarks: uv run python 05_bench_agentic.py')

    return 0


if __name__ == '__main__':
    sys.exit(main())
