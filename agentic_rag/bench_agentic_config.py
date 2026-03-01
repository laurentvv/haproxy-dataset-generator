#!/usr/bin/env python3
"""
Benchmark de correction de configuration HAProxy avec le système RAG agentic.

Ce script compare les performances du système RAG agentic pour :
- Détecter les erreurs de configuration
- Corriger les erreurs syntaxiques et logiques
- Proposer des améliorations de sécurité
- Minimiser les hallucinations

Le système agentic utilise l'outil validate_haproxy_config pour la validation.
"""

import argparse

# Imports des modules de benchmark depuis le répertoire racine
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports du système agentic
from agentic_rag.app.rag_system import AgenticRAGSystem
from agentic_rag.config_agentic import LLM_CONFIG

# Charger les modules depuis le répertoire parent
import importlib.util

# Charger bench_config_dataset.py depuis le répertoire parent
bench_config_dataset_path = Path(__file__).parent.parent / 'bench_config_dataset.py'
spec = importlib.util.spec_from_file_location('bench_config_dataset', bench_config_dataset_path)
bench_config_dataset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_config_dataset)
get_all_tests = bench_config_dataset.get_all_tests
get_quick_tests = bench_config_dataset.get_quick_tests
get_tests_by_difficulty = bench_config_dataset.get_tests_by_difficulty

# Charger haproxy_validator.py depuis le répertoire parent
haproxy_validator_path = Path(__file__).parent.parent / 'haproxy_validator.py'
spec = importlib.util.spec_from_file_location('haproxy_validator', haproxy_validator_path)
haproxy_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(haproxy_validator)
HAProxyValidator = haproxy_validator.HAProxyValidator
ValidationError = haproxy_validator.ValidationError
ErrorType = haproxy_validator.ErrorType
ErrorSeverity = haproxy_validator.ErrorSeverity


# =============================================================================
# Classes de résultats
# =============================================================================


