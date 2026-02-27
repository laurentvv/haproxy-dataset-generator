"""
02_chunking.py - Chunking intelligent avec propagation metadata

Entree  : data/sections_enriched.jsonl (avec metadata IA)
Sortie  : data/chunks_v2.jsonl (metadata propagees aux chunks)

Features :
- Chunking semantique par concepts HAProxy
- Propagation metadata IA (keywords, synonyms, category)
- Parent section tracking
- Taille optimale : 300-800 chars
- Overlap contextuel intelligent
"""

import json
import re
import sys
import io
from pathlib import Path
from typing import Optional

# Fix encoding Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── Constantes ──────────────────────────────────────────────────────────────
MIN_CHUNK_CHARS = 300  # Minimum pour un embedding de qualité
MAX_CHUNK_CHARS = 800  # Optimal pour la précision sémantique
OVERLAP_CHARS = 150  # Overlap pour garder le contexte


# ── Patterns HAProxy ────────────────────────────────────────────────────────
# Patterns pour extraire les directives et keywords HAProxy
HAPROXY_PATTERNS = {
    "directive": re.compile(
        r"^(?:option\s+)?([a-z][a-z0-9\-]*(?:\s+[a-z0-9\-]+)*)", re.MULTILINE
    ),
    "keyword": re.compile(r"`([a-z][a-z0-9\-]*(?:\s+[a-z0-9\-]+)*)`", re.IGNORECASE),
    "section_ref": re.compile(r"\[?(\d+\.\d+(?:\.\d+)*)\]?", re.MULTILINE),
}

# Mots-clés techniques HAProxy à détecter
HAPROXY_KEYWORDS = {
    "stick-table": [
        "stick-table",
        "stick",
        "track-sc",
        "track-sc0",
        "track-sc1",
        "track-sc2",
        "gpc",
        "conn_rate",
        "conn_cur",
        "http_req_rate",
        "http_req_cnt",
    ],
    "acl": ["acl", "path_beg", "path_end", "hdr", "host", "url", "src", "dst"],
    "healthcheck": [
        "check",
        "option httpchk",
        "http-check",
        "inter",
        "fall",
        "rise",
        "port",
    ],
    "bind": ["bind", "ssl", "crt", "key", "cafile", "verify", "alpn", "proto"],
    "backend": ["backend", "server", "balance", "dispatch", "option"],
    "frontend": ["frontend", "default_backend", "use_backend"],
    "timeout": ["timeout", "connect", "client", "server", "http-request", "queue"],
    "logging": ["log", "syslog", "format", "capture", "error"],
    "ssl": ["ssl", "tls", "certificate", "cafile", "verify", "ciphers", "sni"],
    "compression": ["compression", "gzip", "deflate", "offload"],
    "rate_limit": [
        "rate",
        "limit",
        "throttle",
        "deny",
        "tarpit",
        "reject",
        "maxconn",
        "bandwidth",
    ],
}

# Directives HTTP-request à détecter
HTTP_REQUEST_ACTIONS = [
    "http-request deny",
    "http-request redirect",
    "http-request set-header",
    "http-request track-sc",
    "http-request track-sc0",
    "http-request track-sc1",
    "http-request set-bandwidth-limit",
    "http-request auth",
]


def detect_source(url: str) -> str:
    """Détecte le type de source depuis l'URL."""
    if "intro" in url:
        return "intro"
    if "configuration" in url:
        return "configuration"
    if "management" in url:
        return "management"
    return "unknown"


def has_code_block(text: str) -> bool:
    """Vérifie si le texte contient un bloc de code."""
    return "```" in text


def extract_haproxy_keywords(text: str) -> list[str]:
    """
    Extrait les keywords HAProxy pertinents du texte.
    Retourne une liste de tags.
    """
    tags = []
    text_lower = text.lower()

    for category, keywords in HAPROXY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                tags.append(category)
                break  # Un tag par catégorie suffit

    # Extraire les directives HTTP-request spécifiques
    for action in HTTP_REQUEST_ACTIONS:
        if action in text_lower:
            tags.append(f"directive:{action.replace(' ', '_')}")

    # Extraire les sample fetches (sc0_*, sc1_*, table_*)
    sample_fetches = re.findall(r"\b(sc\d+_[a-z_]+|table_[a-z_]+)\b", text_lower)
    for fetch in sample_fetches[:5]:  # Limiter à 5
        tags.append(f"sample_fetch:{fetch}")

    return list(set(tags))


