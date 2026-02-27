# Spécification des Métriques de Performance du Benchmark

## Fichier : `bench_config_metrics.py`

Ce module définit les métriques de performance pour évaluer l'efficacité des prompts de correction de configuration HAProxy.

## Métriques Principales

### 1. Taux de Détection d'Erreurs (Detection Rate)

**Objectif** : Mesurer la capacité du LLM à identifier les erreurs dans une configuration.

```python
def calculate_detection_rate(
    detected_errors: list[ValidationError],
    expected_errors: list[dict]
) -> float:
    """
    Calcule le taux de détection d'erreurs.
    
    Formule :
    detection_rate = (true_positives / total_expected_errors) * 100
    
    Où :
    - true_positives : Erreurs correctement identifiées
    - false_positives : Erreurs détectées mais inexistantes
    - false_negatives : Erreurs existantes mais non détectées
    """
    # Calculer les TP, FP, FN
    true_positives = count_true_positives(detected_errors, expected_errors)
    false_positives = count_false_positives(detected_errors, expected_errors)
    false_negatives = count_false_negatives(detected_errors, expected_errors)
    
    total_expected = len(expected_errors)
    if total_expected == 0:
        return 100.0  # Pas d'erreurs attendues = parfait
    
    return (true_positives / total_expected) * 100
```

#### Sous-métriques

| Métrique | Formule | Description |
|-----------|---------|-------------|
| **Precision** | TP / (TP + FP) | Proportion d'erreurs détectées qui sont réelles |
| **Recall** | TP / (TP + FN) | Proportion d'erreurs réelles détectées |
| **F1-Score** | 2 * (Precision * Recall) / (Precision + Recall) | Moyenne harmonique de Precision et Recall |

#### Interprétation

| Score | Qualité |
|-------|---------|
| 90-100% | Excellent - Presque toutes les erreurs détectées |
| 75-89% | Bon - La plupart des erreurs détectées |
| 50-74% | Moyen - Environ la moitié des erreurs détectées |
| < 50% | Mauvais - Moins de la moitié des erreurs détectées |

### 2. Conformité Syntaxique (Syntax Compliance)

**Objectif** : Mesurer la validité syntaxique de la configuration corrigée.

```python
def calculate_syntax_compliance(
    fixed_config: str,
    validator: HAProxyValidator
) -> float:
    """
    Calcule la conformité syntaxique.
    
    Formule :
    syntax_compliance = get_syntax_compliance_score(fixed_config)
    
    Le score est calculé par le validateur :
    score = max(0.0, 1.0 - (errors * 0.1) - (warnings * 0.02))
    """
    result = validator.validate(fixed_config)
    return validator.get_syntax_compliance_score(fixed_config)
```

#### Sous-métriques

| Métrique | Description |
|-----------|-------------|
| **Nombre d'erreurs** | Erreurs syntaxiques dans la configuration corrigée |
| **Nombre de warnings** | Avertissements dans la configuration corrigée |
| **Score brut** | Score de 0.0 à 1.0 calculé par le validateur |

#### Interprétation

| Score | Qualité |
|-------|---------|
| 1.0 | Parfait - Aucune erreur ni warning |
| 0.9-0.99 | Excellent - Quelques warnings mineurs |
| 0.7-0.89 | Bon - Erreurs mineures ou warnings modérés |
| 0.5-0.69 | Moyen - Erreurs modérées |
| < 0.5 | Mauvais - Erreurs multiples |

### 3. Précision de l'Optimisation (Optimization Precision)

**Objectif** : Mesurer la qualité des optimisations proposées par le LLM.

```python
def calculate_optimization_precision(
    original_config: str,
    fixed_config: str,
    expected_fixed_config: str,
    validator: HAProxyValidator
) -> float:
    """
    Calcule la précision de l'optimisation.
    
    Formule :
    optimization_precision = (correct_changes / total_changes) * 100
    
    Où :
    - correct_changes : Modifications qui correspondent à l'attendu
    - total_changes : Nombre total de modifications apportées
    """
    # Extraire les changements
    changes = extract_changes(original_config, fixed_config)
    expected_changes = extract_changes(original_config, expected_fixed_config)
    
    # Comparer avec l'attendu
    correct_changes = count_matching_changes(changes, expected_changes)
    total_changes = len(changes)
    
    if total_changes == 0:
        return 100.0  # Pas de changements = parfait
    
    return (correct_changes / total_changes) * 100
```

