"""Module de métriques de performance pour le benchmark de correction de configuration HAProxy.

Ce module définit les métriques et les structures de données pour évaluer
l'efficacité des prompts de correction de configuration HAProxy.
"""

from dataclasses import dataclass
from typing import Any
import time

from haproxy_validator import (
    HAProxyValidator,
    ValidationError,
    ErrorType,
    ErrorSeverity,
)

# Imports optionnels pour les calculs statistiques
try:
    from scipy.stats import wilcoxon
    from scipy import stats
    import numpy as np

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Résultat d'un test de benchmark."""

    test_id: str
    test_name: str
    category: str
    difficulty: str

    # Métriques
    detection_rate: float
    syntax_compliance: float
    optimization_precision: float
    hallucination_rate: float
    global_score: float

    # Métriques additionnelles
    response_time: float
    retrieval_time: float | None
    generation_time: float
    input_tokens: int
    output_tokens: int

    # Détails
    detected_errors: list[ValidationError]
    expected_errors: list[dict]
    fixed_config: str
    expected_fixed_config: str

    # Métadonnées
    model: str
    rag_used: bool
    timestamp: str


@dataclass
class CategorySummary:
    """Résumé des résultats pour une catégorie."""

    category: str
    count: int
    avg_detection_rate: float
    avg_syntax_compliance: float
    avg_optimization_precision: float
    avg_hallucination_rate: float
    avg_global_score: float
    avg_response_time: float
    success_rate: float


@dataclass
class DifficultySummary:
    """Résumé des résultats pour un niveau de difficulté."""

    difficulty: str
    count: int
    avg_detection_rate: float
    avg_syntax_compliance: float
    avg_optimization_precision: float
    avg_hallucination_rate: float
    avg_global_score: float
    avg_response_time: float
    success_rate: float


@dataclass
class BenchmarkSummary:
    """Résumé des résultats pour une architecture."""

    avg_detection_rate: float
    avg_syntax_compliance: float
    avg_optimization_precision: float
    avg_hallucination_rate: float
    avg_global_score: float
    avg_response_time: float
    success_rate: float

    # Résultats par catégorie
    by_category: dict[str, CategorySummary]

    # Résultats par difficulté
    by_difficulty: dict[str, DifficultySummary]


@dataclass
class ComparisonSummary:
    """Résumé de la comparaison entre les deux architectures."""

    detection_improvement: float
    syntax_improvement: float
    optimization_improvement: float
    hallucination_reduction: float
    global_score_improvement: float
    time_overhead: float

    # Significativité statistique
    is_significant: bool
    p_value: float | None


@dataclass
class BenchmarkReport:
    """Rapport global du benchmark."""

    timestamp: str
    model: str
    total_tests: int

    # Résultats Ollama seul
    ollama_only: BenchmarkSummary

    # Résultats Ollama + RAG
    ollama_rag: BenchmarkSummary

    # Comparaison
    comparison: ComparisonSummary

    # Résultats détaillés
    detailed_results: list[BenchmarkResult]


# =============================================================================
# Fonctions utilitaires
# =============================================================================


def count_true_positives(
    detected_errors: list[ValidationError], expected_errors: list[dict]
) -> int:
    """Compte les vrais positifs (erreurs correctement identifiées).

    Args:
        detected_errors: Liste des erreurs détectées par le LLM
        expected_errors: Liste des erreurs attendues

    Returns:
        Nombre de vrais positifs
    """
    true_positives = 0
    for detected in detected_errors:
        for expected in expected_errors:
            if (
                detected.line == expected.get("line")
                and str(detected.error_type) == expected.get("error_type")
                and detected.message == expected.get("message")
            ):
                true_positives += 1
                break
    return true_positives


def count_false_positives(
    detected_errors: list[ValidationError], expected_errors: list[dict]
) -> int:
    """Compte les faux positifs (erreurs détectées mais inexistantes).

    Args:
        detected_errors: Liste des erreurs détectées par le LLM
        expected_errors: Liste des erreurs attendues

    Returns:
        Nombre de faux positifs
    """
    false_positives = 0
    for detected in detected_errors:
        is_expected = False
        for expected in expected_errors:
            if (
                detected.line == expected.get("line")
                and str(detected.error_type) == expected.get("error_type")
                and detected.message == expected.get("message")
            ):
                is_expected = True
                break
        if not is_expected:
            false_positives += 1
    return false_positives


