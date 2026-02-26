#!/usr/bin/env python3
"""
03_indexing.py - Construction index V3 avec metadata IA

Entree  : data/chunks_v2.jsonl (avec metadata IA)
Sortie  : index_v3/chroma/, index_v3/bm25.pkl, index_v3/chunks.pkl

Features V3+:
- Embedding : qwen3-embedding:8b (MTEB 70.58, 4096 dims)
- Metadata IA : keywords, synonyms, category (de gemma3:latest)
- Collection : haproxy_docs_v3
"""

import json
import logging
import pickle
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ── Metadata Sanitization ───────────────────────────────────────────────────
def sanitize_metadata(value: str, max_length: int = 500) -> str:
    """
    Sanitize metadata string for safe storage in ChromaDB.

    Args:
        value: Raw metadata value
        max_length: Maximum length after sanitization

    Returns:
        Sanitized metadata string
    """
    if not isinstance(value, str):
        return ""

    # Remove control characters (except newlines, tabs)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)

    # Remove potentially dangerous characters for metadata storage
    sanitized = sanitized.replace("\x00", "").replace("\\x00", "")

    # Truncate to max length
    return sanitized[:max_length]


def sanitize_metadata_list(
    items: list, max_items: int = 20, max_item_length: int = 100
) -> list[str]:
    """
    Sanitize a list of metadata items.

    Args:
        items: List of metadata strings
        max_items: Maximum number of items to keep
        max_item_length: Maximum length per item

    Returns:
        Sanitized list of strings
    """
    if not isinstance(items, list):
        return []

    sanitized = []
    for item in items[:max_items]:
        if isinstance(item, str):
            clean_item = sanitize_metadata(item, max_length=max_item_length)
            if clean_item:  # Only add non-empty items
                sanitized.append(clean_item)

    return sanitized


# Config V3
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:8b"
CHROMA_COLLECTION = "haproxy_docs_v3"

INDEX_DIR = Path("index_v3")
CHROMA_DIR = INDEX_DIR / "chroma"
BM25_PATH = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL = INDEX_DIR / "chunks.pkl"

DATA_DIR = Path("data")
CHUNKS_PATH = DATA_DIR / "chunks_v2.jsonl"


# Cache Ollama
_embedding_cache = {}


def get_embedding(text: str) -> list[float]:
    """Embedding avec cache."""
    if text in _embedding_cache:
        return _embedding_cache[text]

    try:
        import requests

        with requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=120,
        ) as response:
            response.raise_for_status()
            emb = response.json()["embedding"]
            _embedding_cache[text] = emb
            return emb
    except Exception as e:
        logger.error("Erreur embedding: %s", e)
        # Fallback: vecteur nul (mieux que crash)
        return [0.0] * 4096


