#!/usr/bin/env python3
"""Benchmark de correction de configuration HAProxy.

Ce script compare les performances de deux architectures :
1. Ollama seul (LLM sans RAG)
2. Ollama + RAG (LLM avec retrieval hybride)

Le benchmark évalue la capacité du LLM à :
- Détecter les erreurs de configuration
- Corriger les erreurs syntaxiques et logiques
- Proposer des améliorations de sécurité
- Minimiser les hallucinations
"""

import argparse
import sys
import time
from datetime import datetime
from typing import Any

# Imports des modules de benchmark
from bench_config_dataset import (
    get_all_tests,
    get_quick_tests,
    get_tests_by_difficulty,
)
from haproxy_validator import (
    HAProxyValidator,
    ValidationError,
    ErrorType,
    ErrorSeverity,
)
from bench_config_metrics import (
    BenchmarkResult,
    BenchmarkReport,
    calculate_detection_rate,
    calculate_syntax_compliance,
    calculate_optimization_precision,
    calculate_hallucination_rate,
    calculate_global_score,
    calculate_response_time,
    generate_summary_from_results,
    generate_comparison_summary,
)
from bench_config_report import BenchmarkReportGenerator

# Imports des modules LLM et RAG
from llm import generate_response_sync
from retriever_v3 import retrieve_context_string
from config import ollama_config


# =============================================================================
# Prompts
# =============================================================================

OLLAMA_ONLY_PROMPT = """Tu es un expert en configuration HAProxy.

Analyse le fichier de configuration suivant et :
1. Identifie toutes les erreurs (syntaxiques, logiques, de sécurité)
2. Propose les corrections nécessaires
3. Explique chaque correction

Configuration :
{config}

Réponds avec :
- Liste des erreurs trouvées
- Configuration corrigée
- Explications des corrections
"""

RAG_PROMPT = """Tu es un expert en configuration HAProxy.

En utilisant UNIQUEMENT le contexte fourni ci-dessous :
1. Identifie toutes les erreurs dans la configuration
2. Propose les corrections nécessaires
3. Explique chaque correction avec des références à la documentation

<context>
{context}
</context>

Configuration à analyser :
{config}

RÈGLES ABSOLUES :
- Réponds UNIQUEMENT à partir du contexte fourni
- Cite TOUJOURS la source entre parenthèses
- JAMAIS d'invention ou de supposition
"""


# =============================================================================
# Fonctions utilitaires
# =============================================================================


def build_ollama_only_prompt(config: str) -> str:
    """Construit le prompt pour Ollama seul.

    Args:
        config: Configuration HAProxy à analyser

    Returns:
        Prompt complet pour le LLM
    """
    return OLLAMA_ONLY_PROMPT.format(config=config.strip())


def build_rag_prompt(config: str, context: str) -> str:
    """Construit le prompt pour Ollama + RAG.

    Args:
        config: Configuration HAProxy à analyser
        context: Contexte récupéré par RAG

    Returns:
        Prompt complet pour le LLM
    """
    return RAG_PROMPT.format(context=context, config=config.strip())


def print_progress(current: int, total: int, prefix: str = "Progress") -> None:
    """Affiche une barre de progression ASCII.

    Args:
        current: Élément actuel
        total: Nombre total d'éléments
        prefix: Préfixe de la barre
    """
    percent = int(100 * current / total) if total > 0 else 0
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    sys.stdout.write(f"\r{prefix}: [{bar}] {percent}% ({current}/{total})")
    sys.stdout.flush()


def extract_config_from_response(response: str) -> str:
    """Extrait la configuration de la réponse du LLM.

    Args:
        response: Réponse du LLM

    Returns:
        Configuration extraite ou chaîne vide
    """
    # Chercher les blocs de code markdown
    import re

    # Pattern pour les blocs de code avec ou sans spécification de langage
    patterns = [
        r"```(?:haproxy|conf)?\n(.*?)```",  # Blocs avec haproxy/conf
        r"```\n(.*?)```",  # Blocs sans langage
        r"Configuration corrigée\s*:\s*\n(.*?)(?:\n\n|\n[A-Z])",  # Texte après "Configuration corrigée"
    ]

    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            # Retourner le premier bloc de code trouvé
            return matches[0].strip()

    # Si aucun bloc de code, essayer d'extraire les lignes de configuration
    lines = []
    in_config = False
    for line in response.split("\n"):
        line = line.strip()
        # Détecter le début d'une configuration HAProxy
        if line in ("global", "defaults", "frontend", "backend", "listen"):
            in_config = True
        if in_config and line and not line.startswith("#"):
            lines.append(line)
        # Arrêter si on rencontre une section de texte
        if in_config and line and line[0].isupper() and len(line.split()) > 3:
            break

    return "\n".join(lines) if lines else ""