class BenchmarkResult:
    """Résultat d'un test de benchmark."""

    def __init__(
        self,
        test_id: str,
        test_name: str,
        category: str,
        difficulty: str,
        detection_rate: float,
        syntax_compliance: float,
        optimization_precision: float,
        hallucination_rate: float,
        global_score: float,
        response_time: float,
        retrieval_time: float | None,
        generation_time: float,
        detected_errors: list,
        expected_errors: list,
        fixed_config: str,
        expected_fixed_config: str,
        model: str,
        rag_used: bool,
        timestamp: str,
    ) -> None:
        self.test_id = test_id
        self.test_name = test_name
        self.category = category
        self.difficulty = difficulty
        self.detection_rate = detection_rate
        self.syntax_compliance = syntax_compliance
        self.optimization_precision = optimization_precision
        self.hallucination_rate = hallucination_rate
        self.global_score = global_score
        self.response_time = response_time
        self.retrieval_time = retrieval_time
        self.generation_time = generation_time
        self.detected_errors = detected_errors
        self.expected_errors = expected_errors
        self.fixed_config = fixed_config
        self.expected_fixed_config = expected_fixed_config
        self.model = model
        self.rag_used = rag_used
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convertit le résultat en dictionnaire."""
        return {
            'test_id': self.test_id,
            'test_name': self.test_name,
            'category': self.category,
            'difficulty': self.difficulty,
            'detection_rate': self.detection_rate,
            'syntax_compliance': self.syntax_compliance,
            'optimization_precision': self.optimization_precision,
            'hallucination_rate': self.hallucination_rate,
            'global_score': self.global_score,
            'response_time': self.response_time,
            'retrieval_time': self.retrieval_time,
            'generation_time': self.generation_time,
            'detected_errors': [
                {'line': e.line, 'error_type': e.error_type, 'message': e.message}
                for e in self.detected_errors
            ],
            'expected_errors': self.expected_errors,
            'fixed_config': self.fixed_config,
            'expected_fixed_config': self.expected_fixed_config,
            'model': self.model,
            'rag_used': self.rag_used,
            'timestamp': self.timestamp,
        }


class BenchmarkSummary:
    """Résumé des résultats de benchmark."""

    def __init__(self, results: list[BenchmarkResult]) -> None:
        self.results = results
        self.avg_global_score = (
            sum(r.global_score for r in results) / len(results) if results else 0
        )
        self.avg_detection_rate = (
            sum(r.detection_rate for r in results) / len(results) if results else 0
        )
        self.avg_syntax_compliance = (
            sum(r.syntax_compliance for r in results) / len(results) if results else 0
        )
        self.avg_hallucination_rate = (
            sum(r.hallucination_rate for r in results) / len(results) if results else 0
        )
        self.avg_response_time = (
            sum(r.response_time for r in results) / len(results) if results else 0
        )
        self.success_rate = (
            sum(1 for r in results if r.global_score > 0.7) / len(results) * 100 if results else 0
        )


# =============================================================================
# Fonctions de calcul de métriques
# =============================================================================


def calculate_detection_rate(detected_errors: list, expected_errors: list) -> float:
    """Calcule le taux de détection des erreurs."""
    if not expected_errors:
        return 1.0

    detected_types = {e.error_type for e in detected_errors}
    expected_types = {e.get('type') for e in expected_errors}

    if not expected_types:
        return 1.0

    detected_count = len(detected_types & expected_types)
    return detected_count / len(expected_types)


def calculate_syntax_compliance(config: str, validator: HAProxyValidator) -> float:
    """Calcule la conformité syntaxique de la configuration."""
    if not config:
        return 0.0

    try:
        validator.validate(config)
        return 1.0
    except ValidationError:
        return 0.0


def calculate_optimization_precision(
    original_config: str,
    fixed_config: str,
    expected_fixed_config: str,
    validator: HAProxyValidator,
) -> float:
    """Calcule la précision de l'optimisation."""
    if not fixed_config:
        return 0.0

    # Vérifier que la config corrigée est valide
    try:
        validator.validate(fixed_config)
    except ValidationError:
        return 0.0

    # Si pas de config attendue, vérifier juste que c'est valide
    if not expected_fixed_config:
        return 1.0

    # Comparaison simple (peut être améliorée)
    original_lines = set(original_config.strip().split('\n'))
    fixed_lines = set(fixed_config.strip().split('\n'))
    expected_lines = set(expected_fixed_config.strip().split('\n'))

    # Vérifier que les corrections attendues sont présentes
    added_lines = fixed_lines - original_lines
    expected_added = expected_lines - original_lines

    if not expected_added:
        return 1.0

    precision = len(added_lines & expected_added) / len(expected_added)
    return precision


def calculate_hallucination_rate(
    fixed_config: str, validator: HAProxyValidator, rag_used: bool = True
) -> float:
    """Calcule le taux d'hallucination."""
    if not fixed_config:
        return 0.0

    # Vérifier la validité de la configuration
    try:
        validator.validate(fixed_config)
    except ValidationError:
        # Si invalide, c'est probablement une hallucination
        return 1.0

    # Vérifier les directives inconnues
    lines = fixed_config.split('\n')
    unknown_directives = 0
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            parts = line.split()
            if parts:
                directive = parts[0]
                # Liste des directives HAProxy communes
                common_directives = {
                    'global',
                    'defaults',
                    'frontend',
                    'backend',
                    'listen',
                    'bind',
                    'server',
                    'option',
                    'timeout',
                    'log',
                    'mode',
                    'balance',
                    'http-check',
                    'acl',
                    'use_backend',
                    'default_backend',
                    'maxconn',
                    'cookie',
                    'http-request',
                    'http-response',
                    'stick-table',
                    'track-sc',
                }
                if directive not in common_directives:
                    unknown_directives += 1

    if not lines:
        return 0.0

    return unknown_directives / len(lines)