def count_false_negatives(
    detected_errors: list[ValidationError], expected_errors: list[dict]
) -> int:
    """Compte les faux négatifs (erreurs existantes mais non détectées).

    Args:
        detected_errors: Liste des erreurs détectées par le LLM
        expected_errors: Liste des erreurs attendues

    Returns:
        Nombre de faux négatifs
    """
    false_negatives = 0
    for expected in expected_errors:
        is_detected = False
        for detected in detected_errors:
            if (
                detected.line == expected.get("line")
                and str(detected.error_type) == expected.get("error_type")
                and detected.message == expected.get("message")
            ):
                is_detected = True
                break
        if not is_detected:
            false_negatives += 1
    return false_negatives


def extract_changes(original_config: str, fixed_config: str) -> list[dict[str, Any]]:
    """Extrait les changements entre deux configurations.

    Args:
        original_config: Configuration originale
        fixed_config: Configuration modifiée

    Returns:
        Liste des changements détectés
    """
    original_lines = original_config.splitlines()
    fixed_lines = fixed_config.splitlines()

    changes = []

    # Détecter les lignes modifiées
    max_lines = max(len(original_lines), len(fixed_lines))
    for i in range(max_lines):
        original_line = original_lines[i] if i < len(original_lines) else ""
        fixed_line = fixed_lines[i] if i < len(fixed_lines) else ""

        if original_line != fixed_line:
            changes.append(
                {
                    "line": i + 1,
                    "original": original_line,
                    "fixed": fixed_line,
                    "type": "modified"
                    if original_line and fixed_line
                    else ("added" if fixed_line else "removed"),
                }
            )

    return changes


def count_matching_changes(
    changes: list[dict[str, Any]], expected_changes: list[dict[str, Any]]
) -> int:
    """Compte les changements qui correspondent à ceux attendus.

    Args:
        changes: Liste des changements détectés
        expected_changes: Liste des changements attendus

    Returns:
        Nombre de changements correspondants
    """
    matching = 0
    for change in changes:
        for expected in expected_changes:
            if (
                change.get("line") == expected.get("line")
                and change.get("fixed") == expected.get("fixed")
                and change.get("type") == expected.get("type")
            ):
                matching += 1
                break
    return matching


def extract_config_elements(config: str) -> list[dict[str, Any]]:
    """Extrait les éléments d'une configuration HAProxy.

    Args:
        config: Configuration HAProxy

    Returns:
        Liste des éléments extraits
    """
    elements = []
    lines = config.splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) >= 2:
            elements.append({"directive": parts[0], "args": parts[1:], "line": line})

    return elements


def is_valid_haproxy_element(
    element: dict[str, Any], validator: HAProxyValidator | None = None
) -> bool:
    """Vérifie si un élément est valide selon la grammaire HAProxy.

    Args:
        element: Élément à vérifier
        validator: Validateur HAProxy (optionnel)

    Returns:
        True si l'élément est valide, False sinon
    """
    # Liste des directives HAProxy valides (simplifiée)
    valid_directives = {
        "global",
        "defaults",
        "frontend",
        "backend",
        "listen",
        "bind",
        "server",
        "option",
        "timeout",
        "log",
        "maxconn",
        "mode",
        "balance",
        "cookie",
        "acl",
        "use_backend",
        "http-request",
        "http-response",
        "default_backend",
        "stats",
        "errorfile",
        "errorloc",
        "http-check",
    }

    directive = element.get("directive", "")
    return directive in valid_directives


# =============================================================================
# Fonctions de calcul des métriques principales
# =============================================================================


def calculate_detection_rate(
    detected_errors: list[ValidationError], expected_errors: list[dict]
) -> float:
    """Calcule le taux de détection d'erreurs.

    Formule :
    detection_rate = (true_positives / total_expected_errors) * 100

    Args:
        detected_errors: Liste des erreurs détectées par le LLM
        expected_errors: Liste des erreurs attendues

    Returns:
        Taux de détection en pourcentage
    """
    true_positives = count_true_positives(detected_errors, expected_errors)
    total_expected = len(expected_errors)

    if total_expected == 0:
        return 100.0

    return (true_positives / total_expected) * 100


def calculate_syntax_compliance(
    fixed_config: str, validator: HAProxyValidator
) -> float:
    """Calcule la conformité syntaxique.

    Le score est calculé par le validateur :
    score = max(0.0, 1.0 - (errors * 0.1) - (warnings * 0.02))

    Args:
        fixed_config: Configuration corrigée
        validator: Validateur HAProxy

    Returns:
        Score de conformité syntaxique (0.0 à 1.0)
    """
    return validator.get_syntax_compliance_score(fixed_config)


