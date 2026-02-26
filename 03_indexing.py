#!/usr/bin/env python3
"""
03_build_index_v3.py - Construction index V3 avec qwen3-embedding:8b (MTEB #1)

Entrée  : data/chunks_v2.jsonl
Sortie  : index_v3/chroma/, index_v3/bm25.pkl, index_v3/chunks.pkl

Différences avec V2 :
- Embedding : qwen3-embedding:8b (MTEB 70.58, 4096 dims) au lieu de bge-m3 (MTEB 67, 1024 dims)
- Collection : haproxy_docs_v3 au lieu de haproxy_docs_v2
"""
import json
import logging
import pickle
import re
import sys
import io
import time
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('build_index_v3.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    logger.error("❌ chromadb non installé : uv add chromadb")
    sys.exit(1)

try:
    import requests
except ImportError:
    logger.error("❌ requests non installé : uv add requests")
    sys.exit(1)

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    logger.error("❌ rank-bm25 non installé : uv add rank-bm25")
    sys.exit(1)

# Config V3
OLLAMA_URL   = "http://localhost:11434"
EMBED_MODEL  = "qwen3-embedding:8b"  # MTEB #1 mondial (70.58)
CHUNKS_PATH  = Path("data/chunks_v2.jsonl")
INDEX_DIR    = Path("index_v3")
CHROMA_DIR   = INDEX_DIR / "chroma"
BM25_PATH    = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL   = INDEX_DIR / "chunks.pkl"


def tokenize_haproxy(text: str) -> list[str]:
    """Tokenisation optimisée pour HAProxy."""
    text = text.lower()
    haproxy_terms = re.findall(r'[a-z][a-z0-9\-]*[a-z0-9]|[a-z0-9]', text)
    stopwords = {
        'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou',
        'en', 'au', 'aux', 'the', 'a', 'an', 'is', 'are', 'was', 'were',
        'for', 'in', 'on', 'at', 'to', 'of', 'with', 'by', 'from', 'this', 'that',
        'can', 'will', 'may', 'must', 'should', 'if', 'then', 'else',
    }
    return [t for t in haproxy_terms if t not in stopwords and len(t) > 1]


def get_embedding(text: str) -> list[float]:
    """Récupère l'embedding via qwen3-embedding:8b avec retry."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=180,  # qwen3-embedding:8b est plus lent (4.7 GB)
            ) as response:
                response.raise_for_status()
                return response.json()["embedding"]
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                raise
            logger.warning("Retry connexion (%d/%d)...", attempt + 1, max_retries)
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise
            logger.warning("Retry timeout (%d/%d)...", attempt + 1, max_retries)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning("Retry (%d/%d): %s", attempt + 1, max_retries, e)
    return []


def main():
    logger.info("\n" + "="*60)
    logger.info("  BUILD INDEX V3 - HAProxy RAG (qwen3-embedding:8b)")
    logger.info("="*60)
    
    if not CHUNKS_PATH.exists():
        logger.error(f"\n❌ {CHUNKS_PATH} introuvable")
        logger.error("   Lancez: uv run python 02_ingest_v2.py")
        return
    
    chunks = []
    with open(CHUNKS_PATH, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    logger.info(f"\n📦 {len(chunks)} chunks à indexer")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Vérifier si un index existe déjà et compter les documents
    start_chunk_idx = 0
    if CHROMA_DIR.exists():
        try:
            client_check = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
            existing_collection = client_check.get_collection("haproxy_docs_v3")
            existing_count = existing_collection.count()
            logger.info(f"♻️  Index existant trouvé : {existing_count} documents déjà indexés")

            # Trouver l'index du prochain chunk à indexer
            if existing_count > 0:
                # Récupérer le dernier ID indexé pour déterminer où reprendre
                # Note: order_by n'est pas disponible, on récupère tous les IDs et on trie
                try:
                    # Essayer d'abord avec include=['metadatas'] pour avoir un échantillon
                    sample = existing_collection.get(include=[], limit=100)
                    if sample and sample['ids']:
                        # Extraire les index des chunks et trouver le maximum
                        max_idx = -1
                        for chunk_id in sample['ids']:
                            match = re.match(r"chunk_(\d+)", chunk_id)
                            if match:
                                idx = int(match.group(1))
                                if idx > max_idx:
                                    max_idx = idx
                        if max_idx >= 0:
                            start_chunk_idx = max_idx + 1
                            logger.info(f"🔄 Reprise de l'indexation au chunk #{start_chunk_idx}")
                        else:
                            logger.info("🔄 Reprise depuis le chunk #0")
                    else:
                        logger.info("🔄 Reprise depuis le chunk #0")
                except Exception as e2:
                    logger.warning(f"⚠️ Erreur lors de la lecture des IDs : {e2}")
                    logger.info("🔄 Reprise depuis le chunk #0")
            else:
                logger.info("🔄 Index vide, reprise depuis le chunk #0")
        except Exception as e:
            logger.warning(f"⚠️  Impossible de lire l'index existant : {e}")
            logger.info("🗑️  Suppression de l'index corrompu et reprise depuis zéro...")
            import shutil
            try:
                shutil.rmtree(CHROMA_DIR)
            except:
                pass
            start_chunk_idx = 0
    else:
        logger.info("✨ Nouvel index à créer")

    logger.info("\n🔨 Index ChromaDB V3 (qwen3-embedding:8b)...")
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    collection = client.get_or_create_collection(
        name="haproxy_docs_v3",
        metadata={"hnsw:space": "cosine"},
    )

    # Calculer les chunks restants à indexer
    chunks_to_index = chunks[start_chunk_idx:]

    if not chunks_to_index:
        logger.info("✅ Tous les chunks sont déjà indexés !")
        logger.info(f"   Collection : {collection.count()} documents")
    else:
        logger.info(f"   📍 {start_chunk_idx} chunks déjà indexés, {len(chunks_to_index)} restants")

    batch_size = 100
    total_batches = (len(chunks_to_index) + batch_size - 1) // batch_size if chunks_to_index else 0
    start_time = time.time()

    if total_batches > 0:
        logger.info(f"   📦 {total_batches} batches de {batch_size} chunks")
        logger.info(f"   ⏱️  Temps estimé: ~{total_batches * 2:.0f}-{total_batches * 4:.0f} min (qwen3-embedding:8b est lent)")

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(chunks_to_index))
        batch = chunks_to_index[start:end]
        
        # Ajuster l'index global pour les IDs
        global_start = start_chunk_idx + start

        ids = [f"chunk_{start_chunk_idx + start + i}" for i in range(len(batch))]
        embeddings_list = []
        documents = []
        metadatas = []

        for chunk in batch:
            embed_text = chunk.get('embed_text', chunk['content'])
            emb = get_embedding(embed_text)
            embeddings_list.append(emb)
            documents.append(chunk['content'])

            meta = {
                "title": chunk['title'][:500] if chunk['title'] else "",
                "url": chunk.get('url', '')[:500],
                "source": chunk.get('source', chunk.get('url', '')),
                "has_code": chunk['has_code'],
            }
            if chunk.get('tags'):
                meta["tags"] = ",".join(chunk['tags'][:20])
            if chunk.get('keywords'):
                meta["keywords"] = ",".join(chunk['keywords'][:20])
            if chunk.get('parent_section'):
                meta["parent_section"] = chunk['parent_section']
            if chunk.get('section'):
                meta["section"] = chunk['section']

            metadatas.append(meta)

        collection.upsert(
            ids=ids,
            embeddings=embeddings_list,
            documents=documents,
            metadatas=metadatas,
        )

        elapsed = time.time() - start_time
        progress = ((global_start + len(batch)) / len(chunks)) * 100
        eta = (elapsed / (batch_idx + 1)) * (total_batches - batch_idx - 1) / 60 if batch_idx < total_batches - 1 else 0
        logger.info(f"   [{global_start + len(batch):5d}/{len(chunks)}] {progress:5.1f}% - ETA: {eta:5.1f} min")

    logger.info(f"✅ {collection.count()} documents indexés (V3)")

    # Vérifier si l'indexation est complète
    if collection.count() < len(chunks):
        logger.info("\n⚠️  Indexation PARTIELLE - Relancez le script pour continuer")
        logger.info(f"   {collection.count()}/{len(chunks)} documents indexés")
        return

    logger.info("\n🔨 Index BM25 V3...")
    tokenized = [tokenize_haproxy(c['content']) for c in chunks]
    bm25 = BM25Okapi(tokenized)

    with open(BM25_PATH, 'wb') as f:
        pickle.dump(bm25, f)
    logger.info(f"✅ BM25 V3 créé ({len(tokenized)} chunks)")

    logger.info("\n📦 Metadata V3...")
    with open(CHUNKS_PKL, 'wb') as f:
        pickle.dump(chunks, f)
    logger.info(f"✅ {len(chunks)} chunks sauvegardés")

    elapsed_total = (time.time() - start_time) / 60
    logger.info("\n" + "="*60)
    logger.info(f"  INDEX V3 CONSTRUIT EN {elapsed_total:.1f} MINUTES")
    logger.info("="*60)
    logger.info(f"  Embedding    : {EMBED_MODEL}")
    logger.info(f"  Dimension    : 4096 (qwen3-embedding:8b)")
    logger.info(f"  MTEB Score   : 70.58 (#1 mondial)")
    logger.info(f"  Chunks       : {len(chunks)}")
    logger.info(f"  ChromaDB     : {CHROMA_DIR}/")
    logger.info(f"  BM25         : {BM25_PATH}")
    logger.info(f"  Metadata     : {CHUNKS_PKL}")
    logger.info("="*60)

    avg_len = sum(c['char_len'] for c in chunks) // len(chunks)
    avg_tags = sum(len(c.get('tags', [])) for c in chunks) // len(chunks)
    logger.info(f"\n  Taille moy   : {avg_len} chars")
    logger.info(f"  Tags moy     : {avg_tags}/chunk")
    logger.info(f"  Avec code    : {sum(1 for c in chunks if c['has_code'])} ({sum(1 for c in chunks if c['has_code'])*100//len(chunks)}%)")
    logger.info("")


if __name__ == "__main__":
    main()
