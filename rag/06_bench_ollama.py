#!/usr/bin/env python3
"""
06_bench_ollama.py - Benchmark de modèles Ollama pour RAG HAProxy

Teste plusieurs modèles avec les mêmes questions et compare :
- Qualité des réponses (keywords trouvés, pertinence)
- Vitesse (tokens/seconde, temps total)
- Utilisation mémoire (taille du modèle)

Usage:
    uv run python 06_bench_ollama.py
    uv run python 06_bench_ollama.py --models gemma3:latest,qwen3:latest
    uv run python 06_bench_ollama.py --all  # Tous les modèles disponibles
"""

import argparse
import json
import os
import sys
import time
import io

# Fix encoding Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests

from config import ollama_config, benchmark_config


# ── Questions de test ─────────────────────────────────────────────────────────
TEST_QUESTIONS = [
    {
        "id": "healthcheck",
        "question": "Comment configurer un health check HTTP dans HAProxy ?",
        "expected_keywords": ["option httpchk", "check", "GET", "http-check", "server"],
        "min_length": 200,  # Longueur minimale attendue
    },
    {
        "id": "bind",
        "question": "Quelle est la syntaxe de la directive bind ?",
        "expected_keywords": ["bind", "port", "ssl", "crt", "frontend"],
        "min_length": 150,
    },
    {
        "id": "stick_table",
        "question": "Comment limiter les connexions par IP avec stick-table ?",
        "expected_keywords": ["stick-table", "conn_rate", "track-sc", "deny", "ip"],
        "min_length": 200,
    },
]


# ── Modèles à tester ──────────────────────────────────────────────────────────
# Modèles de génération de texte (pas d'embedding, pas d'OCR, pas de vision)
# Utiliser les modèles par défaut depuis config.py
DEFAULT_MODELS = benchmark_config.default_benchmark_models

# Modèles à exclure (embedding, OCR, etc.)
EXCLUDED_PATTERNS = [
    "embed",  # bge-m3, mxbai-embed, qwen3-embedding, nomic-embed
    "ocr",  # glm-ocr
]


# ── Prompt système (identique pour tous) ─────────────────────────────────────
SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2.

CONSIGNES :
- Réponds UNIQUEMENT avec le contexte fourni
- Sois factuel et précis
- Utilise des exemples de configuration si pertinent
- Français uniquement
- Structure ta réponse

<context>
[Source: 5.2. Server and default-server options]
option httpchk - Enable HTTP protocol to check server health

Syntax: option httpchk [<method> <uri> [<version>]]

When this option is set, a server which returns an HTTP code 2xx or 3xx 
is considered alive, otherwise it is considered dead.

Example:
backend web_servers
    option httpchk GET /health HTTP/1.1
    server web1 192.168.1.1:80 check

[Source: 4.2. Alphabetically sorted keywords reference]
bind - Define listening address and port

Syntax: bind [ip_addr]:port [ssl crt /path/to/cert.pem]

Example:
frontend http
    bind *:80
    bind *:443 ssl crt /etc/ssl/cert.pem

[Source: 11.1. stick-table declaration]
stick-table - Declare a stick table for tracking

Syntax: stick-table type ip size <entries> expire <time> store <counters>

Example:
frontend http
    stick-table type ip size 100k expire 30s store conn_rate(10s)
    http-request track-sc0 src
    http-request deny if { sc0_conn_rate gt 100 }
