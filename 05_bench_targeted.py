#!/usr/bin/env python3
"""
05_bench_targeted.py - Benchmark V3 ciblé sur des questions spécifiques

Niveaux disponibles :
- quick     : 7 questions (~3 min)
- standard  : 20 questions (~8 min)
- full      : 92 questions (~45 min)

Usage:
    # Questions spécifiques
    uv run python 05_bench_targeted.py --questions full_backend_name,full_server_weight

    # Par niveau (quick, standard, full)
    uv run python 05_bench_targeted.py --level full

    # Modèle personnalisé
    uv run python 05_bench_targeted.py --level quick --model qwen3:latest
"""

import argparse
import json
import sys
import io
import time
import requests

# Import configuration depuis config.py
from config import ollama_config, llm_config

# Fix encoding Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Importer les questions depuis bench_questions.py (module de données)
import importlib.util

spec = importlib.util.spec_from_file_location("bench_questions", "bench_questions.py")
bench_questions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_questions)
QUESTIONS = bench_questions.QUESTIONS
get_questions_by_level = bench_questions.get_questions_by_level


# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_MODEL = llm_config.default_model
OLLAMA_URL = ollama_config.url

SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2.

RÈGLES ABSOLUES :
1. Réponds UNIQUEMENT à partir du contexte entre <context> et </context>
2. Si l'information n'est PAS dans le contexte → dis "Cette information n'est pas dans la documentation fournie"
3. JAMAIS d'invention, JAMAIS de suppositions
4. Cite TOUJOURS la source entre parenthèses : (Source: nom_de_la_section)
5. Pour les exemples de configuration, utilise des blocs de code avec la syntaxe haproxy

STRUCTURE OBLIGATOIRE :
1. Réponse directe (1-2 phrases)
2. Détails techniques
3. Exemple de configuration (si pertinent)
4. Sources utilisées"""


PROMPT_TEMPLATE = """<context>
{context}
</context>

Question : {question}"""


def get_ollama_url() -> str:
    return OLLAMA_URL


def load_retriever_v3():
    """Charge le retriever V3."""
    try:
        from retriever_v3 import retrieve_context_string

        return retrieve_context_string
    except ImportError as e:
        print(f"❌ Erreur import retriever V3: {e}")
        return None


def generate_response(query: str, context: str, model: str) -> tuple[str, float, int]:
    """Génère une réponse avec Ollama."""
    prompt = PROMPT_TEMPLATE.format(context=context, question=query)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    start_time = time.time()

    try:
        response = requests.post(
            f"{get_ollama_url()}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                    "num_predict": 1024,
                },
            },
            timeout=300,
        )
        response.raise_for_status()

        elapsed = time.time() - start_time
        response_data = response.json()
        answer = response_data["message"]["content"]
        tokens = response_data.get("eval_count", 0)

        return answer, elapsed, tokens

    except Exception as e:
        elapsed = time.time() - start_time
        return f"Erreur: {e}", elapsed, 0


def evaluate_answer(answer: str, expected_keywords: list[str], min_length: int) -> dict:
    """Évalue la qualité d'une réponse."""
    answer_lower = answer.lower()
    found_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    keyword_score = len(found_keywords) / len(expected_keywords)
    length_ok = len(answer) >= min_length

    quality_score = (
        keyword_score * 0.6
        + (0.2 if length_ok else 0)
        + (0.2 if len(answer) > 50 else 0)
    )

    return {
        "keyword_score": round(keyword_score, 2),
        "length_ok": length_ok,
        "quality_score": round(quality_score, 2),
        "found_keywords": found_keywords,
        "answer_length": len(answer),
    }