def calculate_optimization_precision(
    original_config: str,
    fixed_config: str,
    expected_fixed_config: str,
    validator: HAProxyValidator,
) -> float:
    """Calcule la précision de l'optimisation.

    Formule :
    optimization_precision = (correct_changes / total_changes) * 100

    Args:
        original_config: Configuration originale
        fixed_config: Configuration corrigée
        expected_fixed_config: Configuration attendue
        validator: Validateur HAProxy

    Returns:
        Précision de l'optimisation en pourcentage
    """
    changes = extract_changes(original_config, fixed_config)
    expected_changes = extract_changes(original_config, expected_fixed_config)

    correct_changes = count_matching_changes(changes, expected_changes)
    total_changes = len(changes)

    if total_changes == 0:
        return 100.0

    return (correct_changes / total_changes) * 100


def calculate_hallucination_rate(
    fixed_config: str, validator: HAProxyValidator, rag_used: bool
) -> float:
    """Calcule le taux d'hallucination.

    Formule :
    hallucination_rate = (hallucinated_elements / total_elements) * 100

    Args:
        fixed_config: Configuration corrigée
        validator: Validateur HAProxy
        rag_used: Indique si RAG a été utilisé

    Returns:
        Taux d'hallucination en pourcentage
    """
    elements = extract_config_elements(fixed_config)

    hallucinated = []
    for element in elements:
        if not is_valid_haproxy_element(element, validator):
            hallucinated.append(element)

    total_elements = len(elements)
    if total_elements == 0:
        return 0.0

    return (len(hallucinated) / total_elements) * 100


def calculate_global_score(
    detection_rate: float,
    syntax_compliance: float,
    optimization_precision: float,
    hallucination_rate: float,
) -> float:
    """Calcule le score global composite.

    Formule :
    global_score = (
        detection_rate * 0.30 +
        syntax_compliance * 100 * 0.30 +
        optimization_precision * 0.25 +
        (100 - hallucination_rate) * 0.15
    )

    Poids :
    - Taux de détection : 30%
    - Conformité syntaxique : 30%
    - Précision d'optimisation : 25%
    - Réduction d'hallucinations : 15%

    Args:
        detection_rate: Taux de détection d'erreurs
        syntax_compliance: Conformité syntaxique
        optimization_precision: Précision de l'optimisation
        hallucination_rate: Taux d'hallucination

    Returns:
        Score global en pourcentage
    """
    return (
        detection_rate * 0.30
        + syntax_compliance * 100 * 0.30
        + optimization_precision * 0.25
        + (100 - hallucination_rate) * 0.15
    )


# =============================================================================
# Fonctions de calcul additionnelles
# =============================================================================


def calculate_response_time(start_time: float, end_time: float) -> float:
    """Calcule le temps de réponse en secondes.

    Args:
        start_time: Temps de début (epoch)
        end_time: Temps de fin (epoch)

    Returns:
        Temps de réponse en secondes
    """
    return end_time - start_time


def calculate_token_usage(
    input_tokens: int, output_tokens: int, generation_time: float
) -> dict[str, Any]:
    """Calcule l'utilisation des tokens.

    Args:
        input_tokens: Nombre de tokens d'entrée
        output_tokens: Nombre de tokens de sortie
        generation_time: Temps de génération en secondes

    Returns:
        Dictionnaire avec les métriques de tokens
    """
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "tokens_per_second": output_tokens / generation_time
        if generation_time > 0
        else 0,
    }


def calculate_success_rate(test_results: list[dict[str, Any]]) -> float:
    """Calcule le taux de réussite global.

    Formule :
    success_rate = (successful_tests / total_tests) * 100

    Un test est réussi si :
    - syntax_compliance >= 0.8
    - hallucination_rate <= 10%
    - global_score >= 60

    Args:
        test_results: Liste des résultats de tests

    Returns:
        Taux de réussite en pourcentage
    """
    if not test_results:
        return 0.0

    successful = sum(
        1
        for r in test_results
        if r.get("syntax_compliance", 0) >= 0.8
        and r.get("hallucination_rate", 100) <= 10
        and r.get("global_score", 0) >= 60
    )

    return (successful / len(test_results)) * 100