#### Sous-métriques

| Métrique | Description |
|-----------|-------------|
| **Lignes modifiées** | Nombre de lignes modifiées |
| **Lignes ajoutées** | Nombre de lignes ajoutées |
| **Lignes supprimées** | Nombre de lignes supprimées |
| **Similarité** | Similarité avec la configuration attendue |

#### Interprétation

| Score | Qualité |
|-------|---------|
| 90-100% | Excellent - Optimisations quasi parfaites |
| 75-89% | Bon - Optimisations correctes avec quelques écarts |
| 50-74% | Moyen - Optimisations partiellement correctes |
| < 50% | Mauvais - Optimisations incorrectes |

### 4. Réduction des Hallucinations (Hallucination Reduction)

**Objectif** : Mesurer la tendance du LLM à inventer des éléments non documentés.

```python
def calculate_hallucination_rate(
    fixed_config: str,
    validator: HAProxyValidator,
    rag_used: bool
) -> float:
    """
    Calcule le taux d'hallucination.
    
    Formule :
    hallucination_rate = (hallucinated_elements / total_elements) * 100
    
    Où :
    - hallucinated_elements : Éléments inventés non présents dans la documentation
    - total_elements : Nombre total d'éléments dans la configuration
    """
    # Analyser la configuration
    elements = extract_config_elements(fixed_config)
    
    # Vérifier chaque élément
    hallucinated = []
    for element in elements:
        if not is_valid_haproxy_element(element):
            hallucinated.append(element)
    
    total_elements = len(elements)
    if total_elements == 0:
        return 0.0  # Pas d'éléments = pas d'hallucinations
    
    return (len(hallucinated) / total_elements) * 100
```

#### Types d'Hallucinations

| Type | Exemple | Détection |
|------|---------|-----------|
| **Option inexistante** | `option invalid_option` | Vérification dans la grammaire |
| **Directive inconnue** | `unknown_directive value` | Vérification dans la grammaire |
| **Paramètre invalide** | `server name port invalid_param` | Validation des paramètres |
| **Valeur hors spécification** | `timeout connect 999999s` | Validation des valeurs |

#### Interprétation

| Score | Qualité |
|-------|---------|
| 0-5% | Excellent - Très peu d'hallucinations |
| 5-10% | Bon - Quelques hallucinations mineures |
| 10-20% | Moyen - Hallucinations modérées |
| > 20% | Mauvais - Beaucoup d'hallucinations |

### 5. Score Global (Global Score)

**Objectif** : Score composite combinant toutes les métriques.

```python
def calculate_global_score(
    detection_rate: float,
    syntax_compliance: float,
    optimization_precision: float,
    hallucination_rate: float
) -> float:
    """
    Calcule le score global.
    
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
    """
    return (
        detection_rate * 0.30 +
        syntax_compliance * 100 * 0.30 +
        optimization_precision * 0.25 +
        (100 - hallucination_rate) * 0.15
    )
```

#### Interprétation

| Score | Qualité |
|-------|---------|
| 90-100% | Excellent - Performance quasi parfaite |
| 75-89% | Bon - Performance satisfaisante |
| 60-74% | Moyen - Performance acceptable |
| < 60% | Mauvais - Performance insuffisante |

## Métriques Additionnelles

### 6. Temps de Réponse (Response Time)

**Objectif** : Mesurer la latence de génération.

```python
def calculate_response_time(
    start_time: float,
    end_time: float
) -> float:
    """
    Calcule le temps de réponse en secondes.
    """
    return end_time - start_time
```

#### Sous-métriques

| Métrique | Description |
|-----------|-------------|
| **Temps de retrieval** | Temps passé à récupérer le contexte (RAG uniquement) |
| **Temps de génération** | Temps passé à générer la réponse |
| **Temps total** | Temps total du traitement |

### 7. Consommation de Tokens (Token Usage)

**Objectif** : Mesurer la consommation de ressources.

```python
def calculate_token_usage(
    input_tokens: int,
    output_tokens: int
) -> dict:
    """
    Calcule l'utilisation des tokens.
    """
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "tokens_per_second": output_tokens / generation_time
    }
```

### 8. Taux de Réussite Global (Global Success Rate)

**Objectif** : Mesurer le pourcentage de tests réussis.