def benchmark_targeted(
    retrieve_func,
    model: str,
    questions: list[dict],
    verbose: bool = False,
) -> dict:
    """Benchmark ciblé sur des questions spécifiques."""
    print(f"\n{'=' * 70}")
    print("🎯 Benchmark V3 CIBLÉ")
    print(f"{'=' * 70}")
    print(f"   Modèle LLM: {model}")
    print(f"   Questions: {len(questions)}")

    results = []
    total_retrieval_time = 0
    total_generation_time = 0

    for i, test in enumerate(questions, 1):
        question_id = test["id"]
        question = test["question"]
        expected = test["expected_keywords"]

        progress_bar = "█" * i + "░" * (len(questions) - i)
        print(f"\n[{progress_bar}] Question {i}/{len(questions)}: {question_id}")
        if verbose:
            print(f"   Question: {question}")

        # Retrieval
        retrieval_start = time.time()
        try:
            context = retrieve_func(question)
        except Exception as e:
            print(f"   ❌ Erreur retrieval: {e}")
            results.append(
                {
                    "question_id": question_id,
                    "error": str(e),
                    "quality_score": 0,
                }
            )
            continue

        retrieval_time = time.time() - retrieval_start
        total_retrieval_time += retrieval_time

        # Génération
        answer, gen_time, tokens = generate_response(question, context, model)
        total_generation_time += gen_time

        # Évaluation
        eval_result = evaluate_answer(answer, expected, test["min_length"])

        # Affichage
        status = (
            "✅"
            if eval_result["quality_score"] > 0.7
            else "⚠️"
            if eval_result["quality_score"] > 0.4
            else "❌"
        )
        print(f"   {status} Qualité: {eval_result['quality_score']:.2f}/1.0")
        print(f"   ⏱️  Retrieval: {retrieval_time:.2f}s | Génération: {gen_time:.1f}s")
        print(f"   🎯 Keywords: {len(eval_result['found_keywords'])}/{len(expected)}")
        if verbose and eval_result["found_keywords"]:
            print(f"   📝 Trouvés: {', '.join(eval_result['found_keywords'])}")

        results.append(
            {
                "question_id": question_id,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "retrieval_time": round(retrieval_time, 2),
                "generation_time": round(gen_time, 2),
                **eval_result,
            }
        )

    # Stats
    valid_results = [r for r in results if "error" not in r]
    avg_quality = (
        sum(r["quality_score"] for r in valid_results) / len(valid_results)
        if valid_results
        else 0
    )
    questions_resolues = sum(1 for r in valid_results if r["quality_score"] > 0.7)
    taux_reussite = (
        (questions_resolues / len(valid_results) * 100) if valid_results else 0
    )

    return {
        "index": "V3",
        "model": model,
        "questions_tested": len(questions),
        "results": results,
        "stats": {
            "avg_quality": round(avg_quality, 3),
            "questions_resolues": questions_resolues,
            "taux_reussite": round(taux_reussite, 1),
        },
    }


def generate_report(
    benchmark: dict, output_file: str = "bench_v3_targeted_report.json"
):
    """Génère un rapport."""
    stats = benchmark["stats"]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Rapport sauvegardé: {output_file}\n")

    print("=" * 70)
    print("📈 RÉSULTATS BENCHMARK V3 CIBLÉ")
    print("=" * 70)

    print(f"\n🎯 Modèle LLM: {benchmark['model']}")
    print(f"📝 Questions: {benchmark['questions_tested']}")

    print("\n" + "-" * 70)
    print(f"{'Métrique':<30} | {'Valeur':<15}")
    print("-" * 70)
    print(f"{'Qualité moyenne':<30} | {stats['avg_quality']:<15.3f}/1.0")
    print(
        f"{'Questions résolues':<30} | {stats['questions_resolues']}/{benchmark['questions_tested']:<14}"
    )
    print(f"{'Taux de réussite':<30} | {stats['taux_reussite']:<15.1f}%")
    print("-" * 70)

    # Interprétation
    print("\n" + "=" * 70)
    print("💡 INTERPRÉTATION")
    print("=" * 70)

    if stats["avg_quality"] >= 0.90:
        print("✅ EXCELLENT - Qualité >= 0.90/1.0")
    elif stats["avg_quality"] >= 0.80:
        print("✅ TRÈS BON - Qualité >= 0.80/1.0")
    elif stats["avg_quality"] >= 0.70:
        print("⚠️  BON - Qualité >= 0.70/1.0")
    else:
        print("❌ MOYEN - Qualité < 0.70/1.0")

    if stats["taux_reussite"] >= 80:
        print(
            f"✅ {stats['taux_reussite']:.1f}% des questions résolues (objectif >= 80%)"
        )
    else:
        print(
            f"⚠️  {stats['taux_reussite']:.1f}% des questions résolues (objectif >= 80%)"
        )

    # Questions ratées
    failed = [r for r in benchmark["results"] if r.get("quality_score", 0) <= 0.7]
    if failed:
        print(
            f"\n⚠️  Questions à améliorer ({len(failed)}/{benchmark['questions_tested']}):"
        )
        for r in failed:
            print(f"   - {r['question_id']}: {r.get('quality_score', 0):.2f}/1.0")

    # Comparaison
    print("\n" + "=" * 70)
    print("📊 COMPARAISON AVEC AVANT")
    print("=" * 70)
    print("Avant (V2) : backend=0.00, weight=0.20")
    print(
        f"Après (V3) : {stats['avg_quality']:.3f} ({stats['taux_reussite']:.1f}% résolues)"
    )

    if stats["avg_quality"] > 0.70:
        print("\n✅ AMÉLIORATION CONFIRMÉE !")
    else:
        print("\n⚠️  Amélioration insuffisante")