# =============================================================================
# Fonctions statistiques
# =============================================================================


def calculate_significance(
    ollama_scores: list[float], rag_scores: list[float]
) -> tuple[bool, float | None]:
    """Calcule la significativité statistique de l'amélioration.

    Utilise le test de Wilcoxon Signed-Rank pour comparer
    les scores des deux architectures.

    Args:
        ollama_scores: Scores de l'architecture Ollama seul
        rag_scores: Scores de l'architecture Ollama + RAG

    Returns:
        Tuple (is_significant, p_value)
    """
    if not SCIPY_AVAILABLE:
        return False, None

    if len(ollama_scores) != len(rag_scores):
        return False, None

    try:
        statistic, p_value = wilcoxon(ollama_scores, rag_scores)
        is_significant = p_value < 0.05
        return is_significant, p_value
    except Exception:
        return False, None


def calculate_confidence_interval(
    values: list[float], confidence: float = 0.95
) -> tuple[float, float] | None:
    """Calcule l'intervalle de confiance pour une série de valeurs.

    Args:
        values: Liste de valeurs
        confidence: Niveau de confiance (0.0 à 1.0)

    Returns:
        Tuple (lower_bound, upper_bound) ou None si scipy non disponible
    """
    if not SCIPY_AVAILABLE:
        return None

    try:
        mean = np.mean(values)
        std_err = stats.sem(values)
        h = std_err * stats.t.ppf((1 + confidence) / 2, len(values) - 1)
        return (float(mean - h), float(mean + h))
    except Exception:
        return None


# =============================================================================
# Fonctions de génération de rapport
# =============================================================================


def generate_summary_from_results(results: list[BenchmarkResult]) -> BenchmarkSummary:
    """Génère un résumé à partir des résultats de benchmark.

    Args:
        results: Liste des résultats de benchmark

    Returns:
        Résumé des résultats
    """
    if not results:
        return BenchmarkSummary(
            avg_detection_rate=0.0,
            avg_syntax_compliance=0.0,
            avg_optimization_precision=0.0,
            avg_hallucination_rate=0.0,
            avg_global_score=0.0,
            avg_response_time=0.0,
            success_rate=0.0,
            by_category={},
            by_difficulty={},
        )

    # Calculer les moyennes globales
    total = len(results)
    avg_detection_rate = sum(r.detection_rate for r in results) / total
    avg_syntax_compliance = sum(r.syntax_compliance for r in results) / total
    avg_optimization_precision = sum(r.optimization_precision for r in results) / total
    avg_hallucination_rate = sum(r.hallucination_rate for r in results) / total
    avg_global_score = sum(r.global_score for r in results) / total
    avg_response_time = sum(r.response_time for r in results) / total

    # Calculer le taux de réussite
    test_results_dict = [
        {
            "syntax_compliance": r.syntax_compliance,
            "hallucination_rate": r.hallucination_rate,
            "global_score": r.global_score,
        }
        for r in results
    ]
    success_rate = calculate_success_rate(test_results_dict)

    # Résumés par catégorie
    by_category: dict[str, CategorySummary] = {}
    categories = set(r.category for r in results)
    for category in categories:
        cat_results = [r for r in results if r.category == category]
        cat_count = len(cat_results)
        by_category[category] = CategorySummary(
            category=category,
            count=cat_count,
            avg_detection_rate=sum(r.detection_rate for r in cat_results) / cat_count,
            avg_syntax_compliance=sum(r.syntax_compliance for r in cat_results)
            / cat_count,
            avg_optimization_precision=sum(
                r.optimization_precision for r in cat_results
            )
            / cat_count,
            avg_hallucination_rate=sum(r.hallucination_rate for r in cat_results)
            / cat_count,
            avg_global_score=sum(r.global_score for r in cat_results) / cat_count,
            avg_response_time=sum(r.response_time for r in cat_results) / cat_count,
            success_rate=calculate_success_rate(
                [
                    {
                        "syntax_compliance": r.syntax_compliance,
                        "hallucination_rate": r.hallucination_rate,
                        "global_score": r.global_score,
                    }
                    for r in cat_results
                ]
            ),
        )

    # Résumés par difficulté
    by_difficulty: dict[str, DifficultySummary] = {}
    difficulties = set(r.difficulty for r in results)
    for difficulty in difficulties:
        diff_results = [r for r in results if r.difficulty == difficulty]
        diff_count = len(diff_results)
        by_difficulty[difficulty] = DifficultySummary(
            difficulty=difficulty,
            count=diff_count,
            avg_detection_rate=sum(r.detection_rate for r in diff_results) / diff_count,
            avg_syntax_compliance=sum(r.syntax_compliance for r in diff_results)
            / diff_count,
            avg_optimization_precision=sum(
                r.optimization_precision for r in diff_results
            )
            / diff_count,
            avg_hallucination_rate=sum(r.hallucination_rate for r in diff_results)
            / diff_count,
            avg_global_score=sum(r.global_score for r in diff_results) / diff_count,
            avg_response_time=sum(r.response_time for r in diff_results) / diff_count,
            success_rate=calculate_success_rate(
                [
                    {
                        "syntax_compliance": r.syntax_compliance,
                        "hallucination_rate": r.hallucination_rate,
                        "global_score": r.global_score,
                    }
                    for r in diff_results
                ]
            ),
        )

    return BenchmarkSummary(
        avg_detection_rate=avg_detection_rate,
        avg_syntax_compliance=avg_syntax_compliance,
        avg_optimization_precision=avg_optimization_precision,
        avg_hallucination_rate=avg_hallucination_rate,
        avg_global_score=avg_global_score,
        avg_response_time=avg_response_time,
        success_rate=success_rate,
        by_category=by_category,
        by_difficulty=by_difficulty,
    )