def parse_llm_response(
    response: str, expected_errors: list[dict]
) -> tuple[list[ValidationError], str]:
    """Parse la réponse du LLM pour extraire les erreurs et la config corrigée.

    Args:
        response: Réponse du LLM
        expected_errors: Erreurs attendues (pour référence)

    Returns:
        Tuple (erreurs détectées, configuration corrigée)
    """
    detected_errors: list[ValidationError] = []

    # Extraire la configuration corrigée
    fixed_config = extract_config_from_response(response)

    # Analyser la réponse pour détecter les erreurs mentionnées
    lines = response.split("\n")
    for line_num, line in enumerate(lines, start=1):
        line_lower = line.lower()

        # Détecter les mentions d'erreurs
        error_keywords = ["erreur", "error", "problème", "problème", "faute"]
        for keyword in error_keywords:
            if keyword in line_lower:
                # Essayer d'extraire le type d'erreur
                error_type = ErrorType.SYNTAX
                if "syntax" in line_lower:
                    error_type = ErrorType.SYNTAX
                elif "logique" in line_lower or "logic" in line_lower:
                    error_type = ErrorType.LOGIC
                elif "sécurité" in line_lower or "security" in line_lower:
                    error_type = ErrorType.SECURITY

                detected_errors.append(
                    ValidationError(
                        line=0,  # Ligne inconnue dans la réponse
                        column=0,
                        error_type=error_type,
                        severity=ErrorSeverity.ERROR,
                        message=line.strip(),
                    )
                )
                break

    return detected_errors, fixed_config


# =============================================================================
# Classe principale : BenchmarkRunner
# =============================================================================


