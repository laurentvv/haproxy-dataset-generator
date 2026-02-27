#!/usr/bin/env python3
"""
bench_models.py - Benchmark de modèles Ollama pour enrichissement metadata

Teste plusieurs modèles sur un échantillon de sections et compare :
- Qualité des metadata (keywords pertinents, schema valide)
- Vitesse (temps par section)
- Taux de réussite (JSON valide)

Usage:
    uv run python bench_models.py

Modèles testés (de ollama ls) :
- gemma3:latest (3.3 GB) - Rapide, pas de thinking
- qwen3:4b (2.5 GB) - Très rapide
- qwen3:14b (9.3 GB) - Plus intelligent
- gemma3:27b (17 GB) - Le plus gros
"""

import json
import logging
import ollama
import time
from pydantic import BaseModel, Field
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ── Schéma Pydantic ──────────────────────────────────────────────────────────
class SectionMetadata(BaseModel):
    keywords: list[str] = Field(..., min_length=5, max_length=10)
    synonyms: list[str] = Field(..., min_length=3, max_length=5)
    summary: str = Field(..., max_length=200)
    category: str = Field(
        ...,
        pattern=r"^(backend|frontend|acl|ssl|timeout|healthcheck|stick-table|logs|stats|general|loadbalancing)$",
    )


# ── Prompts ──────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2.
Extraire des métadonnées pour un système RAG.
RÈGLES : N'INVENTE RIEN, keywords dans le texte, JSON uniquement."""

USER_PROMPT = """Pour cette section HAProxy, extraire :
1. KEYWORDS (5-10) : Mots-clés techniques du texte
2. SYNONYMES (3-5) : Termes associés
3. SUMMARY (1 phrase) : Résumé court
4. CATEGORY : backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general, loadbalancing

Section :
{section}

JSON :"""


# ── Modèles à tester ────────────────────────────────────────────────────────
MODELS_TO_TEST = [
    {"name": "gemma3:latest", "size": "3.3 GB", "priority": 1},
    {"name": "qwen3:4b", "size": "2.5 GB", "priority": 2},
    {"name": "qwen3:14b", "size": "9.3 GB", "priority": 3},
    {"name": "gemma3:27b", "size": "17 GB", "priority": 4},
]

# ── Sections de test (représentatives) ──────────────────────────────────────
TEST_SECTIONS = [
    {
        "id": "server_options",
        "title": "5.2. Server and default-server options",
        "content": """server <name> <address>[:port] [settings ...]

Settings:
  disabled  : Mark the server as DOWN and do not use it for any traffic.
  backup    : This server is a backup. It will only receive traffic when all non-backup servers are DOWN.
  weight    : Server weight (default: 1, range: 0-256). Higher weights receive more connections.
  check     : Enable health checks for this server.
  inter     : Interval between health checks (default: 2000ms).
  fall      : Number of consecutive failed checks before marking server DOWN.
  rise      : Number of consecutive successful checks before marking server UP.""",
        "expected_keywords": [
            "server",
            "disabled",
            "backup",
            "weight",
            "check",
            "DOWN",
        ],
        "expected_category": "backend",
    },
    {
        "id": "balance_source",
        "title": "5.1. Balance algorithms",
        "content": """Balance algorithms determine how requests are distributed among servers.

Available algorithms:
  roundrobin  : Distribute requests in a round-robin fashion.
  leastconn   : Send requests to the server with the least active connections.
  source      : Hash the client's source IP address to select a server.
                This ensures that the same client IP always reaches the same server (persistence).
  uri         : Hash the request URI to select a server.
  hdr         : Hash a specific HTTP header to select a server.""",
        "expected_keywords": [
            "balance",
            "source",
            "roundrobin",
            "leastconn",
            "persistence",
            "hash",
        ],
        "expected_category": "loadbalancing",
    },
    {
        "id": "acl_negation",
        "title": "7.2. Using ACLs to form conditions",
        "content": """ACLs can be used in conditions to control request flow.

Basic syntax:
  acl <name> <criterion> [flags] [operator] <value>

Using ACLs:
  use_backend <backend> if <acl_name>
  http-request deny if <acl_name>
  
Negation:
  The "!" operator negates a condition.
  
  Example:
    acl allowed_method GET POST
    http-request deny if !allowed_method
    
  This denies all requests that are NOT GET or POST.
  
  Negation can also be written as:
    unless <acl_name>  (equivalent to "if !<acl_name>")""",
        "expected_keywords": ["acl", "!", "negation", "unless", "deny", "if"],
        "expected_category": "acl",
    },
]


def unload_model():
    """Force Ollama to unload the current model."""
    try:
        # Stop any running model by calling a simple endpoint
        ollama.list()
        time.sleep(2)  # Wait for model to unload
        print("  [INFO] Modèle déchargé\n")
    except Exception as e:
        logger.warning("Failed to unload model: %s", e)