def generate_comparison_summary(
    ollama_only: BenchmarkSummary,
    ollama_rag: BenchmarkSummary,
    ollama_results: list[BenchmarkResult],
    rag_results: list[BenchmarkResult],
) -> ComparisonSummary:
    """Génère le résumé de comparaison entre les deux architectures.

    Args:
        ollama_only: Résumé des résultats Ollama seul
        ollama_rag: Résumé des résultats Ollama + RAG
        ollama_results: Résultats détaillés Ollama seul
        rag_results: Résultats détaillés Ollama + RAG

    Returns:
        Résumé de comparaison
    """
    detection_improvement = (
        ollama_rag.avg_detection_rate - ollama_only.avg_detection_rate
    )
    syntax_improvement = (
        ollama_rag.avg_syntax_compliance - ollama_only.avg_syntax_compliance
    )
    optimization_improvement = (
        ollama_rag.avg_optimization_precision - ollama_only.avg_optimization_precision
    )
    hallucination_reduction = (
        ollama_only.avg_hallucination_rate - ollama_rag.avg_hallucination_rate
    )
    global_score_improvement = (
        ollama_rag.avg_global_score - ollama_only.avg_global_score
    )
    time_overhead = ollama_rag.avg_response_time - ollama_only.avg_response_time

    # Test de significativité statistique
    ollama_scores = [r.global_score for r in ollama_results]
    rag_scores = [r.global_score for r in rag_results]
    is_significant, p_value = calculate_significance(ollama_scores, rag_scores)

    return ComparisonSummary(
        detection_improvement=detection_improvement,
        syntax_improvement=syntax_improvement,
        optimization_improvement=optimization_improvement,
        hallucination_reduction=hallucination_reduction,
        global_score_improvement=global_score_improvement,
        time_overhead=time_overhead,
        is_significant=is_significant,
        p_value=p_value,
    )


# =============================================================================
# Test du module
# =============================================================================

