"""
03_build_index_v2.py - Construction index V2 (from scratch)
"""
import json
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

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("❌ chromadb non installé")
    sys.exit(1)

try:
    from ollama import embeddings
except ImportError:
    print("❌ ollama non installé")
    sys.exit(1)

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    print("❌ rank_bm25 non installé")
    sys.exit(1)

import requests

# Config
OLLAMA_URL   = "http://localhost:11434"
EMBED_MODEL  = "qwen3-embedding:8b"  # MTEB #1 mondial (70.58) - 40K context
CHUNKS_PATH  = Path("data/chunks_v2.jsonl")
INDEX_DIR    = Path("index_v2")
CHROMA_DIR   = INDEX_DIR / "chroma"
BM25_PATH    = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL   = INDEX_DIR / "chunks.pkl"


def tokenize_haproxy(text: str) -> list[str]:
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
    """Récupère l'embedding via Ollama avec retry et context manager."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=120,
            ) as response:
                response.raise_for_status()
                return response.json()["embedding"]
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                raise
            print(f"   Retry connexion ({attempt+1}/{max_retries})...")
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise
            print(f"   Retry timeout ({attempt+1}/{max_retries})...")
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"   Retry ({attempt+1}/{max_retries}): {e}")
    return []


def main():
    print("\n" + "="*60)
    print("  BUILD INDEX V2 - HAProxy RAG")
    print("="*60)
    
    # Charger chunks
    if not CHUNKS_PATH.exists():
        print(f"\n❌ {CHUNKS_PATH} introuvable")
        print("   Lancez: uv run python 02_ingest_v2.py")
        return
    
    chunks = []
    with open(CHUNKS_PATH, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    print(f"\n📦 {len(chunks)} chunks à indexer")
    
    # Nettoyer index existant
    if CHROMA_DIR.exists():
        import shutil
        try:
            shutil.rmtree(CHROMA_DIR)
            print("🗑️  Ancien index supprimé")
        except PermissionError as e:
            print(f"⚠️  Fichier verrouillé : {e.filename}")
            print("   Fermez les processus Python et relancez")
            print("   Ou: taskkill /F /IM python.exe")
            return
    
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    # ChromaDB
    print("\n🔨 Index ChromaDB...")
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    
    collection = client.get_or_create_collection(
        name="haproxy_docs_v2",
        metadata={"hnsw:space": "cosine"},
    )
    
    # Batch processing
    batch_size = 100
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    start_time = time.time()
    
    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(chunks))
        batch = chunks[start:end]
        
        ids = [f"chunk_{c['id']}" for c in batch]
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
                "url": chunk['url'][:500],
                "source": chunk['source'],
                "has_code": chunk['has_code'],
            }
            if chunk.get('tags'):
                meta["tags"] = ",".join(chunk['tags'][:20])
            if chunk.get('keywords'):
                meta["keywords"] = ",".join(chunk['keywords'][:20])
            if chunk.get('parent_section'):
                meta["parent_section"] = chunk['parent_section']
            
            metadatas.append(meta)
        
        collection.upsert(
            ids=ids,
            embeddings=embeddings_list,
            documents=documents,
            metadatas=metadatas,
        )
        
        # Progress - affichage immédiat
        elapsed = time.time() - start_time
        progress = ((batch_idx + 1) / total_batches) * 100
        eta = (elapsed / (batch_idx + 1)) * (total_batches - batch_idx - 1) / 60 if batch_idx > 0 else 0
        print(f"   [{batch_idx+1:2d}/{total_batches}] {progress:5.1f}% - ETA: {eta:5.1f} min", flush=True)
    
    print(f"✅ {collection.count()} documents indexés")
    
    # BM25
    print("\n🔨 Index BM25...")
    tokenized = [tokenize_haproxy(c['content']) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    
    with open(BM25_PATH, 'wb') as f:
        pickle.dump(bm25, f)
    print(f"✅ BM25 créé ({len(tokenized)} chunks)")
    
    # Metadata
    print("\n📦 Metadata...")
    with open(CHUNKS_PKL, 'wb') as f:
        pickle.dump(chunks, f)
    print(f"✅ {len(chunks)} chunks sauvegardés")
    
    # Résumé
    elapsed = (time.time() - start_time) / 60
    print("\n" + "="*60)
    print(f"  INDEX V2 CONSTRUIT EN {elapsed:.1f} MINUTES")
    print("="*60)
    print(f"  Chunks:        {len(chunks)}")
    print(f"  ChromaDB:      {CHROMA_DIR}/")
    print(f"  BM25:          {BM25_PATH}")
    print(f"  Metadata:      {CHUNKS_PKL}")
    print("="*60)
    
    # Stats
    avg_len = sum(c['char_len'] for c in chunks) // len(chunks)
    avg_tags = sum(len(c.get('tags', [])) for c in chunks) // len(chunks)
    print(f"\n  Taille moy:    {avg_len} chars")
    print(f"  Tags moy:      {avg_tags}/chunk")
    print(f"  Avec code:     {sum(1 for c in chunks if c['has_code'])} ({sum(1 for c in chunks if c['has_code'])*100//len(chunks)}%)")
    print()


if __name__ == "__main__":
    main()