def extract_section_hierarchy(title: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extrait la hiérarchie de section depuis le titre.
    Retourne (parent_section, current_section).
    """
    if not title:
        return None, None

    # Matcher les titres numérotés (ex: "5.2. Server options")
    match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?\s*(.*)$", title)
    if match:
        chapter = match.group(1)
        section = match.group(2)
        subsection = match.group(3)

        if subsection:
            parent = f"{chapter}.{section}"
            current = f"{chapter}.{section}.{subsection}"
        else:
            parent = chapter
            current = f"{chapter}.{section}"

        return parent, current

    return None, title


def split_into_semantic_chunks(text: str, title: str) -> list[str]:
    """
    Découpe un texte en chunks sémantiques cohérents.
    Priorité aux séparateurs naturels et concepts HAProxy.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    chunks = []
    remaining = text

    # Séparateurs par ordre de priorité
    separators = [
        ("\n\n###", "Sous-section"),
        ("\n\n##", "Section"),
        ("\n\n", "Paragraphe"),
        (". ", "Phrase"),
    ]

    while len(remaining) > MAX_CHUNK_CHARS:
        window = remaining[: MAX_CHUNK_CHARS + 200]  # Fenêtre élargie

        # Trouver le meilleur point de coupure
        best_cut = None

        for sep, name in separators:
            # Chercher dans la fenêtre optimale
            search_start = MIN_CHUNK_CHARS
            search_end = min(len(window), MAX_CHUNK_CHARS)

            idx = window.rfind(sep, search_start, search_end)
            if idx > search_start:
                # Vérifier qu'on ne coupe pas un bloc de code
                before = window[:idx]
                if before.count("```") % 2 == 0:  # Pas dans un bloc
                    best_cut = idx + len(sep)
                    break

        if best_cut is None:
            # Fallback: couper au plus proche de MAX_CHUNK_CHARS
            best_cut = MAX_CHUNK_CHARS

        chunk = remaining[:best_cut].strip()
        if chunk:
            chunks.append(chunk)

        # Overlap: reprendre un peu de contexte
        overlap_start = max(0, best_cut - OVERLAP_CHARS)
        remaining = remaining[overlap_start:]

        # Sécurité: éviter les boucles infinies
        if len(remaining) == len(text):
            chunks.append(remaining.strip())
            break

        text = remaining

    if remaining.strip():
        chunks.append(remaining.strip())

    return chunks


def merge_short_sections(sections: list[dict], min_chars: int) -> list[dict]:
    """
    Fusionne les sections trop courtes avec la section suivante
    si elles ont la même URL source.
    """
    merged = []
    i = 0

    while i < len(sections):
        current = sections[i].copy()

        # Fusionner tant que trop court et même source
        while (
            len(current.get("content", "")) < min_chars
            and i + 1 < len(sections)
            and sections[i + 1].get("url") == current.get("url")
        ):
            next_sec = sections[i + 1]
            next_title = next_sec.get("title", "")

            if next_title and next_title != current.get("title"):
                current["content"] += f"\n\n## {next_title}\n\n" + next_sec["content"]
            else:
                current["content"] += "\n\n" + next_sec["content"]

            i += 1

        merged.append(current)
        i += 1

    return merged


def build_chunks(sections: list[dict]) -> list[dict]:
    """
    Pipeline complet de chunking intelligent :
    1. Fusion des sections courtes
    2. Découpage sémantique des sections longues
    3. Propagation metadata IA aux chunks
    """
    # Étape 1 : fusionner les sections trop courtes
    sections = merge_short_sections(sections, MIN_CHUNK_CHARS)
    print(f"   Après fusion : {len(sections)} sections")

    chunks = []
    chunk_id = 0

    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "").strip()
        url = section.get("url", "")
        source = detect_source(url)

        # Récupérer metadata IA (si présentes)
        metadata = section.get("metadata", {})
        ia_keywords = metadata.get("keywords", [])
        ia_synonyms = metadata.get("synonyms", [])
        ia_category = metadata.get("category", "general")
        ia_summary = metadata.get("summary", "")

        if not content:
            continue

        # Extraire la hiérarchie
        parent_section, current_section = extract_section_hierarchy(title)

        # Étape 2 : découpage sémantique
        if len(content) > MAX_CHUNK_CHARS:
            sub_chunks = split_into_semantic_chunks(content, title)
        else:
            sub_chunks = [content]

        for idx, chunk_text in enumerate(sub_chunks):
            # Le texte à embedder inclut le titre et le contexte hiérarchique
            context_parts = []
            if parent_section:
                context_parts.append(f"Section {parent_section}")
            if title:
                context_parts.append(title)

            context_prefix = " | ".join(context_parts) if context_parts else ""
            embed_text = (
                f"{context_prefix}\n\n{chunk_text}" if context_prefix else chunk_text
            )

            # Extraire les keywords HAProxy du chunk
            tags = extract_haproxy_keywords(chunk_text)

            # Combiner keywords IA + keywords extraits du chunk
            chunk_keywords = list(
                set(
                    [t.split(":")[1] for t in tags if ":" in t]
                    + [kw.lower() for kw in ia_keywords]
                )
            )

            chunks.append(
                {
                    "id": chunk_id,
                    "title": title,
                    "content": chunk_text,
                    "embed_text": embed_text,
                    "url": url,
                    "source": source,
                    "parent_section": parent_section,
                    "current_section": current_section,
                    "chunk_index": idx,
                    "total_chunks": len(sub_chunks),
                    "has_code": has_code_block(chunk_text),
                    "char_len": len(chunk_text),
                    "tags": tags,
                    "keywords": chunk_keywords,
                    # Metadata IA propagées
                    "ia_keywords": ia_keywords,
                    "ia_synonyms": ia_synonyms,
                    "ia_category": ia_category,
                    "ia_summary": ia_summary,
                }
            )
            chunk_id += 1

    return chunks


