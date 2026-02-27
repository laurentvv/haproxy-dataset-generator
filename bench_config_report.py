"""Module de génération de rapports pour le benchmark de correction de configuration HAProxy.

Ce module fournit des fonctionnalités pour générer des rapports complets
et lisibles à partir des résultats de benchmark, en plusieurs formats :
JSON, Markdown et HTML.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from bench_config_metrics import (
    BenchmarkReport,
    BenchmarkSummary,
    ComparisonSummary,
    BenchmarkResult,
)

# Imports optionnels pour les graphiques
try:
    import matplotlib.pyplot as plt
    import matplotlib
    import base64
    from io import BytesIO

    matplotlib.use("Agg")  # Mode non-interactif
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class BenchmarkReportGenerator:
    """Générateur de rapports pour le benchmark de configuration HAProxy.

    Cette classe fournit des méthodes pour générer des rapports dans
    différents formats (JSON, Markdown, HTML) à partir des résultats
    de benchmark.
    """

    def __init__(self, report: BenchmarkReport) -> None:
        """Initialise le générateur de rapports.

        Args:
            report: Rapport de benchmark à générer
        """
        self.report = report

    def generate_json_report(self) -> dict[str, Any]:
        """Génère un rapport JSON complet.

        Returns:
            Dictionnaire contenant toutes les informations du rapport
        """
        return {
            "metadata": {
                "timestamp": self.report.timestamp,
                "model": self.report.model,
                "total_tests": self.report.total_tests,
            },
            "ollama_only": self._summary_to_dict(self.report.ollama_only),
            "ollama_rag": self._summary_to_dict(self.report.ollama_rag),
            "comparison": self._comparison_to_dict(self.report.comparison),
            "detailed_results": [
                self._result_to_dict(r) for r in self.report.detailed_results
            ],
        }

    def generate_markdown_report(self) -> str:
        """Génère un rapport Markdown lisible.

        Returns:
            Chaîne de caractères contenant le rapport en format Markdown
        """
        lines: list[str] = []

        # Titre et métadonnées
        lines.append("# Rapport de Benchmark - Correction de Configuration HAProxy")
        lines.append("")
        lines.append("## Résumé Exécutif")
        lines.append("")
        lines.append(f"- **Modèle LLM**: {self.report.model}")
        lines.append(f"- **Date du benchmark**: {self.report.timestamp}")
        lines.append(f"- **Nombre total de tests**: {self.report.total_tests}")
        lines.append("")

        # Tableau comparatif principal
        lines.append("## Comparaison Globale")
        lines.append("")
        lines.append(self._create_comparison_table())
        lines.append("")

        # Analyse par catégorie
        lines.append("## Analyse par Catégorie")
        lines.append("")
        lines.append(self._create_category_breakdown())
        lines.append("")

        # Analyse par difficulté
        lines.append("## Analyse par Difficulté")
        lines.append("")
        lines.append(self._create_difficulty_breakdown())
        lines.append("")

        # Cas d'échec et recommandations
        lines.append("## Analyse des Cas d'Échec")
        lines.append("")
        lines.append(self._create_failure_analysis())
        lines.append("")

        # Graphiques ASCII
        lines.append("## Visualisation des Résultats")
        lines.append("")
        lines.append(self._create_ascii_charts())
        lines.append("")

        # Conclusion et recommandations
        lines.append("## Conclusion et Recommandations")
        lines.append("")
        lines.append(self._create_conclusion())
        lines.append("")

        return "\n".join(lines)

    def generate_html_report(self) -> str:
        """Génère un rapport HTML avec graphiques.

        Returns:
            Chaîne de caractères contenant le rapport en format HTML
        """
        html_parts: list[str] = []

        # En-tête HTML
        html_parts.append("<!DOCTYPE html>")
        html_parts.append('<html lang="fr">')
        html_parts.append("<head>")
        html_parts.append("  <meta charset='UTF-8'>")
        html_parts.append(
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        )
        html_parts.append("  <title>Rapport de Benchmark HAProxy</title>")
        html_parts.append("  <style>")
        html_parts.append(self._get_html_styles())
        html_parts.append("  </style>")
        html_parts.append("</head>")
        html_parts.append("<body>")
        html_parts.append("  <div class='container'>")

        # Titre et métadonnées
        html_parts.append(
            "    <h1>Rapport de Benchmark - Correction de Configuration HAProxy</h1>"
        )
        html_parts.append("    <div class='metadata'>")
        html_parts.append(
            f"      <p><strong>Modèle LLM:</strong> {self.report.model}</p>"
        )
        html_parts.append(
            f"      <p><strong>Date:</strong> {self.report.timestamp}</p>"
        )
        html_parts.append(
            f"      <p><strong>Nombre de tests:</strong> {self.report.total_tests}</p>"
        )
        html_parts.append("    </div>")

        # Tableau comparatif
        html_parts.append("    <h2>Comparaison Globale</h2>")
        html_parts.append(self._create_html_comparison_table())

        # Graphiques
        if MATPLOTLIB_AVAILABLE:
            html_parts.append("    <h2>Visualisation des Résultats</h2>")
            html_parts.append(self._create_html_charts())
        else:
            html_parts.append("    <h2>Visualisation (ASCII)</h2>")
            html_parts.append(f"    <pre>{self._create_ascii_charts()}</pre>")

        # Analyse par catégorie
        html_parts.append("    <h2>Analyse par Catégorie</h2>")
        html_parts.append(self._create_html_category_breakdown())

        # Analyse par difficulté
        html_parts.append("    <h2>Analyse par Difficulté</h2>")
        html_parts.append(self._create_html_difficulty_breakdown())

        # Cas d'échec
        html_parts.append("    <h2>Analyse des Cas d'Échec</h2>")
        html_parts.append(self._create_html_failure_analysis())

        # Conclusion
        html_parts.append("    <h2>Conclusion et Recommandations</h2>")
        html_parts.append(
            f"    <div class='conclusion'>{self._create_conclusion()}</div>"
        )

        # Pied de page
        html_parts.append("  </div>")
        html_parts.append("</body>")
        html_parts.append("</html>")

        return "\n".join(html_parts)

    def save_report(
        self,
        output_path: str | Path,
        format: str = "json",
    ) -> None:
        """Sauvegarde le rapport dans un fichier.

        Args:
            output_path: Chemin du fichier de sortie
            format: Format du rapport ('json', 'markdown', 'html')
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            report_data = self.generate_json_report()
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
        elif format == "markdown":
            report_content = self.generate_markdown_report()
            output_path = output_path.with_suffix(".md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        elif format == "html":
            report_content = self.generate_html_report()
            output_path = output_path.with_suffix(".html")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        else:
            msg = f"Format non supporté: {format}"
            raise ValueError(msg)

    # =============================================================================
    # Méthodes de conversion
    # =============================================================================

    def _summary_to_dict(self, summary: BenchmarkSummary) -> dict[str, Any]:
        """Convertit un résumé de benchmark en dictionnaire.

        Args:
            summary: Résumé à convertir

        Returns:
            Dictionnaire contenant les données du résumé
        """
        return {
            "averages": {
                "detection_rate": summary.avg_detection_rate,
                "syntax_compliance": summary.avg_syntax_compliance,
                "optimization_precision": summary.avg_optimization_precision,
                "hallucination_rate": summary.avg_hallucination_rate,
                "global_score": summary.avg_global_score,
                "response_time": summary.avg_response_time,
                "success_rate": summary.success_rate,
            },
            "by_category": {
                cat: {
                    "count": cat_sum.count,
                    "avg_detection_rate": cat_sum.avg_detection_rate,
                    "avg_syntax_compliance": cat_sum.avg_syntax_compliance,
                    "avg_optimization_precision": cat_sum.avg_optimization_precision,
                    "avg_hallucination_rate": cat_sum.avg_hallucination_rate,
                    "avg_global_score": cat_sum.avg_global_score,
                    "avg_response_time": cat_sum.avg_response_time,
                    "success_rate": cat_sum.success_rate,
                }
                for cat, cat_sum in summary.by_category.items()
            },
            "by_difficulty": {
                diff: {
                    "count": diff_sum.count,
                    "avg_detection_rate": diff_sum.avg_detection_rate,
                    "avg_syntax_compliance": diff_sum.avg_syntax_compliance,
                    "avg_optimization_precision": diff_sum.avg_optimization_precision,
                    "avg_hallucination_rate": diff_sum.avg_hallucination_rate,
                    "avg_global_score": diff_sum.avg_global_score,
                    "avg_response_time": diff_sum.avg_response_time,
                    "success_rate": diff_sum.success_rate,
                }
                for diff, diff_sum in summary.by_difficulty.items()
            },
        }

    def _comparison_to_dict(self, comparison: ComparisonSummary) -> dict[str, Any]:
        """Convertit un résumé de comparaison en dictionnaire.

        Args:
            comparison: Comparaison à convertir

        Returns:
            Dictionnaire contenant les données de comparaison
        """
        return {
            "improvements": {
                "detection": comparison.detection_improvement,
                "syntax": comparison.syntax_improvement,
                "optimization": comparison.optimization_improvement,
                "hallucination_reduction": comparison.hallucination_reduction,
                "global_score": comparison.global_score_improvement,
                "time_overhead": comparison.time_overhead,
            },
            "statistical_significance": {
                "is_significant": comparison.is_significant,
                "p_value": comparison.p_value,
            },
        }

    def _result_to_dict(self, result: BenchmarkResult) -> dict[str, Any]:
        """Convertit un résultat de benchmark en dictionnaire.

        Args:
            result: Résultat à convertir

        Returns:
            Dictionnaire contenant les données du résultat
        """
        return {
            "test_id": result.test_id,
            "test_name": result.test_name,
            "category": result.category,
            "difficulty": result.difficulty,
            "metrics": {
                "detection_rate": result.detection_rate,
                "syntax_compliance": result.syntax_compliance,
                "optimization_precision": result.optimization_precision,
                "hallucination_rate": result.hallucination_rate,
                "global_score": result.global_score,
                "response_time": result.response_time,
                "retrieval_time": result.retrieval_time,
                "generation_time": result.generation_time,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            },
            "details": {
                "detected_errors_count": len(result.detected_errors),
                "expected_errors_count": len(result.expected_errors),
                "fixed_config_length": len(result.fixed_config),
                "expected_fixed_config_length": len(result.expected_fixed_config),
            },
            "metadata": {
                "model": result.model,
                "rag_used": result.rag_used,
                "timestamp": result.timestamp,
            },
        }

    # =============================================================================
    # Méthodes de création de tableaux Markdown
    # =============================================================================

    def _create_comparison_table(self) -> str:
        """Crée un tableau comparatif des métriques principales.

        Returns:
            Tableau en format Markdown
        """
        ollama = self.report.ollama_only
        rag = self.report.ollama_rag
        comp = self.report.comparison

        lines: list[str] = []
        lines.append("| Métrique | Ollama Seul | Ollama + RAG | Amélioration |")
        lines.append("|----------|-------------|-------------|--------------|")
        lines.append(
            f"| Taux de détection | {format_score(ollama.avg_detection_rate)} | "
            f"{format_score(rag.avg_detection_rate)} | "
            f"{format_improvement(comp.detection_improvement)} |"
        )
        lines.append(
            f"| Conformité syntaxique | {format_score(ollama.avg_syntax_compliance * 100)} | "
            f"{format_score(rag.avg_syntax_compliance * 100)} | "
            f"{format_improvement(comp.syntax_improvement * 100)} |"
        )
        lines.append(
            f"| Précision optimisation | {format_score(ollama.avg_optimization_precision)} | "
            f"{format_score(rag.avg_optimization_precision)} | "
            f"{format_improvement(comp.optimization_improvement)} |"
        )
        lines.append(
            f"| Taux d'hallucination | {format_score(ollama.avg_hallucination_rate)} | "
            f"{format_score(rag.avg_hallucination_rate)} | "
            f"{format_improvement(-comp.hallucination_reduction)} |"
        )
        lines.append(
            f"| Score global | {format_score(ollama.avg_global_score)} | "
            f"{format_score(rag.avg_global_score)} | "
            f"{format_improvement(comp.global_score_improvement)} |"
        )
        lines.append(
            f"| Taux de réussite | {format_score(ollama.success_rate)} | "
            f"{format_score(rag.success_rate)} | "
            f"{format_improvement(rag.success_rate - ollama.success_rate)} |"
        )
        lines.append(
            f"| Temps de réponse | {ollama.avg_response_time:.3f}s | "
            f"{rag.avg_response_time:.3f}s | "
            f"{format_improvement(comp.time_overhead * 1000)}ms |"
        )

        # Significativité statistique
        if comp.p_value is not None:
            sig_text = "✅ Oui" if comp.is_significant else "❌ Non"
            lines.append(
                f"| Significativité statistique | - | - | {sig_text} (p={comp.p_value:.4f}) |"
            )
        else:
            lines.append(
                "| Significativité statistique | - | - | ⚠️ Non calculé (scipy non disponible) |"
            )

        return "\n".join(lines)

    def _create_category_breakdown(self) -> str:
        """Crée une ventilation des résultats par catégorie.

        Returns:
            Tableau en format Markdown
        """
        ollama = self.report.ollama_only
        rag = self.report.ollama_rag

        lines: list[str] = []

        for category in sorted(ollama.by_category.keys()):
            ollama_cat = ollama.by_category[category]
            rag_cat = rag.by_category.get(category)

            if rag_cat is None:
                continue

            lines.append(f"### Catégorie : {category}")
            lines.append("")
            lines.append(f"- **Nombre de tests**: {ollama_cat.count}")
            lines.append("")
            lines.append("| Métrique | Ollama Seul | Ollama + RAG | Amélioration |")
            lines.append("|----------|-------------|-------------|--------------|")
            lines.append(
                f"| Score global | {format_score(ollama_cat.avg_global_score)} | "
                f"{format_score(rag_cat.avg_global_score)} | "
                f"{format_improvement(rag_cat.avg_global_score - ollama_cat.avg_global_score)} |"
            )
            lines.append(
                f"| Taux de détection | {format_score(ollama_cat.avg_detection_rate)} | "
                f"{format_score(rag_cat.avg_detection_rate)} | "
                f"{format_improvement(rag_cat.avg_detection_rate - ollama_cat.avg_detection_rate)} |"
            )
            lines.append(
                f"| Conformité syntaxique | {format_score(ollama_cat.avg_syntax_compliance * 100)} | "
                f"{format_score(rag_cat.avg_syntax_compliance * 100)} | "
                f"{format_improvement((rag_cat.avg_syntax_compliance - ollama_cat.avg_syntax_compliance) * 100)} |"
            )
            lines.append(
                f"| Taux de réussite | {format_score(ollama_cat.success_rate)} | "
                f"{format_score(rag_cat.success_rate)} | "
                f"{format_improvement(rag_cat.success_rate - ollama_cat.success_rate)} |"
            )
            lines.append("")

        return "\n".join(lines)

    def _create_difficulty_breakdown(self) -> str:
        """Crée une ventilation des résultats par difficulté.

        Returns:
            Tableau en format Markdown
        """
        ollama = self.report.ollama_only
        rag = self.report.ollama_rag

        lines: list[str] = []

        for difficulty in sorted(ollama.by_difficulty.keys()):
            ollama_diff = ollama.by_difficulty[difficulty]
            rag_diff = rag.by_difficulty.get(difficulty)

            if rag_diff is None:
                continue

            lines.append(f"### Difficulté : {difficulty}")
            lines.append("")
            lines.append(f"- **Nombre de tests**: {ollama_diff.count}")
            lines.append("")
            lines.append("| Métrique | Ollama Seul | Ollama + RAG | Amélioration |")
            lines.append("|----------|-------------|-------------|--------------|")
            lines.append(
                f"| Score global | {format_score(ollama_diff.avg_global_score)} | "
                f"{format_score(rag_diff.avg_global_score)} | "
                f"{format_improvement(rag_diff.avg_global_score - ollama_diff.avg_global_score)} |"
            )
            lines.append(
                f"| Taux de détection | {format_score(ollama_diff.avg_detection_rate)} | "
                f"{format_score(rag_diff.avg_detection_rate)} | "
                f"{format_improvement(rag_diff.avg_detection_rate - ollama_diff.avg_detection_rate)} |"
            )
            lines.append(
                f"| Conformité syntaxique | {format_score(ollama_diff.avg_syntax_compliance * 100)} | "
                f"{format_score(rag_diff.avg_syntax_compliance * 100)} | "
                f"{format_improvement((rag_diff.avg_syntax_compliance - ollama_diff.avg_syntax_compliance) * 100)} |"
            )
            lines.append(
                f"| Taux de réussite | {format_score(ollama_diff.success_rate)} | "
                f"{format_score(rag_diff.success_rate)} | "
                f"{format_improvement(rag_diff.success_rate - ollama_diff.success_rate)} |"
            )
            lines.append("")

        return "\n".join(lines)

    def _create_failure_analysis(self) -> str:
        """Crée une analyse des cas d'échec.

        Returns:
            Analyse en format Markdown
        """
        # Identifier les tests échoués
        failed_tests = [
            r
            for r in self.report.detailed_results
            if r.global_score < 60 or r.hallucination_rate > 10
        ]

        if not failed_tests:
            return "✅ Aucun cas d'échec significatif détecté."

        lines: list[str] = []
        lines.append(f"⚠️ **{len(failed_tests)} tests échoués ou problématiques**")
        lines.append("")

        # Regrouper par catégorie
        failures_by_category: dict[str, list[BenchmarkResult]] = {}
        for test in failed_tests:
            if test.category not in failures_by_category:
                failures_by_category[test.category] = []
            failures_by_category[test.category].append(test)

        for category, tests in sorted(failures_by_category.items()):
            lines.append(f"### {category} ({len(tests)} échecs)")
            lines.append("")
            for test in tests[:5]:  # Limiter à 5 par catégorie
                lines.append(
                    f"- **{test.test_name}** (Score: {test.global_score:.1f}%)"
                )
                if test.hallucination_rate > 10:
                    lines.append(
                        f"  - ⚠️ Hallucination élevée: {test.hallucination_rate:.1f}%"
                    )
                if test.global_score < 60:
                    lines.append("  - ⚠️ Score global insuffisant")
                lines.append("")

        # Recommandations
        lines.append("### Recommandations")
        lines.append("")
        if any(t.category == "timeout" for t in failed_tests):
            lines.append(
                "- **Timeouts**: Améliorer la récupération de documentation sur les timeouts"
            )
        if any(t.category == "syntax" for t in failed_tests):
            lines.append(
                "- **Syntaxe**: Enrichir les exemples de syntaxe dans la base RAG"
            )
        if any(t.category == "optimization" for t in failed_tests):
            lines.append(
                "- **Optimisation**: Ajouter plus de cas d'optimisation dans le dataset"
            )
        if any(t.difficulty == "hard" for t in failed_tests):
            lines.append(
                "- **Cas difficiles**: Considérer l'ajout de prompts spécifiques pour les cas complexes"
            )

        return "\n".join(lines)

    def _create_ascii_charts(self) -> str:
        """Crée des graphiques ASCII des résultats.

        Returns:
            Graphiques en format ASCII
        """
        lines: list[str] = []

        # Graphique des scores globaux
        lines.append("### Scores Globaux")
        lines.append("```")
        lines.append(
            create_bar_chart(
                ["Ollama Seul", "Ollama + RAG"],
                [
                    self.report.ollama_only.avg_global_score,
                    self.report.ollama_rag.avg_global_score,
                ],
                max_value=100,
            )
        )
        lines.append("```")
        lines.append("")

        # Graphique des améliorations
        lines.append("### Améliorations par Métrique")
        lines.append("```")
        improvements = [
            self.report.comparison.detection_improvement,
            self.report.comparison.syntax_improvement * 100,
            self.report.comparison.optimization_improvement,
            -self.report.comparison.hallucination_reduction,
            self.report.comparison.global_score_improvement,
        ]
        labels = ["Détection", "Syntaxe", "Optimisation", "Hallucination↓", "Global"]
        lines.append(create_bar_chart(labels, improvements, max_value=30))
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def _create_conclusion(self) -> str:
        """Crée une conclusion et des recommandations.

        Returns:
            Conclusion en format Markdown
        """
        comp = self.report.comparison
        rag = self.report.ollama_rag

        lines: list[str] = []

        # Évaluation globale
        if comp.global_score_improvement > 10:
            lines.append("✅ **RAG apporte une amélioration significative**")
        elif comp.global_score_improvement > 5:
            lines.append("⚠️ **RAG apporte une amélioration modérée**")
        elif comp.global_score_improvement > 0:
            lines.append("📊 **RAG apporte une légère amélioration**")
        else:
            lines.append("❌ **RAG n'apporte pas d'amélioration notable**")

        lines.append("")

        # Points forts
        lines.append("### Points Forts")
        lines.append("")
        if comp.detection_improvement > 5:
            lines.append(
                f"- ✅ Meilleure détection des erreurs (+{comp.detection_improvement:.1f}%)"
            )
        if comp.syntax_improvement > 0.05:
            lines.append(
                f"- ✅ Meilleure conformité syntaxique (+{comp.syntax_improvement * 100:.1f}%)"
            )
        if comp.hallucination_reduction > 5:
            lines.append(
                f"- ✅ Réduction des hallucinations (-{comp.hallucination_reduction:.1f}%)"
            )

        # Points faibles
        lines.append("")
        lines.append("### Points d'Attention")
        lines.append("")
        if comp.time_overhead > 0.5:
            lines.append(f"- ⚠️ Surcoût temporel important (+{comp.time_overhead:.2f}s)")
        if comp.global_score_improvement < 5:
            lines.append("- ⚠️ Amélioration globale limitée")
        if rag.avg_hallucination_rate > 10:
            lines.append(
                f"- ⚠️ Taux d'hallucination encore élevé ({rag.avg_hallucination_rate:.1f}%)"
            )

        # Recommandations finales
        lines.append("")
        lines.append("### Recommandations")
        lines.append("")
        if comp.is_significant:
            lines.append(
                "- ✅ **Utiliser RAG en production** (amélioration statistiquement significative)"
            )
        else:
            lines.append(
                "- ⚠️ **Évaluer l'utilité de RAG** (amélioration non significative)"
            )

        if rag.avg_global_score > 80:
            lines.append(
                "- ✅ Le système atteint un niveau de performance satisfaisant"
            )
        elif rag.avg_global_score > 60:
            lines.append("- ⚠️ Le système nécessite encore des améliorations")
        else:
            lines.append("- ❌ Le système nécessite des améliorations majeures")

        return "\n".join(lines)

    # =============================================================================
    # Méthodes de création de contenu HTML
    # =============================================================================

    def _get_html_styles(self) -> str:
        """Retourne les styles CSS pour le rapport HTML.

        Returns:
            Chaîne CSS
        """
        return """
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: #f5f5f5;
      }
      .container {
        background: white;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      }
      h1 {
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
      }
      h2 {
        color: #34495e;
        margin-top: 30px;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 5px;
      }
      h3 {
        color: #7f8c8d;
      }
      .metadata {
        background: #ecf0f1;
        padding: 15px;
        border-radius: 5px;
        margin: 20px 0;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
      }
      th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
      }
      th {
        background: #3498db;
        color: white;
      }
      tr:hover {
        background: #f5f5f5;
      }
      .positive {
        color: #27ae60;
        font-weight: bold;
      }
      .negative {
        color: #e74c3c;
        font-weight: bold;
      }
      .neutral {
        color: #7f8c8d;
      }
      .chart-container {
        margin: 20px 0;
        padding: 20px;
        background: #fafafa;
        border-radius: 5px;
      }
      .conclusion {
        background: #e8f4f8;
        padding: 15px;
        border-left: 4px solid #3498db;
        border-radius: 3px;
      }
      pre {
        background: #2c3e50;
        color: #ecf0f1;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
      }
    """

    def _create_html_comparison_table(self) -> str:
        """Crée un tableau comparatif en HTML.

        Returns:
            Tableau en format HTML
        """
        ollama = self.report.ollama_only
        rag = self.report.ollama_rag
        comp = self.report.comparison

        rows: list[str] = []
        rows.append("    <table>")
        rows.append("      <thead>")
        rows.append("        <tr>")
        rows.append("          <th>Métrique</th>")
        rows.append("          <th>Ollama Seul</th>")
        rows.append("          <th>Ollama + RAG</th>")
        rows.append("          <th>Amélioration</th>")
        rows.append("        </tr>")
        rows.append("      </thead>")
        rows.append("      <tbody>")

        # Fonction helper pour créer une ligne
        def create_row(
            label: str,
            ollama_val: float,
            rag_val: float,
            improvement: float,
            unit: str = "",
        ) -> str:
            ollama_class = (
                "positive"
                if ollama_val >= 70
                else "negative"
                if ollama_val < 50
                else "neutral"
            )
            rag_class = (
                "positive"
                if rag_val >= 70
                else "negative"
                if rag_val < 50
                else "neutral"
            )
            imp_class = (
                "positive"
                if improvement > 0
                else "negative"
                if improvement < 0
                else "neutral"
            )
            imp_sign = "+" if improvement > 0 else ""

            return f"""        <tr>
          <td>{label}</td>
          <td class="{ollama_class}">{ollama_val:.2f}{unit}</td>
          <td class="{rag_class}">{rag_val:.2f}{unit}</td>
          <td class="{imp_class}">{imp_sign}{improvement:.2f}{unit}</td>
        </tr>"""

        rows.append(
            create_row(
                "Taux de détection",
                ollama.avg_detection_rate,
                rag.avg_detection_rate,
                comp.detection_improvement,
                "%",
            )
        )
        rows.append(
            create_row(
                "Conformité syntaxique",
                ollama.avg_syntax_compliance * 100,
                rag.avg_syntax_compliance * 100,
                comp.syntax_improvement * 100,
                "%",
            )
        )
        rows.append(
            create_row(
                "Précision optimisation",
                ollama.avg_optimization_precision,
                rag.avg_optimization_precision,
                comp.optimization_improvement,
                "%",
            )
        )
        rows.append(
            create_row(
                "Taux d'hallucination",
                ollama.avg_hallucination_rate,
                rag.avg_hallucination_rate,
                -comp.hallucination_reduction,
                "%",
            )
        )
        rows.append(
            create_row(
                "Score global",
                ollama.avg_global_score,
                rag.avg_global_score,
                comp.global_score_improvement,
                "%",
            )
        )
        rows.append(
            create_row(
                "Taux de réussite",
                ollama.success_rate,
                rag.success_rate,
                rag.success_rate - ollama.success_rate,
                "%",
            )
        )

        # Significativité
        if comp.p_value is not None:
            sig_class = "positive" if comp.is_significant else "negative"
            sig_text = "Oui" if comp.is_significant else "Non"
            rows.append(f"""        <tr>
          <td>Significativité</td>
          <td>-</td>
          <td>-</td>
          <td class="{sig_class}">{sig_text} (p={comp.p_value:.4f})</td>
        </tr>""")

        rows.append("      </tbody>")
        rows.append("    </table>")

        return "\n".join(rows)

    def _create_html_charts(self) -> str:
        """Crée des graphiques HTML avec matplotlib.

        Returns:
            Graphiques en format HTML
        """
        if not MATPLOTLIB_AVAILABLE:
            return "<p>Matplotlib non disponible</p>"

        # Créer les graphiques
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(
            "Visualisation des Résultats de Benchmark", fontsize=16, fontweight="bold"
        )

        # Graphique 1: Scores globaux
        ax1 = axes[0, 0]
        models = ["Ollama Seul", "Ollama + RAG"]
        scores = [
            self.report.ollama_only.avg_global_score,
            self.report.ollama_rag.avg_global_score,
        ]
        colors = ["#e74c3c", "#27ae60"]
        bars = ax1.bar(models, scores, color=colors, alpha=0.7)
        ax1.set_ylabel("Score Global (%)")
        ax1.set_title("Scores Globaux par Architecture")
        ax1.set_ylim(0, 100)
        for bar, score in zip(bars, scores):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{score:.1f}%",
                ha="center",
                fontweight="bold",
            )

        # Graphique 2: Améliorations par métrique
        ax2 = axes[0, 1]
        metrics = ["Détection", "Syntaxe", "Optimisation", "Hallucination↓", "Global"]
        improvements = [
            self.report.comparison.detection_improvement,
            self.report.comparison.syntax_improvement * 100,
            self.report.comparison.optimization_improvement,
            -self.report.comparison.hallucination_reduction,
            self.report.comparison.global_score_improvement,
        ]
        colors2 = ["#27ae60" if imp > 0 else "#e74c3c" for imp in improvements]
        bars2 = ax2.bar(metrics, improvements, color=colors2, alpha=0.7)
        ax2.set_ylabel("Amélioration (%)")
        ax2.set_title("Améliorations par Métrique")
        ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        for bar, imp in zip(bars2, improvements):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (0.5 if imp > 0 else -2),
                f"{imp:+.1f}%",
                ha="center",
                fontweight="bold",
            )

        # Graphique 3: Scores par catégorie
        ax3 = axes[1, 0]
        categories = sorted(self.report.ollama_rag.by_category.keys())
        ollama_cat_scores = [
            self.report.ollama_only.by_category[c].avg_global_score for c in categories
        ]
        rag_cat_scores = [
            self.report.ollama_rag.by_category[c].avg_global_score for c in categories
        ]
        x = range(len(categories))
        width = 0.35
        ax3.bar(
            [i - width / 2 for i in x],
            ollama_cat_scores,
            width,
            label="Ollama Seul",
            color="#e74c3c",
            alpha=0.7,
        )
        ax3.bar(
            [i + width / 2 for i in x],
            rag_cat_scores,
            width,
            label="Ollama + RAG",
            color="#27ae60",
            alpha=0.7,
        )
        ax3.set_ylabel("Score Global (%)")
        ax3.set_title("Scores par Catégorie")
        ax3.set_xticks(x)
        ax3.set_xticklabels(categories, rotation=45, ha="right")
        ax3.legend()
        ax3.set_ylim(0, 100)

        # Graphique 4: Taux de réussite
        ax4 = axes[1, 1]
        success_rates = [
            self.report.ollama_only.success_rate,
            self.report.ollama_rag.success_rate,
        ]
        colors4 = ["#e74c3c", "#27ae60"]
        bars4 = ax4.bar(models, success_rates, color=colors4, alpha=0.7)
        ax4.set_ylabel("Taux de Réussite (%)")
        ax4.set_title("Taux de Réussite par Architecture")
        ax4.set_ylim(0, 100)
        for bar, rate in zip(bars4, success_rates):
            ax4.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{rate:.1f}%",
                ha="center",
                fontweight="bold",
            )

        plt.tight_layout()

        # Convertir en base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return f"""    <div class="chart-container">
      <img src="data:image/png;base64,{image_base64}" alt="Graphiques de benchmark" style="max-width: 100%; height: auto;">
    </div>"""

    def _create_html_category_breakdown(self) -> str:
        """Crée une ventilation par catégorie en HTML.

        Returns:
            Tableau en format HTML
        """
        ollama = self.report.ollama_only
        rag = self.report.ollama_rag

        sections: list[str] = []

        for category in sorted(ollama.by_category.keys()):
            ollama_cat = ollama.by_category[category]
            rag_cat = rag.by_category.get(category)

            if rag_cat is None:
                continue

            sections.append(f"    <h3>{category}</h3>")
            sections.append(
                f"    <p><strong>Nombre de tests:</strong> {ollama_cat.count}</p>"
            )
            sections.append("    <table>")
            sections.append("      <thead>")
            sections.append("        <tr>")
            sections.append("          <th>Métrique</th>")
            sections.append("          <th>Ollama Seul</th>")
            sections.append("          <th>Ollama + RAG</th>")
            sections.append("          <th>Amélioration</th>")
            sections.append("        </tr>")
            sections.append("      </thead>")
            sections.append("      <tbody>")

            def create_row(
                label: str, o_val: float, r_val: float, unit: str = ""
            ) -> str:
                imp = r_val - o_val
                imp_class = (
                    "positive" if imp > 0 else "negative" if imp < 0 else "neutral"
                )
                imp_sign = "+" if imp > 0 else ""
                return f"""        <tr>
          <td>{label}</td>
          <td>{o_val:.2f}{unit}</td>
          <td>{r_val:.2f}{unit}</td>
          <td class="{imp_class}">{imp_sign}{imp:.2f}{unit}</td>
        </tr>"""

            sections.append(
                create_row(
                    "Score global",
                    ollama_cat.avg_global_score,
                    rag_cat.avg_global_score,
                    "%",
                )
            )
            sections.append(
                create_row(
                    "Taux de détection",
                    ollama_cat.avg_detection_rate,
                    rag_cat.avg_detection_rate,
                    "%",
                )
            )
            sections.append(
                create_row(
                    "Conformité syntaxique",
                    ollama_cat.avg_syntax_compliance * 100,
                    rag_cat.avg_syntax_compliance * 100,
                    "%",
                )
            )
            sections.append(
                create_row(
                    "Taux de réussite",
                    ollama_cat.success_rate,
                    rag_cat.success_rate,
                    "%",
                )
            )

            sections.append("      </tbody>")
            sections.append("    </table>")

        return "\n".join(sections)

    def _create_html_difficulty_breakdown(self) -> str:
        """Crée une ventilation par difficulté en HTML.

        Returns:
            Tableau en format HTML
        """
        ollama = self.report.ollama_only
        rag = self.report.ollama_rag

        sections: list[str] = []

        for difficulty in sorted(ollama.by_difficulty.keys()):
            ollama_diff = ollama.by_difficulty[difficulty]
            rag_diff = rag.by_difficulty.get(difficulty)

            if rag_diff is None:
                continue

            sections.append(f"    <h3>{difficulty}</h3>")
            sections.append(
                f"    <p><strong>Nombre de tests:</strong> {ollama_diff.count}</p>"
            )
            sections.append("    <table>")
            sections.append("      <thead>")
            sections.append("        <tr>")
            sections.append("          <th>Métrique</th>")
            sections.append("          <th>Ollama Seul</th>")
            sections.append("          <th>Ollama + RAG</th>")
            sections.append("          <th>Amélioration</th>")
            sections.append("        </tr>")
            sections.append("      </thead>")
            sections.append("      <tbody>")

            def create_row(
                label: str, o_val: float, r_val: float, unit: str = ""
            ) -> str:
                imp = r_val - o_val
                imp_class = (
                    "positive" if imp > 0 else "negative" if imp < 0 else "neutral"
                )
                imp_sign = "+" if imp > 0 else ""
                return f"""        <tr>
          <td>{label}</td>
          <td>{o_val:.2f}{unit}</td>
          <td>{r_val:.2f}{unit}</td>
          <td class="{imp_class}">{imp_sign}{imp:.2f}{unit}</td>
        </tr>"""

            sections.append(
                create_row(
                    "Score global",
                    ollama_diff.avg_global_score,
                    rag_diff.avg_global_score,
                    "%",
                )
            )
            sections.append(
                create_row(
                    "Taux de détection",
                    ollama_diff.avg_detection_rate,
                    rag_diff.avg_detection_rate,
                    "%",
                )
            )
            sections.append(
                create_row(
                    "Conformité syntaxique",
                    ollama_diff.avg_syntax_compliance * 100,
                    rag_diff.avg_syntax_compliance * 100,
                    "%",
                )
            )
            sections.append(
                create_row(
                    "Taux de réussite",
                    ollama_diff.success_rate,
                    rag_diff.success_rate,
                    "%",
                )
            )

            sections.append("      </tbody>")
            sections.append("    </table>")

        return "\n".join(sections)

    def _create_html_failure_analysis(self) -> str:
        """Crée une analyse des échecs en HTML.

        Returns:
            Analyse en format HTML
        """
        failed_tests = [
            r
            for r in self.report.detailed_results
            if r.global_score < 60 or r.hallucination_rate > 10
        ]

        if not failed_tests:
            return "<p>✅ Aucun cas d'échec significatif détecté.</p>"

        sections: list[str] = []
        sections.append(
            f"<p>⚠️ <strong>{len(failed_tests)} tests échoués ou problématiques</strong></p>"
        )

        # Regrouper par catégorie
        failures_by_category: dict[str, list[BenchmarkResult]] = {}
        for test in failed_tests:
            if test.category not in failures_by_category:
                failures_by_category[test.category] = []
            failures_by_category[test.category].append(test)

        for category, tests in sorted(failures_by_category.items()):
            sections.append(f"    <h3>{category} ({len(tests)} échecs)</h3>")
            sections.append("    <ul>")
            for test in tests[:5]:
                sections.append(
                    f"      <li><strong>{test.test_name}</strong> (Score: {test.global_score:.1f}%)"
                )
                if test.hallucination_rate > 10:
                    sections.append(
                        f"        <br>⚠️ Hallucination élevée: {test.hallucination_rate:.1f}%"
                    )
                if test.global_score < 60:
                    sections.append("        <br>⚠️ Score global insuffisant")
                sections.append("      </li>")
            sections.append("    </ul>")

        return "\n".join(sections)


# =============================================================================
# Fonctions utilitaires
# =============================================================================


def format_score(score: float) -> str:
    """Formate un score avec couleur/émoji.

    Args:
        score: Score à formater

    Returns:
        Score formaté avec émoji
    """
    if score >= 80:
        return f"🟢 {score:.1f}%"
    elif score >= 60:
        return f"🟡 {score:.1f}%"
    elif score >= 40:
        return f"🟠 {score:.1f}%"
    else:
        return f"🔴 {score:.1f}%"


def format_improvement(value: float) -> str:
    """Formate une amélioration avec signe.

    Args:
        value: Valeur d'amélioration

    Returns:
        Amélioration formatée avec signe et émoji
    """
    if value > 5:
        return f"✅ +{value:.1f}%"
    elif value > 0:
        return f"📈 +{value:.1f}%"
    elif value == 0:
        return f"➡️ {value:.1f}%"
    elif value > -5:
        return f"📉 {value:.1f}%"
    else:
        return f"❌ {value:.1f}%"


def create_comparison_table(
    ollama_only: BenchmarkSummary,
    ollama_rag: BenchmarkSummary,
    comparison: ComparisonSummary,
) -> str:
    """Crée un tableau comparatif des métriques principales.

    Args:
        ollama_only: Résumé des résultats Ollama seul
        ollama_rag: Résumé des résultats Ollama + RAG
        comparison: Résumé de la comparaison

    Returns:
        Tableau en format Markdown
    """
    lines: list[str] = []
    lines.append("| Métrique | Ollama Seul | Ollama + RAG | Amélioration |")
    lines.append("|----------|-------------|-------------|--------------|")
    lines.append(
        f"| Taux de détection | {format_score(ollama_only.avg_detection_rate)} | "
        f"{format_score(ollama_rag.avg_detection_rate)} | "
        f"{format_improvement(comparison.detection_improvement)} |"
    )
    lines.append(
        f"| Conformité syntaxique | {format_score(ollama_only.avg_syntax_compliance * 100)} | "
        f"{format_score(ollama_rag.avg_syntax_compliance * 100)} | "
        f"{format_improvement(comparison.syntax_improvement * 100)} |"
    )
    lines.append(
        f"| Précision optimisation | {format_score(ollama_only.avg_optimization_precision)} | "
        f"{format_score(ollama_rag.avg_optimization_precision)} | "
        f"{format_improvement(comparison.optimization_improvement)} |"
    )
    lines.append(
        f"| Taux d'hallucination | {format_score(ollama_only.avg_hallucination_rate)} | "
        f"{format_score(ollama_rag.avg_hallucination_rate)} | "
        f"{format_improvement(-comparison.hallucination_reduction)} |"
    )
    lines.append(
        f"| Score global | {format_score(ollama_only.avg_global_score)} | "
        f"{format_score(ollama_rag.avg_global_score)} | "
        f"{format_improvement(comparison.global_score_improvement)} |"
    )
    lines.append(
        f"| Taux de réussite | {format_score(ollama_only.success_rate)} | "
        f"{format_score(ollama_rag.success_rate)} | "
        f"{format_improvement(ollama_rag.success_rate - ollama_only.success_rate)} |"
    )

    return "\n".join(lines)


def create_category_breakdown(
    ollama_only: BenchmarkSummary,
    ollama_rag: BenchmarkSummary,
) -> str:
    """Crée une ventilation des résultats par catégorie.

    Args:
        ollama_only: Résumé des résultats Ollama seul
        ollama_rag: Résumé des résultats Ollama + RAG

    Returns:
        Ventilation en format Markdown
    """
    lines: list[str] = []

    for category in sorted(ollama_only.by_category.keys()):
        ollama_cat = ollama_only.by_category[category]
        rag_cat = ollama_rag.by_category.get(category)

        if rag_cat is None:
            continue

        lines.append(f"### {category}")
        lines.append("")
        lines.append(f"- **Nombre de tests**: {ollama_cat.count}")
        lines.append("")
        lines.append("| Métrique | Ollama Seul | Ollama + RAG | Amélioration |")
        lines.append("|----------|-------------|-------------|--------------|")
        lines.append(
            f"| Score global | {format_score(ollama_cat.avg_global_score)} | "
            f"{format_score(rag_cat.avg_global_score)} | "
            f"{format_improvement(rag_cat.avg_global_score - ollama_cat.avg_global_score)} |"
        )
        lines.append(
            f"| Taux de détection | {format_score(ollama_cat.avg_detection_rate)} | "
            f"{format_score(rag_cat.avg_detection_rate)} | "
            f"{format_improvement(rag_cat.avg_detection_rate - ollama_cat.avg_detection_rate)} |"
        )
        lines.append(
            f"| Taux de réussite | {format_score(ollama_cat.success_rate)} | "
            f"{format_score(rag_cat.success_rate)} | "
            f"{format_improvement(rag_cat.success_rate - ollama_cat.success_rate)} |"
        )
        lines.append("")

    return "\n".join(lines)


def create_bar_chart(
    labels: list[str],
    values: list[float],
    max_value: float = 100,
    bar_width: int = 30,
) -> str:
    """Crée un graphique à barres en ASCII.

    Args:
        labels: Étiquettes des barres
        values: Valeurs des barres
        max_value: Valeur maximale pour l'échelle
        bar_width: Largeur maximale des barres en caractères

    Returns:
        Graphique ASCII
    """
    lines: list[str] = []

    # Calculer la largeur de l'étiquette la plus longue
    max_label_length = max(len(label) for label in labels)

    # Créer les barres
    for label, value in zip(labels, values):
        # Calculer la longueur de la barre
        bar_length = int((abs(value) / max_value) * bar_width)
        bar_length = max(1, min(bar_length, bar_width))

        # Déterminer le caractère de la barre
        if value >= 0:
            bar_char = "█"
            sign = "+"
        else:
            bar_char = "░"
            sign = ""

        # Créer la ligne
        bar = bar_char * bar_length
        line = f"{label.ljust(max_label_length)} │ {sign}{value:6.2f} {bar}"
        lines.append(line)

    # Ajouter l'échelle
    lines.append("")
    scale_line = " " * (max_label_length + 2) + "└" + "─" * (bar_width + 8)
    lines.append(scale_line)

    return "\n".join(lines)


# =============================================================================
# Test du module
# =============================================================================

if __name__ == "__main__":
    from haproxy_validator import ValidationError, ErrorType, ErrorSeverity

    # Créer des résultats de benchmark fictifs
    def create_mock_result(
        test_id: str,
        test_name: str,
        category: str,
        difficulty: str,
        rag_used: bool,
    ) -> BenchmarkResult:
        """Crée un résultat de benchmark fictif."""
        return BenchmarkResult(
            test_id=test_id,
            test_name=test_name,
            category=category,
            difficulty=difficulty,
            detection_rate=70.0 if not rag_used else 85.0,
            syntax_compliance=0.75 if not rag_used else 0.90,
            optimization_precision=65.0 if not rag_used else 80.0,
            hallucination_rate=15.0 if not rag_used else 8.0,
            global_score=68.0 if not rag_used else 82.0,
            response_time=1.5 if not rag_used else 2.2,
            retrieval_time=0.0 if not rag_used else 0.3,
            generation_time=1.5 if not rag_used else 1.9,
            input_tokens=1000,
            output_tokens=500,
            detected_errors=[
                ValidationError(
                    line=10,
                    column=0,
                    error_type=ErrorType.SYNTAX,
                    severity=ErrorSeverity.ERROR,
                    message="Invalid directive",
                )
            ],
            expected_errors=[
                {"line": 10, "error_type": "syntax", "message": "Invalid directive"},
                {"line": 15, "error_type": "validation", "message": "Invalid port"},
            ],
            fixed_config="global\n  maxconn 2000\n",
            expected_fixed_config="global\n  maxconn 2000\n",
            model="qwen2.5-coder:7b",
            rag_used=rag_used,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    # Créer des résultats pour Ollama seul
    ollama_results = [
        create_mock_result("test_001", "Test timeout easy", "timeout", "easy", False),
        create_mock_result("test_002", "Test syntax medium", "syntax", "medium", False),
        create_mock_result(
            "test_003", "Test optimization hard", "optimization", "hard", False
        ),
        create_mock_result(
            "test_004", "Test timeout medium", "timeout", "medium", False
        ),
        create_mock_result("test_005", "Test syntax easy", "syntax", "easy", False),
    ]

    # Créer des résultats pour Ollama + RAG
    rag_results = [
        create_mock_result("test_001", "Test timeout easy", "timeout", "easy", True),
        create_mock_result("test_002", "Test syntax medium", "syntax", "medium", True),
        create_mock_result(
            "test_003", "Test optimization hard", "optimization", "hard", True
        ),
        create_mock_result(
            "test_004", "Test timeout medium", "timeout", "medium", True
        ),
        create_mock_result("test_005", "Test syntax easy", "syntax", "easy", True),
    ]

    # Importer les fonctions de génération de résumés
    from bench_config_metrics import (
        generate_summary_from_results,
        generate_comparison_summary,
    )

    # Générer les résumés
    ollama_summary = generate_summary_from_results(ollama_results)
    rag_summary = generate_summary_from_results(rag_results)
    comparison = generate_comparison_summary(
        ollama_summary, rag_summary, ollama_results, rag_results
    )

    # Créer le rapport de benchmark
    benchmark_report = BenchmarkReport(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        model="qwen2.5-coder:7b",
        total_tests=len(ollama_results) + len(rag_results),
        ollama_only=ollama_summary,
        ollama_rag=rag_summary,
        comparison=comparison,
        detailed_results=ollama_results + rag_results,
    )

    # Créer le générateur de rapports
    generator = BenchmarkReportGenerator(benchmark_report)

    # Générer et sauvegarder les rapports
    print("Generation des rapports de benchmark...")

    # Rapport JSON
    json_report = generator.generate_json_report()
    print(f"[OK] Rapport JSON genere avec {len(json_report)} sections")

    # Sauvegarder le rapport JSON
    generator.save_report("test_benchmark_report", format="json")
    print("[OK] Rapport JSON sauvegarde dans test_benchmark_report.json")

    # Rapport Markdown
    md_report = generator.generate_markdown_report()
    print(f"[OK] Rapport Markdown genere ({len(md_report)} caracteres)")

    # Sauvegarder le rapport Markdown
    generator.save_report("test_benchmark_report", format="markdown")
    print("[OK] Rapport Markdown sauvegarde dans test_benchmark_report.md")

    # Rapport HTML
    html_report = generator.generate_html_report()
    print(f"[OK] Rapport HTML genere ({len(html_report)} caracteres)")

    # Sauvegarder le rapport HTML
    generator.save_report("test_benchmark_report", format="html")
    print("[OK] Rapport HTML sauvegarde dans test_benchmark_report.html")

    print("\n[OK] Tous les rapports ont ete generes avec succes!")