if __name__ == "__main__":
    # Créer un validateur HAProxy
    validator = HAProxyValidator()

    # Créer des erreurs attendues
    expected_errors = [
        {"line": 10, "error_type": "syntax", "message": "Invalid directive"},
        {"line": 15, "error_type": "validation", "message": "Invalid port"},
    ]

    # Créer des erreurs détectées
    detected_errors = [
        ValidationError(
            line=10,
            column=0,
            error_type=ErrorType.SYNTAX,
            severity=ErrorSeverity.ERROR,
            message="Invalid directive",
        ),
        ValidationError(
            line=12,
            column=0,
            error_type=ErrorType.SYNTAX,
            severity=ErrorSeverity.ERROR,
            message="Unknown option",
        ),
    ]

    # Tester le calcul du taux de détection
    detection_rate = calculate_detection_rate(detected_errors, expected_errors)
    print(f"Taux de détection: {detection_rate:.2f}%")

    # Tester les sous-métriques
    tp = count_true_positives(detected_errors, expected_errors)
    fp = count_false_positives(detected_errors, expected_errors)
    fn = count_false_negatives(detected_errors, expected_errors)
    print(f"Vrais positifs: {tp}, Faux positifs: {fp}, Faux négatifs: {fn}")

    # Créer des configurations de test
    original_config = """global
    log /dev/log local0
    maxconn 1000

defaults
    timeout connect 5000ms
    timeout client 50000ms
"""

    fixed_config = """global
    log /dev/log local0
    maxconn 2000

defaults
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
"""

    expected_fixed_config = """global
    log /dev/log local0
    maxconn 2000

defaults
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
"""

    # Tester la conformité syntaxique
    syntax_compliance = calculate_syntax_compliance(fixed_config, validator)
    print(f"Conformité syntaxique: {syntax_compliance:.2f}")

    # Tester la précision de l'optimisation
    optimization_precision = calculate_optimization_precision(
        original_config, fixed_config, expected_fixed_config, validator
    )
    print(f"Précision de l'optimisation: {optimization_precision:.2f}%")

    # Tester le taux d'hallucination
    hallucination_rate = calculate_hallucination_rate(fixed_config, validator, True)
    print(f"Taux d'hallucination: {hallucination_rate:.2f}%")

    # Tester le score global
    global_score = calculate_global_score(
        detection_rate=detection_rate,
        syntax_compliance=syntax_compliance,
        optimization_precision=optimization_precision,
        hallucination_rate=hallucination_rate,
    )
    print(f"Score global: {global_score:.2f}%")

    # Tester le temps de réponse
    start_time = time.time()
    time.sleep(0.1)
    end_time = time.time()
    response_time = calculate_response_time(start_time, end_time)
    print(f"Temps de réponse: {response_time:.3f}s")

    # Tester l'utilisation des tokens
    token_usage = calculate_token_usage(
        input_tokens=1000, output_tokens=500, generation_time=2.0
    )
    print(f"Utilisation des tokens: {token_usage}")

    # Tester le taux de réussite
    test_results = [
        {"syntax_compliance": 0.9, "hallucination_rate": 5.0, "global_score": 85.0},
        {"syntax_compliance": 0.7, "hallucination_rate": 15.0, "global_score": 55.0},
        {"syntax_compliance": 0.95, "hallucination_rate": 3.0, "global_score": 90.0},
    ]
    success_rate = calculate_success_rate(test_results)
    print(f"Taux de réussite: {success_rate:.2f}%")

    # Tester les fonctions statistiques (si scipy disponible)
    if SCIPY_AVAILABLE:
        print("\nTests statistiques (scipy disponible):")
        ollama_scores = [70.0, 75.0, 80.0, 72.0, 78.0]
        rag_scores = [85.0, 88.0, 92.0, 86.0, 90.0]
        is_significant, p_value = calculate_significance(ollama_scores, rag_scores)
        print(f"Significativité: {is_significant}, p-value: {p_value}")

        confidence_interval = calculate_confidence_interval(ollama_scores)
        print(f"Intervalle de confiance (95%): {confidence_interval}")
    else:
        print("\nTests statistiques: scipy non disponible")

    # Créer un résultat de benchmark fictif
    benchmark_result = BenchmarkResult(
        test_id="test_001",
        test_name="Test de correction de timeout",
        category="timeout",
        difficulty="easy",
        detection_rate=detection_rate,
        syntax_compliance=syntax_compliance,
        optimization_precision=optimization_precision,
        hallucination_rate=hallucination_rate,
        global_score=global_score,
        response_time=response_time,
        retrieval_time=0.05,
        generation_time=response_time - 0.05,
        input_tokens=1000,
        output_tokens=500,
        detected_errors=detected_errors,
        expected_errors=expected_errors,
        fixed_config=fixed_config,
        expected_fixed_config=expected_fixed_config,
        model="qwen2.5-coder:7b",
        rag_used=True,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    )

    print(f"\nRésultat de benchmark créé: {benchmark_result.test_id}")
    print(f"  Score global: {benchmark_result.global_score:.2f}%")

    # Générer un résumé à partir des résultats
    results = [benchmark_result]
    summary = generate_summary_from_results(results)
    print("\nRésumé généré:")
    print(f"  Taux de détection moyen: {summary.avg_detection_rate:.2f}%")
    print(f"  Conformité syntaxique moyenne: {summary.avg_syntax_compliance:.2f}")
    print(f"  Taux de réussite: {summary.success_rate:.2f}%")

    print("\nTests termines avec succes!")