def main():
    data_dir = Path("data")
    input_path = data_dir / "sections_enriched.jsonl"
    output_path = data_dir / "chunks_v2.jsonl"

    if not input_path.exists():
        print(f"[ERREUR] {input_path} introuvable.")
        print("  Lance d'abord : uv run python 01b_enrich_metadata.py")
        return

    # Charger les sections enrichies
    sections = []
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                sections.append(json.loads(line))

    print(f"[INFO] {len(sections)} sections enrichies chargees depuis {input_path}")

    # Statistiques avant
    lengths_before = [len(s["content"]) for s in sections]
    print(
        f"   Avant | Moy: {sum(lengths_before) // len(lengths_before)} | "
        f"Min: {min(lengths_before)} | Max: {max(lengths_before)}"
    )

    # Construire les chunks
    chunks = build_chunks(sections)

    # Statistiques après
    lengths_after = [c["char_len"] for c in chunks]
    has_code_count = sum(1 for c in chunks if c["has_code"])
    tags_count = sum(len(c["tags"]) for c in chunks)

    # Stats metadata IA
    chunks_with_ia = sum(1 for c in chunks if c.get("ia_keywords"))
    total_ia_keywords = sum(len(c.get("ia_keywords", [])) for c in chunks)

    print("\n[INFO] Resultat re-chunking V2:")
    print(f"   Chunks totaux     : {len(chunks)}")
    print(
        f"   Avec code         : {has_code_count} ({has_code_count * 100 // len(chunks)}%)"
    )
    print(f"   Taille moy.       : {sum(lengths_after) // len(lengths_after)} chars")
    print(f"   Min / Max         : {min(lengths_after)} / {max(lengths_after)}")
    print(
        f"   Tags HAProxy      : {tags_count} ({tags_count // len(chunks):.1f}/chunk)"
    )
    print(
        f"   Avec metadata IA  : {chunks_with_ia} ({chunks_with_ia * 100 // len(chunks)}%)"
    )
    print(
        f"   IA keywords tot.  : {total_ia_keywords} ({total_ia_keywords // len(chunks):.1f}/chunk)"
    )

    # Distribution des tailles
    small = sum(1 for length in lengths_after if length < 300)
    medium = sum(1 for length in lengths_after if 300 <= length < 600)
    large = sum(1 for length in lengths_after if length >= 600)
    print(f"   Distribution      : <300: {small} | 300-600: {medium} | >600: {large}")

    # Sauvegarder
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\n[SUCCESS] {len(chunks)} chunks sauvegardes dans {output_path}")

    # Afficher quelques exemples
    print("\n[EXEMPLES] Quelques chunks:")
    for i in [0, min(5, len(chunks) - 1), min(20, len(chunks) - 1)]:
        c = chunks[i]
        print(f"\n  Chunk {c['id']}: {c['title'][:50]}")
        print(f"    Tags HAProxy: {', '.join(c['tags'][:5]) if c['tags'] else 'aucun'}")
        print(
            f"    IA Keywords: {', '.join(c['ia_keywords'][:5]) if c.get('ia_keywords') else 'aucun'}"
        )
        print(f"    IA Category: {c.get('ia_category', 'N/A')}")
        print(f"    Len: {c['char_len']} | Code: {c['has_code']}")