def main():
    parser = argparse.ArgumentParser(description="Benchmark V3 ciblé")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Modèle LLM (défaut: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--questions",
        type=str,
        default="",
        help="Questions à tester (comma-separated)",
    )
    parser.add_argument(
        "--level",
        type=str,
        choices=["quick", "standard", "full"],
        default="",
        help="Niveau de benchmark (quick=7, standard=20, full=92 questions)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bench_v3_targeted_report.json",
        help="Fichier de rapport",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Afficher plus de détails",
    )

    args = parser.parse_args()

    # Vérifier Ollama
    print("🔍 Vérification d'Ollama...", flush=True)
    try:
        response = requests.get(f"{get_ollama_url()}/api/tags", timeout=10)
        response.raise_for_status()
        available_models = [m["name"] for m in response.json().get("models", [])]
        print(f"✅ {len(available_models)} modèles disponibles\n", flush=True)

        if args.model not in available_models:
            print(f"⚠️  Modèle '{args.model}' non disponible", flush=True)
            sys.exit(1)

    except Exception as e:
        print(f"❌ Ollama inaccessible: {e}", flush=True)
        sys.exit(1)

    # Charger retriever
    print("📥 Chargement du retriever V3...", flush=True)
    retrieve_v3 = load_retriever_v3()

    if not retrieve_v3:
        print("❌ Impossible de charger le retriever V3", flush=True)
        sys.exit(1)

    print("✅ Retriever V3 chargé\n", flush=True)

    # Sélectionner les questions
    questions_to_test = []

    if args.level:
        # Utiliser un niveau prédéfini
        questions_to_test = get_questions_by_level(args.level)
        print(
            f"📋 Niveau: {args.level.upper()} ({len(questions_to_test)} questions)",
            flush=True,
        )
    elif args.questions:
        # Questions spécifiques
        question_ids = [q.strip() for q in args.questions.split(",")]
        questions_to_test = [q for q in QUESTIONS if q["id"] in question_ids]
        print(f"📋 Questions ciblées: {len(questions_to_test)}", flush=True)
        for q in questions_to_test:
            print(f"   - {q['id']} ({q['category']})", flush=True)
    else:
        print("❌ Spécifiez --level (quick/standard/full) ou --questions", flush=True)
        print("\nExemples:")
        print("  uv run python 05_bench_targeted.py --level quick")
        print("  uv run python 05_bench_targeted.py --level full")
        print(
            "  uv run python 05_bench_targeted.py --questions full_backend_name,full_server_weight"
        )
        sys.exit(1)

    print(f"📋 Modèle LLM: {args.model}", flush=True)
    print(f"⏱️  Temps estimé: ~{len(questions_to_test) * 25:.0f}s\n", flush=True)

    # Benchmark
    try:
        result = benchmark_targeted(
            retrieve_v3, args.model, questions_to_test, args.verbose
        )
    except Exception as e:
        print(f"\n❌ Erreur benchmark: {e}", flush=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Rapport
    generate_report(result, args.output)

    print("\n✅ Benchmark V3 ciblé terminé !\n", flush=True)


if __name__ == "__main__":
    main()