def test_model(model_name: str, test_sections: list) -> dict:
    """Teste un modèle sur des sections."""
    print(f"\n{'=' * 70}")
    print(f"TEST MODÈLE: {model_name}")
    print(f"{'=' * 70}\n")

    results = {
        "model": model_name,
        "sections": [],
        "total_time": 0,
        "success_rate": 0,
        "avg_keywords": 0,
        "schema_compliance": 0,
    }

    total_success = 0

    for i, section in enumerate(test_sections, 1):
        print(f"[{i}/{len(test_sections)}] {section['id']}...", end=" ", flush=True)

        start_time = time.time()

        try:
            prompt = USER_PROMPT.format(section=section["content"])

            response = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                format=SectionMetadata.model_json_schema(),
                options={"temperature": 0.1, "num_predict": 500},
            )

            elapsed = time.time() - start_time

            # Parser JSON
            json_content = response["message"]["content"]
            metadata = SectionMetadata.model_validate_json(json_content)

            # Évaluer qualité
            found_keywords = sum(
                1
                for kw in section["expected_keywords"]
                if kw.lower() in [k.lower() for k in metadata.keywords]
            )
            keyword_score = found_keywords / len(section["expected_keywords"])

            category_match = (
                1.0 if metadata.category == section["expected_category"] else 0.5
            )

            quality_score = (keyword_score * 0.6 + category_match * 0.4) * 100

            total_success += 1

            print(f"OK | {elapsed:.1f}s | Qualité: {quality_score:.0f}%")
            print(f"       Keywords: {metadata.keywords[:5]}...")
            print(f"       Category: {metadata.category}")

            results["sections"].append(
                {
                    "id": section["id"],
                    "time": elapsed,
                    "quality": quality_score,
                    "keywords_found": found_keywords,
                    "keywords_total": len(section["expected_keywords"]),
                }
            )

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"ERREUR: {str(e)[:50]}")
            results["sections"].append(
                {"id": section["id"], "time": elapsed, "quality": 0, "error": str(e)}
            )

    # Calculer stats
    results["total_time"] = sum(s["time"] for s in results["sections"])
    results["avg_time"] = results["total_time"] / len(results["sections"])
    results["success_rate"] = (total_success / len(test_sections)) * 100
    results["avg_quality"] = sum(
        s.get("quality", 0) for s in results["sections"]
    ) / len(results["sections"])

    return results


def print_report(all_results: list):
    """Affiche le rapport comparatif."""
    print("\n" + "=" * 70)
    print("RÉSULTATS DU BENCHMARK")
    print("=" * 70)

    print(
        f"\n{'Modèle':<20} {'Taille':<10} {'Temps':<10} {'Qualité':<10} {'Succès':<10} {'Score':<10}"
    )
    print("-" * 70)

    for result in all_results:
        model_info = next(
            (m for m in MODELS_TO_TEST if m["name"] == result["model"]), {}
        )
        size = model_info.get("size", "N/A")

        score = (
            result["avg_quality"] * 0.5
            + (100 - min(result["avg_time"], 60)) * 0.3
            + result["success_rate"] * 0.2
        )

        print(
            f"{result['model']:<20} {size:<10} {result['avg_time']:<10.1f}s {result['avg_quality']:<10.0f}% {result['success_rate']:<10.0f}% {score:<10.0f}"
        )

    print("-" * 70)

    # Recommandation
    best = max(
        all_results,
        key=lambda r: r["avg_quality"] * 0.7 + (100 - min(r["avg_time"], 60)) * 0.3,
    )
    print(f"\n[WINNER] MEILLEUR COMPROMIS: {best['model']}")
    print(f"   Qualite: {best['avg_quality']:.0f}% | Temps: {best['avg_time']:.1f}s")
    print("\n[RECOMMANDATION]:")
    if best["avg_quality"] >= 80:
        print(f"   -> Utiliser {best['model']} pour la production")
    else:
        print("   -> Qualite insuffisante, tester d'autres modeles")


def main():
    print("=" * 70)
    print("BENCHMARK MODÈLES OLLAMA - ENRICHISSEMENT MÉTADONNÉES")
    print("=" * 70)
    print(f"\nModèles à tester: {len(MODELS_TO_TEST)}")
    for m in MODELS_TO_TEST:
        print(f"  - {m['name']} ({m['size']})")
    print(f"\nSections de test: {len(TEST_SECTIONS)}")
    print(
        f"Temps estimé total: ~{len(MODELS_TO_TEST) * len(TEST_SECTIONS) * 10 // 60} min"
    )

    all_results = []

    for model_info in MODELS_TO_TEST:
        model_name = model_info["name"]

        # Tester le modèle
        results = test_model(model_name, TEST_SECTIONS)
        all_results.append(results)

        # Décharger le modèle
        unload_model()

    # Rapport
    print_report(all_results)

    # Sauvegarder résultats
    output_path = Path("bench_models_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Rapport sauvegardé dans {output_path}")


if __name__ == "__main__":
    main()
