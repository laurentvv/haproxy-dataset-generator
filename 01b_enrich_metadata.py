#!/usr/bin/env python3
"""
01b_enrich_metadata.py - Enrichissement IA des sections HAProxy

Entree  : data/sections.jsonl
Sortie  : data/sections_enriched.jsonl

Pour chaque section, l'IA génère :
- keywords (5-10 mots-clés)
- synonyms (3-5 synonymes/termes associés)
- summary (1 phrase)
- category (backend/acl/ssl/etc.)

Usage:
    uv run python 01b_enrich_metadata.py
"""

import json
import ollama
from pydantic import BaseModel, Field
from pathlib import Path


# ── Schéma Pydantic pour les metadata ────────────────────────────────────────
class SectionMetadata(BaseModel):
    """Métadonnées pour une section HAProxy."""

    keywords: list[str] = Field(
        ...,
        description="5-10 mots-clés techniques OBLIGATOIREMENT présents dans le texte",
        min_length=5,
        max_length=10,
    )
    synonyms: list[str] = Field(
        ...,
        description="3-5 termes associés, variantes, antonymes (ex: 'désactiver' → 'disabled')",
        min_length=3,
        max_length=5,
    )
    summary: str = Field(
        ..., description="Résumé en 1 phrase maximum de la section", max_length=200
    )
    category: str = Field(
        ...,
        description="Catégorie de la section",
        pattern=r"^(backend|frontend|acl|ssl|timeout|healthcheck|stick-table|logs|stats|general|loadbalancing)$",
    )


# ── Prompt pour l'IA ─────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2.

Ta tâche : Extraire des métadonnées pour améliorer la recherche sémantique dans un système RAG.

RÈGLES ABSOLUES :
1. N'INVENTE RIEN - Utilise UNIQUEMENT le contenu fourni
2. Keywords doivent être OBLIGATOIREMENT dans le texte
3. Sois précis et technique
4. Réponds UNIQUEMENT avec le JSON valide, pas de texte avant ou après
"""

USER_PROMPT_TEMPLATE = """Pour cette section HAProxy, extraire :

1. KEYWORDS (5-10) : Mots-clés techniques présents dans le texte
2. SYNONYMES (3-5) : Termes associés, variantes (ex: "désactiver" → "disabled", "down")
3. SUMMARY (1 phrase max) : Résumé ultra-court
4. CATEGORY : backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general, loadbalancing

Section :
{section}

Métadonnées JSON :"""


# ── Fonction d'enrichissement ────────────────────────────────────────────────
def generate_metadata(
    section_content: str, model: str = "gemma3:latest"
) -> SectionMetadata:
    """
    Génère les métadonnées pour une section via Ollama.

    Args:
        section_content: Contenu de la section (max 8000 chars)
        model: Modèle Ollama à utiliser

    Returns:
        SectionMetadata validée par Pydantic
    """
    # Limiter à 8000 chars pour éviter les timeouts
    content = section_content[:8000]

    prompt = USER_PROMPT_TEMPLATE.format(section=content)

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            format=SectionMetadata.model_json_schema(),
            options={
                "temperature": 0.1,  # Bas pour du déterminisme
                "num_predict": 500,
            },
        )

        # Parser la réponse JSON
        json_content = response["message"]["content"]
        metadata = SectionMetadata.model_validate_json(json_content)

        return metadata

    except Exception as e:
        print(f"  [WARN] Erreur IA: {e}")
        # Fallback metadata vides
        return SectionMetadata(
            keywords=["ha-proxy", "configuration"],
            synonyms=[],
            summary="Section de documentation HAProxy.",
            category="general",
        )


# ── Pipeline principal ──────────────────────────────────────────────────────
def main():
    input_path = Path("data/sections.jsonl")
    output_path = Path("data/sections_enriched.jsonl")

    if not input_path.exists():
        print(f"❌ {input_path} introuvable. Lance d'abord 01_scrape.py")
        return

    # Charger les sections
    sections = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                sections.append(json.loads(line))

    print(f"[INFO] {len(sections)} sections chargees depuis {input_path}")
    print("[INFO] Modele IA: gemma3:latest")
    print(
        f"[INFO] Temps estime: ~{len(sections) * 5 // 60} min ({len(sections)} sections x 5s)"
    )
    print()

    # Enrichir chaque section
    enriched = []
    errors = 0

    for i, section in enumerate(sections, 1):
        title = section.get("title", "Unknown")[:50]
        print(f"[{i}/{len(sections)}] {title}...", end=" ", flush=True)

        metadata = generate_metadata(section["content"])
        section["metadata"] = metadata.model_dump()

        # Afficher resume
        print(f"OK {len(metadata.keywords)} keywords | {metadata.category}")

        if not metadata.keywords or not metadata.summary:
            errors += 1
            print("  [WARN] Metadata incomplete")

        enriched.append(section)

    # Sauvegarder
    print(f"\n[INFO] Sauvegarde dans {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        for section in enriched:
            f.write(json.dumps(section, ensure_ascii=False) + "\n")

    # Stats
    total_keywords = sum(len(s["metadata"]["keywords"]) for s in enriched)
    categories = {}
    for s in enriched:
        cat = s["metadata"]["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print()
    print("=" * 70)
    print("[SUCCESS] ENRICHISSEMENT TERMINE")
    print("=" * 70)
    print(f"[INFO] Sections enrichies: {len(enriched)}")
    print(f"[WARN] Erreurs/partielles: {errors}")
    print(
        f"[INFO] Keywords totaux: {total_keywords} ({total_keywords // len(enriched):.1f}/section)"
    )
    print("[INFO] Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count} ({count * 100 // len(enriched)}%)")
    print()
    print("Prochaine etape:")
    print("  uv run python 02_chunking.py  (propager metadata aux chunks)")
    print()


if __name__ == "__main__":
    main()