```python
def calculate_success_rate(
    test_results: list[dict]
) -> float:
    """
    Calcule le taux de réussite global.
    
    Formule :
    success_rate = (successful_tests / total_tests) * 100
    
    Un test est réussi si :
    - syntax_compliance >= 0.8
    - hallucination_rate <= 10%
    - global_score >= 60
    """
    successful = sum(
        1 for r in test_results
        if r["syntax_compliance"] >= 0.8
        and r["hallucination_rate"] <= 10
        and r["global_score"] >= 60
    )
    return (successful / len(test_results)) * 100
```

## Structure des Résultats

```python
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
```

## Structure du Rapport Global

```python
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
```

## Calculs Statistiques

### Test de Significativité (Wilcoxon Signed-Rank Test)

```python
from scipy.stats import wilcoxon

def calculate_significance(
    ollama_scores: list[float],
    rag_scores: list[float]
) -> tuple[bool, float | None]:
    """
    Calcule la significativité statistique de l'amélioration.
    
    Utilise le test de Wilcoxon Signed-Rank pour comparer
    les scores des deux architectures.
    """
    if len(ollama_scores) != len(rag_scores):
        return False, None
    
    try:
        statistic, p_value = wilcoxon(ollama_scores, rag_scores)
        is_significant = p_value < 0.05
        return is_significant, p_value
    except:
        return False, None
```

### Intervalle de Confiance

```python
import numpy as np
from scipy import stats

def calculate_confidence_interval(
    values: list[float],
    confidence: float = 0.95
) -> tuple[float, float]:
    """
    Calcule l'intervalle de confiance pour une série de valeurs.
    """
    mean = np.mean(values)
    std_err = stats.sem(values)
    h = std_err * stats.t.ppf((1 + confidence) / 2, len(values) - 1)
    return (mean - h, mean + h)
```

## Visualisation des Résultats

### Graphiques Suggérés

1. **Barres comparatives** : Comparaison des métriques entre Ollama seul et Ollama+RAG
2. **Box plots** : Distribution des scores par catégorie
3. **Scatter plot** : Relation entre le temps de réponse et la qualité
4. **Heatmap** : Matrice de confusion pour les types d'erreurs
5. **Line chart** : Évolution des scores au fil du temps (si exécutions multiples)

### Exemple de Graphique

```python
import matplotlib.pyplot as plt

def plot_comparison(ollama_results: dict, rag_results: dict):
    """Génère un graphique comparatif."""
    metrics = [
        "Detection Rate",
        "Syntax Compliance",
        "Optimization Precision",
        "Global Score"
    ]
    
    ollama_values = [
        ollama_results["avg_detection_rate"],
        ollama_results["avg_syntax_compliance"] * 100,
        ollama_results["avg_optimization_precision"],
        ollama_results["avg_global_score"]
    ]
    
    rag_values = [
        rag_results["avg_detection_rate"],
        rag_results["avg_syntax_compliance"] * 100,
        rag_results["avg_optimization_precision"],
        rag_results["avg_global_score"]
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, ollama_values, width, label='Ollama Seul')
    rects2 = ax.bar(x + width/2, rag_values, width, label='Ollama + RAG')
    
    ax.set_ylabel('Score (%)')
    ax.set_title('Comparaison des Métriques')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.set_ylim([0, 100])
    
    fig.tight_layout()
    plt.savefig('benchmark_comparison.png')
```

## Critères de Succès

### Objectifs Minimaux

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|--------------|--------------|-------------|
| Taux de détection | ≥ 70% | ≥ 85% | ≥ +10% |
| Conformité syntaxique | ≥ 0.75 | ≥ 0.85 | ≥ +0.05 |
| Précision optimisation | ≥ 65% | ≥ 80% | ≥ +10% |
| Hallucinations | ≤ 15% | ≤ 8% | -≥ 5% |
| Score global | ≥ 65% | ≥ 80% | ≥ +10% |

### Objectifs Idéaux

| Métrique | Ollama Seul | Ollama + RAG | Amélioration |
|----------|--------------|--------------|-------------|
| Taux de détection | ≥ 80% | ≥ 95% | ≥ +15% |
| Conformité syntaxique | ≥ 0.85 | ≥ 0.95 | ≥ +0.10 |
| Précision optimisation | ≥ 75% | ≥ 90% | ≥ +15% |
| Hallucinations | ≤ 10% | ≤ 5% | -≥ 5% |
| Score global | ≥ 75% | ≥ 90% | ≥ +15% |