</context>"""


def list_available_models() -> list[str]:
    """Liste les modèles disponibles dans Ollama (filtre embedding/OCR)."""
    try:
        response = requests.get(f"{ollama_config.url}/api/tags", timeout=10)
        response.raise_for_status()
        all_models = [m["name"] for m in response.json().get("models", [])]

        # Filtrer les modèles non pertinents
        filtered_models = []
        for model in all_models:
            # Garder lfm2.5-thinking même si contient 'bf16'
            if "lfm2.5-thinking" in model:
                filtered_models.append(model)
                continue

            # Exclure les patterns non pertinents
            if any(pattern in model.lower() for pattern in EXCLUDED_PATTERNS):
                continue

            filtered_models.append(model)

        return filtered_models
    except Exception as e:
        print(f"❌ Erreur liste modèles: {e}")
        return []


def unload_model() -> bool:
    """Décharge le modèle courant pour libérer le GPU."""
    try:
        # Ollama décharge automatiquement les modèles après inactivité
        # On peut forcer avec un appel vide
        requests.post(
            f"{ollama_config.url}/api/generate",
            json={"model": "", "prompt": ""},
            timeout=5,
        )
        return True
    except Exception:
        pass

    # Alternative: tuer le processus Ollama (radical)
    print("   ⚠️  Attente 10s pour libération GPU...")
    time.sleep(10)
    return True


def load_model(model_name: str) -> bool:
    """Charge le modèle en mémoire (warm-up)."""
    print(f"   📥 Chargement de {model_name}...")
    try:
        # Petit appel pour charger le modèle
        response = requests.post(
            f"{ollama_config.url}/api/generate",
            json={
                "model": model_name,
                "prompt": "Hello",
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        print(f"   ✅ {model_name} chargé")
        return True
    except Exception as e:
        print(f"   ❌ Erreur chargement: {e}")
        return False


def is_gguf_model(model_name: str) -> bool:
    """Vérifie si le modèle est au format GGUF."""
    return "GGUF" in model_name or "gguf" in model_name.lower()


def benchmark_model(
    model_name: str,
    questions: list[dict],
) -> dict:
    """
    Benchmark d'un modèle.

    Returns:
        dict avec stats: temps, tokens, qualité, etc.
    """
    print(f"\n{'=' * 60}")
    print(f"🔍 Benchmark: {model_name}")
    print(f"{'=' * 60}")

    # Charger le modèle
    if not load_model(model_name):
        return {"error": "Failed to load model"}

    results = []
    total_tokens = 0
    total_time = 0

    for i, test in enumerate(questions, 1):
        question_id = test["id"]
        question = test["question"]
        expected = test["expected_keywords"]

        print(f"\n  Question {i}/{len(questions)}: {question_id}")

        # Messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        # Benchmark
        start_time = time.time()

        try:
            # Les modèles GGUF utilisent l'endpoint /api/generate
            if is_gguf_model(model_name):
                # Construire un prompt simple pour GGUF
                prompt = f"System: {SYSTEM_PROMPT}\n\nUser: {question}\n\nAssistant:"
                response = requests.post(
                    f"{ollama_config.url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
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
                response_data = response.json()
                answer = response_data.get("response", "")
            else:
                # Format standard pour les modèles natifs Ollama
                response = requests.post(
                    f"{ollama_config.url}/api/chat",
                    json={
                        "model": model_name,
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
                response_data = response.json()
                answer = response_data["message"]["content"]

            # Stats
            elapsed = time.time() - start_time
            tokens = response_data.get("eval_count", 0)
            total_tokens += tokens
            total_time += elapsed

            # Tokens/seconde
            tokens_per_sec = tokens / elapsed if elapsed > 0 else 0

            # Qualité
            answer_lower = answer.lower()
            found_keywords = [kw for kw in expected if kw.lower() in answer_lower]
            keyword_score = len(found_keywords) / len(expected)

            # Longueur
            length_ok = len(answer) >= test["min_length"]

            # Score global
            quality_score = (
                keyword_score * 0.6
                + (0.2 if length_ok else 0)
                + (0.2 if tokens > 50 else 0)
            )

            result = {
                "question_id": question_id,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "answer_length": len(answer),
                "elapsed": elapsed,
                "tokens": tokens,
                "tokens_per_sec": round(tokens_per_sec, 2),
                "keyword_score": round(keyword_score, 2),
                "found_keywords": found_keywords,
                "quality_score": round(quality_score, 2),
            }
            results.append(result)

            # Affichage
            status = (
                "✅" if quality_score > 0.7 else "⚠️" if quality_score > 0.4 else "❌"
            )
            print(f"    {status} Qualité: {quality_score:.2f}")
            print(
                f"    ⏱️  Temps: {elapsed:.2f}s | Tokens: {tokens} | {tokens_per_sec:.1f} tok/s"
            )
            print(f"    🎯 Keywords: {len(found_keywords)}/{len(expected)}")

        except Exception as e:
            print(f"    ❌ Erreur: {e}")
            results.append(
                {
                    "question_id": question_id,
                    "error": str(e),
                    "quality_score": 0,
                }
            )

    # Décharger le modèle
    unload_model()

    # Stats globales
    avg_quality = sum(r.get("quality_score", 0) for r in results) / len(results)
    avg_time = sum(r.get("elapsed", 0) for r in results if "elapsed" in r) / max(
        1, len([r for r in results if "elapsed" in r])
    )
    avg_tokens_per_sec = total_tokens / total_time if total_time > 0 else 0

    return {
        "model": model_name,
        "results": results,
        "stats": {
            "avg_quality": round(avg_quality, 2),
            "avg_time": round(avg_time, 2),
            "avg_tokens_per_sec": round(avg_tokens_per_sec, 1),
            "total_tokens": total_tokens,
            "total_time": round(total_time, 2),
        },
    }


def generate_report(benchmarks: list[dict], output_file: str = "bench_report.json"):
    """Génère un rapport JSON et texte."""

    # Filtrer les erreurs
    valid_benchmarks = [b for b in benchmarks if "error" not in b]

    if not valid_benchmarks:
        print("\n❌ Aucun benchmark valide")
        return

    # Classement par qualité
    ranking_quality = sorted(
        valid_benchmarks,
        key=lambda x: x["stats"]["avg_quality"],
        reverse=True,
    )

    # Classement par vitesse
    ranking_speed = sorted(
        valid_benchmarks,
        key=lambda x: x["stats"]["avg_tokens_per_sec"],
        reverse=True,
    )

    # Rapport JSON
    report_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models_tested": len(valid_benchmarks),
        "ranking_quality": [
            {
                "model": b["model"],
                "avg_quality": b["stats"]["avg_quality"],
                "avg_time": b["stats"]["avg_time"],
                "tokens_per_sec": b["stats"]["avg_tokens_per_sec"],
            }
            for b in ranking_quality
        ],
        "ranking_speed": [
            {
                "model": b["model"],
                "tokens_per_sec": b["stats"]["avg_tokens_per_sec"],
                "avg_quality": b["stats"]["avg_quality"],
            }
            for b in ranking_speed
        ],
        "all_results": benchmarks,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Rapport sauvegardé: {output_file}")

    # Rapport texte
    print("\n" + "=" * 70)
    print("📈 CLASSEMENT PAR QUALITÉ")
    print("=" * 70)

    for i, entry in enumerate(ranking_quality, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        print(f"{medal} {i}. {entry['model']}")
        print(
            f"     Qualité: {entry['avg_quality']:.2f}/1.0 | "
            f"Temps: {entry['avg_time']:.2f}s | "
            f"Vitesse: {entry['tokens_per_sec']:.1f} tok/s"
        )

    print("\n" + "=" * 70)
    print("⚡ CLASSEMENT PAR VITESSE")
    print("=" * 70)

    for i, entry in enumerate(ranking_speed, 1):
        medal = "🚀" if i == 1 else "  "
        print(f"{medal} {i}. {entry['model']}")
        print(
            f"     Vitesse: {entry['tokens_per_sec']:.1f} tok/s | "
            f"Qualité: {entry['avg_quality']:.2f}/1.0"
        )

    # Recommandations
    print("\n" + "=" * 70)
    print("💡 RECOMMANDATIONS")
    print("=" * 70)

    best_quality = ranking_quality[0]
    best_speed = ranking_speed[0]

    print(f"✅ Meilleure qualité: {best_quality['model']}")
    print(f"⚡ Meilleure vitesse: {best_speed['model']}")

    # Compromis qualité/vitesse
    best_compromise = max(
        valid_benchmarks,
        key=lambda x: x["stats"]["avg_quality"] * x["stats"]["avg_tokens_per_sec"],
    )
    print(f"🎯 Meilleur compromis: {best_compromise['model']}")

    if best_quality["avg_quality"] < 0.6:
        print("\n⚠️  Tous les modèles ont des scores < 0.6")
        print("   → Essayez un modèle plus grand ou fine-tunez")


def main():
    parser = argparse.ArgumentParser(description="Benchmark de modèles Ollama")
    parser.add_argument(
        "--models",
        type=str,
        default=",".join(DEFAULT_MODELS),
        help="Modèles à tester (comma-separated)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Tester tous les modèles disponibles",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="bench_report.json",
        help="Fichier de rapport",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Afficher les réponses complètes",
    )

    args = parser.parse_args()

    # Vérifier Ollama
    print("🔍 Vérification d'Ollama...")
    try:
        response = requests.get(f"{ollama_config.url}/api/tags", timeout=10)
        response.raise_for_status()
        available_models = [m["name"] for m in response.json().get("models", [])]
        print(f"✅ {len(available_models)} modèles disponibles")
    except Exception as e:
        print(f"❌ Ollama inaccessible: {e}")
        print("   Lancez: ollama serve")
        sys.exit(1)

    # Sélection des modèles
    if args.all:
        models_to_test = available_models
    else:
        models_to_test = [m.strip() for m in args.models.split(",")]
        # Filtrer les modèles indisponibles
        models_to_test = [m for m in models_to_test if m in available_models]

    if not models_to_test:
        print("❌ Aucun modèle à tester")
        sys.exit(1)

    print(f"\n📋 Modèles à tester: {models_to_test}")
    print(f"📝 Questions: {len(TEST_QUESTIONS)}")

    # Benchmarks
    benchmarks = []
    for model in models_to_test:
        try:
            result = benchmark_model(model, TEST_QUESTIONS)
            benchmarks.append(result)
        except Exception as e:
            print(f"\n❌ Erreur pour {model}: {e}")
            benchmarks.append(
                {
                    "model": model,
                    "error": str(e),
                    "results": [],
                    "stats": {"avg_quality": 0, "avg_time": 0, "avg_tokens_per_sec": 0},
                }
            )

    # Rapport
    generate_report(benchmarks, args.output)

    print("\n✅ Benchmark terminé !")


if __name__ == "__main__":
    main()