class BenchmarkRunner:
    """Orchestrateur du benchmark de correction de configuration HAProxy."""

    def __init__(
        self,
        model: str = ollama_config.llm_model,
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

    def run_ollama_only(self, tests: list[dict[str, Any]]) -> list[BenchmarkResult]:
        """Exécute les tests avec Ollama seul.

        Args:
            tests: Liste des tests à exécuter

        Returns:
            Liste des résultats de benchmark
        """
        results: list[BenchmarkResult] = []

        print(f"\n{'=' * 60}")
        print(f"Exécution des tests avec Ollama seul ({self.model})")
        print(f"{'=' * 60}\n")

        for i, test in enumerate(tests):
            print_progress(i, len(tests), "Ollama seul")
            result = self.run_single_test_ollama(test)
            results.append(result)

        print_progress(len(tests), len(tests), "Ollama seul")
        print("\n")

        return results

    def run_ollama_rag(self, tests: list[dict[str, Any]]) -> list[BenchmarkResult]:
        """Exécute les tests avec Ollama + RAG.

        Args:
            tests: Liste des tests à exécuter

        Returns:
            Liste des résultats de benchmark
        """
        results: list[BenchmarkResult] = []

        print(f"\n{'=' * 60}")
        print(f"Exécution des tests avec Ollama + RAG ({self.model})")
        print(f"{'=' * 60}\n")

        for i, test in enumerate(tests):
            print_progress(i, len(tests), "Ollama + RAG")
            result = self.run_single_test_rag(test)
            results.append(result)

        print_progress(len(tests), len(tests), "Ollama + RAG")
        print("\n")

        return results

    def run_single_test_ollama(self, test: dict[str, Any]) -> BenchmarkResult:
        """Exécute un test avec Ollama seul.

        Args:
            test: Cas de test à exécuter

        Returns:
            Résultat de benchmark
        """
        start_time = time.time()

        # Construire le prompt
        prompt = build_ollama_only_prompt(test["original_config"])

        # Générer la réponse
        try:
            response = generate_response_sync(
                question=prompt,
                context="",  # Pas de contexte pour Ollama seul
                model=self.model,
            )
        except Exception as e:
            if self.verbose:
                print(f"\nErreur lors de la génération: {e}")
            response = f"Erreur: {e}"

        end_time = time.time()

        # Parser la réponse
        detected_errors, fixed_config = parse_llm_response(
            response, test.get("expected_errors", [])
        )

        # Si aucune config n'a été extraite, utiliser la réponse brute
        if not fixed_config:
            fixed_config = test["original_config"]

        # Calculer les métriques
        detection_rate = calculate_detection_rate(
            detected_errors, test.get("expected_errors", [])
        )
        syntax_compliance = calculate_syntax_compliance(fixed_config, self.validator)
        optimization_precision = calculate_optimization_precision(
            test["original_config"],
            fixed_config,
            test.get("expected_fixed_config", ""),
            self.validator,
        )
        hallucination_rate = calculate_hallucination_rate(
            fixed_config, self.validator, rag_used=False
        )
        global_score = calculate_global_score(
            detection_rate,
            syntax_compliance,
            optimization_precision,
            hallucination_rate,
        )
        response_time = calculate_response_time(start_time, end_time)

        return BenchmarkResult(
            test_id=test["id"],
            test_name=test["name"],
            category=test["category"],
            difficulty=test["difficulty"],
            detection_rate=detection_rate,
            syntax_compliance=syntax_compliance,
            optimization_precision=optimization_precision,
            hallucination_rate=hallucination_rate,
            global_score=global_score,
            response_time=response_time,
            retrieval_time=None,
            generation_time=response_time,
            input_tokens=0,  # Non disponible avec generate_response_sync
            output_tokens=0,
            detected_errors=detected_errors,
            expected_errors=test.get("expected_errors", []),
            fixed_config=fixed_config,
            expected_fixed_config=test.get("expected_fixed_config", ""),
            model=self.model,
            rag_used=False,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def run_single_test_rag(self, test: dict[str, Any]) -> BenchmarkResult:
        """Exécute un test avec Ollama + RAG.

        Args:
            test: Cas de test à exécuter

        Returns:
            Résultat de benchmark
        """
        start_time = time.time()

        # Construire la requête pour RAG
        query = f"Correction de configuration HAProxy: {test['name']}"
        if test.get("metadata", {}).get("keywords"):
            query += " " + " ".join(test["metadata"]["keywords"])

        # Récupérer le contexte
        retrieval_start = time.time()
        try:
            context, _, _ = retrieve_context_string(query, top_k=5)
        except Exception as e:
            if self.verbose:
                print(f"\nErreur lors du retrieval: {e}")
            context = ""
        retrieval_end = time.time()
        retrieval_time = retrieval_end - retrieval_start

        # Construire le prompt
        prompt = build_rag_prompt(test["original_config"], context)

        # Générer la réponse
        generation_start = time.time()
        try:
            response = generate_response_sync(
                question=prompt,
                context=context,
                model=self.model,
            )
        except Exception as e:
            if self.verbose:
                print(f"\nErreur lors de la génération: {e}")
            response = f"Erreur: {e}"
        generation_end = time.time()
        generation_time = generation_end - generation_start

        end_time = time.time()

        # Parser la réponse
        detected_errors, fixed_config = parse_llm_response(
            response, test.get("expected_errors", [])
        )

        # Si aucune config n'a été extraite, utiliser la réponse brute
        if not fixed_config:
            fixed_config = test["original_config"]

        # Calculer les métriques
        detection_rate = calculate_detection_rate(
            detected_errors, test.get("expected_errors", [])
        )
        syntax_compliance = calculate_syntax_compliance(fixed_config, self.validator)
        optimization_precision = calculate_optimization_precision(
            test["original_config"],
            fixed_config,
            test.get("expected_fixed_config", ""),
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
            test_id=test["id"],
            test_name=test["name"],
            category=test["category"],
            difficulty=test["difficulty"],
            detection_rate=detection_rate,
            syntax_compliance=syntax_compliance,
            optimization_precision=optimization_precision,
            hallucination_rate=hallucination_rate,
            global_score=global_score,
            response_time=response_time,
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            input_tokens=0,  # Non disponible avec generate_response_sync
            output_tokens=0,
            detected_errors=detected_errors,
            expected_errors=test.get("expected_errors", []),
            fixed_config=fixed_config,
            expected_fixed_config=test.get("expected_fixed_config", ""),
            model=self.model,
            rag_used=True,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


# =============================================================================
# Point d'entrée principal
# =============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse les arguments en ligne de commande.

    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="Benchmark de correction de configuration HAProxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  # Exécuter tous les tests
  python 07_bench_config_correction.py --tests all

  # Exécuter les tests rapides
  python 07_bench_config_correction.py --tests quick

  # Exécuter avec un modèle spécifique
  python 07_bench_config_correction.py --model qwen3:latest

  # Générer tous les formats de rapport
  python 07_bench_config_correction.py --format all
        """,
    )

    parser.add_argument(
        "--model",
        type=str,
        default=ollama_config.llm_model,
        help=f"Modèle LLM à utiliser (défaut: {ollama_config.llm_model})",
    )
    parser.add_argument(
        "--tests",
        type=str,
        choices=["all", "quick", "standard", "full"],
        default="all",
        help="Tests à exécuter (défaut: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bench_config_correction_report",
        help="Fichier de sortie sans extension (défaut: bench_config_correction_report)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown", "html", "all"],
        default="all",
        help="Format de rapport (défaut: all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbeux",
    )

    return parser.parse_args()


def load_tests(tests_level: str) -> list[dict[str, Any]]:
    """Charge les tests selon le niveau demandé.

    Args:
        tests_level: Niveau de tests (all, quick, standard, full)

    Returns:
        Liste des tests à exécuter
    """
    if tests_level == "quick":
        return get_quick_tests()
    elif tests_level == "standard":
        # Tests de difficulté easy et medium
        tests = get_tests_by_difficulty("easy") + get_tests_by_difficulty("medium")
        return tests
    elif tests_level in ("all", "full"):
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
    print("=" * 60)
    print("Benchmark de Correction de Configuration HAProxy")
    print("=" * 60)
    print(f"Modèle LLM : {args.model}")
    print(f"Niveau de tests : {args.tests}")
    print(f"Format de rapport : {args.format}")
    print(f"Mode verbeux : {args.verbose}")
    print("=" * 60)

    # Charger les tests
    tests = load_tests(args.tests)
    print(f"\nNombre de tests à exécuter : {len(tests)}")

    # Initialiser le runner
    runner = BenchmarkRunner(model=args.model, verbose=args.verbose)

    # Exécuter les tests avec Ollama seul
    ollama_results = runner.run_ollama_only(tests)

    # Exécuter les tests avec Ollama + RAG
    rag_results = runner.run_ollama_rag(tests)

    # Générer les résumés
    ollama_summary = generate_summary_from_results(ollama_results)
    rag_summary = generate_summary_from_results(rag_results)
    comparison = generate_comparison_summary(
        ollama_summary, rag_summary, ollama_results, rag_results
    )

    # Créer le rapport de benchmark
    benchmark_report = BenchmarkReport(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        model=args.model,
        total_tests=len(tests),
        ollama_only=ollama_summary,
        ollama_rag=rag_summary,
        comparison=comparison,
        detailed_results=ollama_results + rag_results,
    )

    # Générer et sauvegarder les rapports
    generator = BenchmarkReportGenerator(benchmark_report)

    print(f"\n{'=' * 60}")
    print("Génération des rapports")
    print(f"{'=' * 60}\n")

    formats_to_generate = []
    if args.format == "all":
        formats_to_generate = ["json", "markdown", "html"]
    else:
        formats_to_generate = [args.format]

    for fmt in formats_to_generate:
        try:
            generator.save_report(args.output, format=fmt)
            print(f"✅ Rapport {fmt} sauvegardé : {args.output}.{fmt}")
        except Exception as e:
            print(f"❌ Erreur lors de la génération du rapport {fmt}: {e}")

    # Afficher le résumé
    print(f"\n{'=' * 60}")
    print("Résumé des Résultats")
    print(f"{'=' * 60}")
    print("\nOllama Seul :")
    print(f"  Score global : {ollama_summary.avg_global_score:.2f}%")
    print(f"  Taux de réussite : {ollama_summary.success_rate:.2f}%")
    print(f"  Temps moyen : {ollama_summary.avg_response_time:.2f}s")
    print("\nOllama + RAG :")
    print(f"  Score global : {rag_summary.avg_global_score:.2f}%")
    print(f"  Taux de réussite : {rag_summary.success_rate:.2f}%")
    print(f"  Temps moyen : {rag_summary.avg_response_time:.2f}s")
    print("\nAmélioration :")
    print(f"  Score global : +{comparison.global_score_improvement:.2f}%")
    print(f"  Taux de détection : +{comparison.detection_improvement:.2f}%")
    print(f"  Conformité syntaxique : +{comparison.syntax_improvement * 100:.2f}%")
    print(f"  Réduction hallucinations : -{comparison.hallucination_reduction:.2f}%")
    print(f"  Surcoût temporel : +{comparison.time_overhead:.2f}s")

    if comparison.is_significant:
        print(
            f"\n✅ Amélioration statistiquement significative (p={comparison.p_value:.4f})"
        )
    elif comparison.p_value is not None:
        print(f"\n⚠️ Amélioration non significative (p={comparison.p_value:.4f})")

    print(f"\n{'=' * 60}")
    print("Benchmark terminé avec succès !")
    print(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