def build_index(chunks: list[dict], batch_size: int = 100):
    """
    Construit l'index ChromaDB + BM25 + embeddings.

    Args:
        chunks: Liste des chunks avec metadata
        batch_size: Taille des batches pour embeddings
    """
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        logger.error("chromadb non installe: uv add chromadb")
        return

    # Nettoyer ancien index
    if CHROMA_DIR.exists():
        import shutil

        shutil.rmtree(CHROMA_DIR)
        logger.info(f"🗑️  Ancien index supprime: {CHROMA_DIR}")

    # ChromaDB client
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.create_collection(CHROMA_COLLECTION)

    # BM25
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.error("rank_bm25 non installe: uv add rank-bm25")
        return

    # Tokenization pour BM25
    def tokenize(text: str) -> list[str]:
        text = text.lower()
        tokens = re.findall(r"[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]", text)
        stopwords = {
            "le",
            "la",
            "les",
            "de",
            "du",
            "des",
            "un",
            "une",
            "et",
            "ou",
            "en",
            "au",
            "aux",
            "the",
            "a",
            "an",
            "is",
            "are",
            "for",
            "in",
            "on",
            "at",
            "to",
            "of",
            "with",
            "by",
            "from",
            "this",
            "that",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 1]

    bm25_tokens = []

    # Progression
    total = len(chunks)
    done = 0

    logger.info(f"📦 Indexation de {total} chunks...")

    # Traiter par batches
    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]

        # Ajuster l'index global pour les IDs
        global_start = i
        ids = [f"chunk_{global_start + j}" for j in range(len(batch))]
        embeddings_list = []
        documents = []
        metadatas = []

        for chunk in batch:
            embed_text = chunk.get("embed_text", chunk["content"])
            emb = get_embedding(embed_text)
            embeddings_list.append(emb)
            documents.append(chunk["content"])

            # Metadata de base (sanitized)
            meta = {
                "title": sanitize_metadata(chunk.get("title", ""), max_length=500),
                "url": sanitize_metadata(chunk.get("url", ""), max_length=500),
                "source": sanitize_metadata(
                    chunk.get("source", chunk.get("url", "")), max_length=100
                ),
                "has_code": chunk.get("has_code", False),
            }

            # Metadata HAProxy tags (sanitized list)
            if chunk.get("tags"):
                tags_list = sanitize_metadata_list(chunk["tags"], max_items=20)
                if tags_list:
                    meta["tags"] = ",".join(tags_list)

            # Keywords combines (HAProxy + IA) (sanitized list)
            if chunk.get("keywords"):
                keywords_list = sanitize_metadata_list(chunk["keywords"], max_items=30)
                if keywords_list:
                    meta["keywords"] = ",".join(keywords_list)

            # Metadata IA (de gemma3:latest) (sanitized)
            if chunk.get("ia_keywords"):
                ia_kw_list = sanitize_metadata_list(chunk["ia_keywords"], max_items=20)
                if ia_kw_list:
                    meta["ia_keywords"] = ",".join(ia_kw_list)

            if chunk.get("ia_synonyms"):
                ia_syn_list = sanitize_metadata_list(chunk["ia_synonyms"], max_items=10)
                if ia_syn_list:
                    meta["ia_synonyms"] = ",".join(ia_syn_list)

            if chunk.get("ia_category"):
                meta["ia_category"] = sanitize_metadata(
                    chunk["ia_category"], max_length=50
                )

            if chunk.get("ia_summary"):
                meta["ia_summary"] = sanitize_metadata(
                    chunk["ia_summary"], max_length=500
                )

            metadatas.append(meta)

            # BM25 tokens
            bm25_tokens.append(tokenize(chunk["content"]))

        # Add to ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings_list,
            documents=documents,
            metadatas=metadatas,
        )

        done += len(batch)
        if done % 500 == 0 or done == total:
            pct = done * 100 // total
            eta_min = (total - done) * 2 // 60  # ~2s par chunk
            logger.info(
                f"   Progression: {done}/{total} ({pct}%) | ETA: ~{eta_min} min"
            )

    # Sauvegarder BM25
    bm25_index = BM25Okapi(bm25_tokens)
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_index, f)
    logger.info(f"✅ Index BM25 sauvegarde: {BM25_PATH}")

    # Sauvegarder chunks
    with open(CHUNKS_PKL, "wb") as f:
        pickle.dump(chunks, f)
    logger.info(f"✅ Chunks sauvegardes: {CHUNKS_PKL}")

    # Stats
    logger.info("\n✅ Index V3 termine !")
    logger.info(f"   Collection ChromaDB: {CHROMA_COLLECTION}")
    logger.info(f"   Nombre de chunks: {collection.count()}")
    logger.info(
        f"   Dimensions embedding: {len(embeddings_list[0]) if embeddings_list else 0}"
    )


def main():
    """Script principal."""
    print("=" * 70)
    print("🔍 Indexation V3 - HAProxy RAG")
    print("=" * 70)

    # Verifier dependencies
    try:
        import chromadb
        import requests
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.error("Dependencies manquantes: uv add chromadb requests rank-bm25")
        return

    # Verifier chunks
    if not CHUNKS_PATH.exists():
        logger.error(f"❌ {CHUNKS_PATH} introuvable. Lance 02_chunking.py")
        return

    # Charger chunks
    chunks = []
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    logger.info(f"📂 {len(chunks)} chunks charges depuis {CHUNKS_PATH}")

    # Verifier Ollama
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]
            if EMBED_MODEL in model_names or any(
                EMBED_MODEL.split(":")[0] in m for m in model_names
            ):
                logger.info(f"✅ Ollama OK - Modele: {EMBED_MODEL}")
            else:
                logger.warning(f"⚠️  Modele {EMBED_MODEL} non trouve dans Ollama")
                logger.info(f"   Modeles disponibles: {', '.join(model_names)}")
        else:
            logger.warning(f"⚠️  Ollama retourne status {resp.status_code}")
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Ollama non disponible sur {OLLAMA_URL}")
        logger.error("   Lance: ollama serve")
        return
    except Exception as e:
        logger.warning("⚠️ Erreur verification Ollama: %s", e)

    # Construire index
    build_index(chunks, batch_size=100)

    print("\n" + "=" * 70)
    print("✅ Indexation terminee !")
    print("=" * 70)


if __name__ == "__main__":
    main()
