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

from config import get_model_config


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
USER_PROMPT_TEMPLATE = """Extrais les métadonnées de ce texte HAProxy. Réponds UNIQUEMENT avec du JSON.

Texte:
{section}

Format JSON requis:
{{
  "keywords": ["5-10 mots du texte"],
  "synonyms": ["3-5 termes associés"],
  "summary": "résumé en 1 phrase (<200 chars)",
  "category": "backend|frontend|acl|ssl|timeout|healthcheck|stick-table|logs|stats|general|loadbalancing"
}}

JSON:"""


# ── Fonction d'enrichissement ────────────────────────────────────────────────
def generate_metadata(
    section_content: str, model: str | None = None
) -> SectionMetadata:
    """
    Génère les métadonnées pour une section via Ollama.

    Args:
        section_content: Contenu de la section (max 5000 chars)
        model: Modèle Ollama à utiliser (défaut: modèle d'enrichissement depuis config.py)

    Returns:
        SectionMetadata validée par Pydantic
    """
    if model is None:
        model = get_model_config("enrichment")

    # Stratégie de découpage pour sections longues (> 5000 chars)
    # On garde le début (titre/intro) + la fin (exemples/conclusion)
    max_chars = 5000
    if len(section_content) > max_chars:
        # Garder 2500 chars du début + 2500 chars de la fin
        content = section_content[:2500] + "\n\n[...] (section tronquée) [...]\n\n" + section_content[-2500:]
    else:
        content = section_content

    prompt = USER_PROMPT_TEMPLATE.format(section=content)

    try:
        # qwen3.5:4b : modèle thinking plus rapide que 9b
        # Paramètres optimisés pour génération JSON
        # num_ctx réduit à 4096 tokens (suffisant pour 5000 chars de texte)
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Extrais les métadonnées JSON du texte. Réponds UNIQUEMENT avec du JSON valide.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.6,  # Recommandé pour Qwen3.5 (précis)
                "num_predict": 3000,  # Thinking + JSON
                "num_ctx": 4096,  # Contexte réduit (défaut: 32768)
                "top_p": 0.95,
                "top_k": 20,
                "presence_penalty": 1.5,
            },
            stream=False,
        )

        # qwen3.5:4b est un modèle thinking - la réponse peut être dans 'thinking' ou 'content'
        json_content = response["message"].get("content", "").strip()

        # Si content est vide, extraire le JSON depuis thinking
        if not json_content:
            thinking = response["message"].get("thinking", "")
            if thinking:
                # Extraire le JSON du thinking (cherche le premier { et le dernier })
                start_idx = thinking.find("{")
                end_idx = thinking.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_content = thinking[start_idx:end_idx]

        # Nettoyer le contenu : garder uniquement le JSON valide
        # Chercher le premier { et le dernier } pour ignorer texte avant/après
        if json_content:
            start_idx = json_content.find("{")
            end_idx = json_content.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_content = json_content[start_idx:end_idx]

        # Nettoyer d'éventuels marqueurs markdown ```json ... ```
        if "```" in json_content:
            parts = json_content.split("```")
            for part in parts:
                if part.strip().startswith("json"):
                    json_content = part[4:].strip()
                    break
                elif part.strip().startswith("{"):
                    json_content = part.strip()
                    break
            json_content = json_content.rstrip("`").strip()

        # Vérifier que le JSON n'est pas vide
        if not json_content:
            raise ValueError("Réponse JSON vide")

        metadata = SectionMetadata.model_validate_json(json_content)

        return metadata

    except Exception as e:
        print(f"  [WARN] Erreur IA: {e}")
        # Fallback metadata valides (respectent les contraintes Pydantic)
        return SectionMetadata(
            keywords=["ha-proxy", "configuration", "load-balancer", "proxy", "server"],
            synonyms=["lb", "reverse-proxy", "balancing", "proxy-server"],
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
    default_model = get_model_config("enrichment")
    print(f"[INFO] Modele IA: {default_model}")
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