def calculate_global_score(
    detection_rate: float,
    syntax_compliance: float,
    optimization_precision: float,
    hallucination_rate: float,
) -> float:
    """Calcule le score global."""
    return (
        detection_rate * 0.3
        + syntax_compliance * 0.3
        + optimization_precision * 0.2
        + (1 - hallucination_rate) * 0.2
    )


def calculate_response_time(start_time: float, end_time: float) -> float:
    """Calcule le temps de réponse."""
    return end_time - start_time


def generate_summary_from_results(results: list[BenchmarkResult]) -> BenchmarkSummary:
    """Génère un résumé à partir des résultats."""
    return BenchmarkSummary(results)


# =============================================================================
# Classe principale : BenchmarkRunner
# =============================================================================


class BenchmarkRunner:
    """Orchestrateur du benchmark de correction de configuration HAProxy."""

    def __init__(
        self,
        model: str = LLM_CONFIG['model'],
        verbose: bool = False,
    ) -> None:
        """Initialise le runner de benchmark.

        Args:
            model: Modèle LLM à utiliser
            verbose: Mode verbeux
        """
        self.model = model
        self.verbose = verbose
        self.validator = HAProxyValidator()
        self.rag_system = AgenticRAGSystem()

    def run_agentic_rag(self, tests: list[dict[str, Any]]) -> list[BenchmarkResult]:
        """Exécute les tests avec le système RAG agentic.

        Args:
            tests: Liste des tests à exécuter

        Returns:
            Liste des résultats de benchmark
        """
        results: list[BenchmarkResult] = []

        print(f'\n{"=" * 60}')
        print(f'Exécution des tests avec RAG Agentic ({self.model})')
        print(f'{"=" * 60}\n')

        for i, test in enumerate(tests):
            print(f'Test {i + 1}/{len(tests)}: {test["name"]}')
            result = self.run_single_test_agentic(test)
            results.append(result)
            print(f'  Score: {result.global_score:.2f}/1.0\n')

        print(f'\n{"=" * 60}')
        print('Tests terminés')
        print(f'{"=" * 60}\n')

        return results

    def run_single_test_agentic(self, test: dict[str, Any]) -> BenchmarkResult:
        """Exécute un test avec le système RAG agentic.

        Args:
            test: Cas de test à exécuter

        Returns:
            Résultat de benchmark
        """
        start_time = time.time()

        # Construire la requête pour RAG
        query = f'Correction de configuration HAProxy: {test["name"]}'
        if test.get('metadata', {}).get('keywords'):
            query += ' ' + ' '.join(test['metadata']['keywords'])

        # Créer une nouvelle session
        session_id = self.rag_system.create_session()

        # Exécuter la requête
        retrieval_start = time.time()
        try:
            response_chunks = []
            for chunk in self.rag_system.query(session_id, query):
                response_chunks.append(chunk)
            response = ''.join(response_chunks)
        except Exception as e:
            if self.verbose:
                print(f'\nErreur lors de la génération: {e}')
            response = f'Erreur: {e}'
        retrieval_end = time.time()
        retrieval_time = retrieval_end - retrieval_start

        generation_time = retrieval_time  # Le système agentic fait tout en une étape

        end_time = time.time()

        # Extraire la configuration corrigée
        fixed_config = self.extract_config_from_response(response)

        # Si aucune config n'a été extraite, utiliser la réponse brute
        if not fixed_config:
            fixed_config = test['original_config']

        # Calculer les métriques
        detection_rate = calculate_detection_rate([], test.get('expected_errors', []))
        syntax_compliance = calculate_syntax_compliance(fixed_config, self.validator)
        optimization_precision = calculate_optimization_precision(
            test['original_config'],
            fixed_config,
            test.get('expected_fixed_config', ''),
            self.validator,
        )
        hallucination_rate = calculate_hallucination_rate(
            fixed_config, self.validator, rag_used=True
        )
        global_score = calculate_global_score(
            detection_rate,
            syntax_compliance,
            optimization_precision,
            hallucination_rate,
        )
        response_time = calculate_response_time(start_time, end_time)

        return BenchmarkResult(
            test_id=test['id'],
            test_name=test['name'],
            category=test['category'],
            difficulty=test['difficulty'],
            detection_rate=detection_rate,
            syntax_compliance=syntax_compliance,
            optimization_precision=optimization_precision,
            hallucination_rate=hallucination_rate,
            global_score=global_score,
            response_time=response_time,
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            detected_errors=[],
            expected_errors=test.get('expected_errors', []),
            fixed_config=fixed_config,
            expected_fixed_config=test.get('expected_fixed_config', ''),
            model=self.model,
            rag_used=True,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

    def extract_config_from_response(self, response: str) -> str:
        """Extrait la configuration de la réponse du LLM.

        Args:
            response: Réponse du LLM

        Returns:
            Configuration extraite ou chaîne vide
        """
        import re

        # Chercher les blocs de code markdown
        patterns = [
            r'```(?:haproxy|conf)?\n(.*?)```',  # Blocs avec haproxy/conf
            r'```\n(.*?)```',  # Blocs sans langage
            r'Configuration corrigée\s*:\s*\n(.*?)(?:\n\n|\n[A-Z])',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                return matches[0].strip()

        # Si aucun bloc de code, essayer d'extraire les lignes de configuration
        lines = []
        in_config = False
        for line in response.split('\n'):
            line = line.strip()
            if line in ('global', 'defaults', 'frontend', 'backend', 'listen'):
                in_config = True
            if in_config and line and not line.startswith('#'):
                lines.append(line)
            if in_config and line and line[0].isupper() and len(line.split()) > 3:
                break

        return '\n'.join(lines) if lines else ''


# =============================================================================
# Point d'entrée principal
# =============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse les arguments en ligne de commande.

    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description='Benchmark de correction de configuration HAProxy avec RAG agentic',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  # Exécuter tous les tests
  python 07_bench_agentic_config.py --tests all

  # Exécuter les tests rapides
  python 07_bench_agentic_config.py --tests quick

  # Exécuter avec un modèle spécifique
  python 07_bench_agentic_config.py --model qwen3:latest

  # Générer tous les formats de rapport
  python 07_bench_agentic_config.py --format all
        """,
    )

    parser.add_argument(
        '--model',
        type=str,
        default=LLM_CONFIG['model'],
        help=f'Modèle LLM à utiliser (défaut: {LLM_CONFIG["model"]})',
    )
    parser.add_argument(
        '--tests',
        type=str,
        choices=['all', 'quick', 'standard', 'full'],
        default='all',
        help='Tests à exécuter (défaut: all)',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='bench_agentic_config_report',
        help='Fichier de sortie sans extension (défaut: bench_agentic_config_report)',
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'markdown', 'html', 'all'],
        default='all',
        help='Format de rapport (défaut: all)',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mode verbeux',
    )

    return parser.parse_args()


def load_tests(tests_level: str) -> list[dict[str, Any]]:
    """Charge les tests selon le niveau demandé.

    Args:
        tests_level: Niveau de tests (all, quick, standard, full)

    Returns:
        Liste des tests à exécuter
    """
    if tests_level == 'quick':
        return get_quick_tests()
    elif tests_level == 'standard':
        tests = get_tests_by_difficulty('easy') + get_tests_by_difficulty('medium')
        return tests
    elif tests_level in ('all', 'full'):
        return get_all_tests()
    else:
        return get_all_tests()


def main() -> int:
    """Point d'entrée principal du benchmark.

    Returns:
        Code de sortie (0 = succès)
    """
    # Parser les arguments
    args = parse_arguments()

    # Afficher les informations de démarrage
    print('=' * 60)
    print('Benchmark de Correction de Configuration HAProxy (RAG Agentic)')
    print('=' * 60)
    print(f'Modèle LLM : {args.model}')
    print(f'Niveau de tests : {args.tests}')
    print(f'Format de rapport : {args.format}')
    print(f'Mode verbeux : {args.verbose}')
    print('=' * 60)

    # Charger les tests
    tests = load_tests(args.tests)
    print(f'\nNombre de tests à exécuter : {len(tests)}')

    # Initialiser le runner
    runner = BenchmarkRunner(model=args.model, verbose=args.verbose)

    # Exécuter les tests avec RAG agentic
    rag_results = runner.run_agentic_rag(tests)

    # Générer le résumé
    rag_summary = generate_summary_from_results(rag_results)

    # Créer le rapport de benchmark
    benchmark_report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model': args.model,
        'total_tests': len(tests),
        'agentic_rag': {
            'avg_global_score': rag_summary.avg_global_score,
            'avg_detection_rate': rag_summary.avg_detection_rate,
            'avg_syntax_compliance': rag_summary.avg_syntax_compliance,
            'avg_hallucination_rate': rag_summary.avg_hallucination_rate,
            'avg_response_time': rag_summary.avg_response_time,
            'success_rate': rag_summary.success_rate,
        },
        'detailed_results': [r.to_dict() for r in rag_results],
    }

    # Générer et sauvegarder les rapports
    formats_to_generate = []
    if args.format == 'all':
        formats_to_generate = ['json', 'markdown']
    else:
        formats_to_generate = [args.format]

    for fmt in formats_to_generate:
        try:
            if fmt == 'json':
                output_file = f'{args.output}.json'
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(benchmark_report, f, indent=2, ensure_ascii=False)
                print(f'✅ Rapport {fmt} sauvegardé : {output_file}')
            elif fmt == 'markdown':
                output_file = f'{args.output}.md'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('# Benchmark RAG Agentic - Correction de Configuration\n\n')
                    f.write('## Informations\n\n')
                    f.write(f'- Modèle: {args.model}\n')
                    f.write(f'- Tests: {len(tests)}\n')
                    f.write(f'- Date: {benchmark_report["timestamp"]}\n\n')
                    f.write('## Résultats\n\n')
                    f.write(f'- Score global: {rag_summary.avg_global_score:.2f}%\n')
                    f.write(f'- Taux de réussite: {rag_summary.success_rate:.2f}%\n')
                    f.write(f'- Temps moyen: {rag_summary.avg_response_time:.2f}s\n\n')
                    f.write('## Détails\n\n')
                    for r in rag_results:
                        f.write(f'### {r.test_name}\n\n')
                        f.write(f'- Score: {r.global_score:.2f}/1.0\n')
                        f.write(f'- Conformité syntaxique: {r.syntax_compliance:.2f}\n')
                        f.write(f"- Taux d'hallucination: {r.hallucination_rate:.2f}\n\n")
                print(f'✅ Rapport {fmt} sauvegardé : {output_file}')
        except Exception as e:
            print(f'❌ Erreur lors de la génération du rapport {fmt}: {e}')

    # Afficher le résumé
    print(f'\n{"=" * 60}')
    print('Résumé des Résultats')
    print(f'{"=" * 60}')
    print('\nRAG Agentic :')
    print(f'  Score global : {rag_summary.avg_global_score:.2f}%')
    print(f'  Taux de réussite : {rag_summary.success_rate:.2f}%')
    print(f'  Temps moyen : {rag_summary.avg_response_time:.2f}s')
    print(f'  Conformité syntaxique : {rag_summary.avg_syntax_compliance:.2f}')
    print(f"  Taux d'hallucination : {rag_summary.avg_hallucination_rate:.2f}")

    print(f'\n{"=" * 60}')
    print('Benchmark terminé avec succès !')
    print(f'{"=" * 60}\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
