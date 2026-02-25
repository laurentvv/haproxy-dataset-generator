"""
retriever_v3.py - Retrieval hybride V3 avec qwen3-embedding:8b (MTEB #1 mondial)

Entrée  : index_v3/ (chunks + embeddings qwen3-embedding:8b)
Sortie  : context + sources pour LLM

Différences avec V2 :
- Embedding : qwen3-embedding:8b (MTEB 70.58) au lieu de bge-m3 (MTEB 67)
- Dimension : 4096 au lieu de 1024
- Contexte : 40K tokens au lieu de 8K
"""
import logging
import os
import pickle
import re
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError("Installe chromadb : uv add chromadb")

try:
    import requests
except ImportError:
    raise ImportError("Installe requests : uv add requests")

try:
    from flashrank import Ranker, RerankRequest
    FLASHRANK_AVAILABLE = True
except ImportError:
    FLASHRANK_AVAILABLE = False
    logger.warning("flashrank non disponible, reranking désactivé")


# Config V3
OLLAMA_URL        = "http://localhost:11434"
EMBED_MODEL       = "qwen3-embedding:8b"  # MTEB #1 mondial (70.58)
CHROMA_COLLECTION = "haproxy_docs_v3"

INDEX_DIR  = Path("index_v3")
CHROMA_DIR = INDEX_DIR / "chroma"
BM25_PATH  = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL = INDEX_DIR / "chunks.pkl"

TOP_K_RETRIEVAL      = 50
TOP_K_RRF            = 25
TOP_K_RERANK         = 5
RRF_K                = 60
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.0"))


# ── Query Expansion ──────────────────────────────────────────────────────────
QUERY_EXPANSIONS = {
    "health check": ["health check", "check", "option httpchk", "tcp-check", "inter", "fall", "rise"],
    "httpchk": ["option httpchk", "http-check", "GET", "HEAD", "uri", "HTTP version"],
    "bind": ["bind", ":", "port", "ssl", "crt", "key", "cafile", "verify", "alpn"],
    "connexion par ip": ["stick-table", "src", "conn_rate", "conn_cur", "track-sc", "track-sc0", "deny", "http_req_rate"],
    "rate limit": ["stick-table", "rate", "limit", "throttle", "deny", "tarpit", "http_req_rate"],
    "acl": ["acl", "path_beg", "path_end", "hdr", "host", "url", "use_backend", "if"],
    "timeout": ["timeout", "connect", "client", "server", "http-request", "queue"],
    "ssl": ["ssl", "tls", "crt", "certificate", "cafile", "verify", "ciphers"],
}


def expand_query(query: str) -> list[str]:
    """Étend la requête avec des synonymes techniques HAProxy."""
    query_lower = query.lower()
    expanded = set()
    
    original_tokens = _tokenize(query)
    expanded.update(original_tokens)
    
    for key, expansions in QUERY_EXPANSIONS.items():
        if key in query_lower:
            expanded.update(expansions)
    
    if "http" in query_lower:
        expanded.update(["HTTP", "http-request", "http-response", "httpchk"])
    
    return list(expanded)


# Singletons
_chroma_collection = None
_bm25 = None
_chunks = None
_reranker = None
_index_error = None


def _load_indexes():
    """Charge les index V3 une seule fois."""
    global _chroma_collection, _bm25, _chunks, _reranker, _index_error
    
    if _chroma_collection is not None:
        return
    
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"Index V3 manquant : {CHROMA_DIR}\nLance 03_build_index_v3.py"
        )
    if not BM25_PATH.exists():
        raise FileNotFoundError(
            f"Index BM25 V3 manquant : {BM25_PATH}\nLance 03_build_index_v3.py"
        )
    if not CHUNKS_PKL.exists():
        raise FileNotFoundError(
            f"Chunks V3 manquant : {CHUNKS_PKL}\nLance 03_build_index_v3.py"
        )
    
    logger.info("Chargement des index V3 (qwen3-embedding:8b)...")
    
    # ChromaDB
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    _chroma_collection = client.get_collection(CHROMA_COLLECTION)
    
    # BM25 + chunks
    with open(BM25_PATH, "rb") as f:
        _bm25 = pickle.load(f)
    with open(CHUNKS_PKL, "rb") as f:
        _chunks = pickle.load(f)
    
    # Reranker
    if FLASHRANK_AVAILABLE:
        import tempfile
        cache_dir = Path(tempfile.gettempdir()) / "flashrank_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        _reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=str(cache_dir))
    
    logger.info(f"✅ Index V3 chargés : {len(_chunks)} chunks | ChromaDB: {_chroma_collection.count()} docs")


def _get_embedding(text: str) -> list[float] | None:
    """Embedding via qwen3-embedding:8b."""
    try:
        with requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=120,
        ) as response:
            response.raise_for_status()
            return response.json()["embedding"]
    except requests.exceptions.ConnectionError as e:
        logger.error("Erreur connexion Ollama (embedding): %s", e)
        return None
    except requests.exceptions.Timeout as e:
        logger.error("Timeout Ollama (embedding): %s", e)
        return None
    except Exception as e:
        logger.error("Erreur embedding: %s", e)
        return None


def _tokenize(text: str) -> list[str]:
    """Tokenisation pour BM25."""
    text = text.lower()
    tokens = re.findall(r'[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]', text)
    stopwords = {
        'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou',
        'en', 'au', 'aux', 'the', 'a', 'an', 'is', 'are', 'for', 'in', 'on',
        'at', 'to', 'of', 'with', 'by', 'from', 'this', 'that',
    }
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _chroma_search(query_embedding: list[float], top_k: int) -> list[tuple[int, float]]:
    """Recherche vectorielle ChromaDB."""
    results = _chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, _chroma_collection.count()),
        include=["distances", "metadatas"],
    )
    
    ids = results["ids"][0]
    distances = results["distances"][0]
    
    output = []
    for chroma_id, dist in zip(ids, distances):
        chunk_idx = int(chroma_id.replace("chunk_", ""))
        similarity = 1.0 - dist
        output.append((chunk_idx, similarity))
    
    return output


def _bm25_search(query: str, top_k: int) -> list[tuple[int, float]]:
    """Recherche BM25 avec query expansion."""
    original_tokens = _tokenize(query)
    expanded_tokens = expand_query(query)
    expanded_tokens_lower = [t.lower() for t in expanded_tokens if len(t) > 1]
    
    all_tokens = original_tokens + original_tokens + expanded_tokens_lower
    
    if not all_tokens:
        return []
    
    scores = _bm25.get_scores(all_tokens)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]


def _reciprocal_rank_fusion(
    chroma_results: list[tuple[int, float]],
    bm25_results: list[tuple[int, float]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """Fusion RRF (Reciprocal Rank Fusion)."""
    rrf_scores: dict[int, float] = {}
    
    for rank, (chunk_id, _) in enumerate(chroma_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    
    for rank, (chunk_id, _) in enumerate(bm25_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Reranking avec FlashRank + query expansion."""
    if not FLASHRANK_AVAILABLE or _reranker is None:
        for c in candidates:
            c["rerank_score"] = c.get("rrf_score", 0.5)
        return candidates
    
    passages = [
        {"id": i, "text": c["content"], "meta": c}
        for i, c in enumerate(candidates)
    ]
    
    expanded_query = " ".join(expand_query(query))
    results = _reranker.rerank(
        RerankRequest(query=expanded_query, passages=passages)
    )
    
    reranked = []
    for result in results:
        if isinstance(result, dict):
            chunk = result.get('meta', {}).copy() if result.get('meta') else {}
            if not chunk:
                chunk = candidates[result.get('id', 0)].copy()
            chunk["rerank_score"] = float(result.get('score', 0.0))
        elif hasattr(result, 'meta'):
            chunk = result.meta.copy()
            chunk["rerank_score"] = float(result.score)
        else:
            logger.error("Type de résultat flashrank inconnu: %s", type(result))
            continue
        reranked.append(chunk)
    
    # Boosting par keywords
    query_keywords = set(_tokenize(query.lower()))
    expanded_query_keywords = set(expand_query(query.lower()))
    
    strong_keywords = ["stick-table", "track-sc", "http_req_rate", "conn_rate", "deny", "acl"]
    
    for chunk in reranked:
        content_lower = chunk.get("content", "").lower()
        title_lower = chunk.get("title", "").lower()
        
        matches_base = sum(1 for kw in query_keywords if kw in content_lower or kw in title_lower)
        matches_expanded = sum(1 for kw in expanded_query_keywords if kw in content_lower or kw in title_lower)
        matches = max(matches_base, matches_expanded)
        
        match_ratio = matches / len(expanded_query_keywords) if expanded_query_keywords else 0
        
        title_boost = 0.0
        for strong_kw in strong_keywords:
            if strong_kw in title_lower:
                title_boost += 0.3
        
        original_score = chunk.get("rerank_score", 0)
        chunk["rerank_score"] = original_score * (1.0 + 0.5 * match_ratio + title_boost)
        chunk["_keyword_matches"] = matches
        chunk["_match_ratio"] = match_ratio
        chunk["_title_boost"] = title_boost
    
    reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return reranked


def retrieve(
    query: str,
    top_k: int = TOP_K_RERANK,
    verbose: bool = False,
    filter_source: str | None = None,
) -> dict:
    """Pipeline complet de retrieval V3."""
    _load_indexes()
    
    query_emb = _get_embedding(query)
    if query_emb is None:
        return {"chunks": [], "low_confidence": True, "query": query, "best_score": 0.0}
    
    if filter_source:
        chroma_results_raw = _chroma_collection.query(
            query_embeddings=[query_emb],
            n_results=min(TOP_K_RETRIEVAL, _chroma_collection.count()),
            where={"source": filter_source},
            include=["distances", "metadatas"],
        )
        ids = chroma_results_raw["ids"][0]
        distances = chroma_results_raw["distances"][0]
        chroma_results = [
            (int(cid.replace("chunk_", "")), 1.0 - dist)
            for cid, dist in zip(ids, distances)
        ]
    else:
        chroma_results = _chroma_search(query_emb, TOP_K_RETRIEVAL)
    
    if verbose:
        print(f"\n[ChromaDB V3] top-5 :")
        for rank, (cid, score) in enumerate(chroma_results[:5]):
            print(f"   [{rank+1}] sim={score:.3f} | {_chunks[cid]['title'][:60]}")
    
    bm25_results = _bm25_search(query, TOP_K_RETRIEVAL)
    
    if verbose:
        print(f"\n[BM25 V3] top-5 (query expansion):")
        for rank, (cid, score) in enumerate(bm25_results[:5]):
            print(f"   [{rank+1}] score={score:.3f} | {_chunks[cid]['title'][:60]}")
    
    rrf_results = _reciprocal_rank_fusion(chroma_results, bm25_results)[:TOP_K_RRF]
    
    if verbose:
        print(f"\n[RRF V3] top-5 :")
        for rank, (cid, score) in enumerate(rrf_results[:5]):
            print(f"   [{rank+1}] rrf={score:.4f} | {_chunks[cid]['title'][:60]}")
    
    candidates = []
    for chunk_id, rrf_score in rrf_results:
        chunk = _chunks[chunk_id].copy()
        chunk["rrf_score"] = rrf_score
        chunk["chunk_id"] = chunk_id
        candidates.append(chunk)
    
    reranked = _rerank(query, candidates)
    final = reranked[:top_k]
    
    if verbose:
        print(f"\n[Reranking V3] résultats finaux :")
        for rank, chunk in enumerate(final):
            code_icon = "[code]" if chunk["has_code"] else "      "
            print(f"   [{rank+1}] score={chunk.get('rerank_score', 0):.3f} | {code_icon} | {chunk['title'][:60]}")
    
    best_score = final[0].get("rerank_score", 0) if final else 0.0
    low_confidence = best_score < CONFIDENCE_THRESHOLD
    
    logger.debug("Score V3 (qwen3-embedding:8b): %.4f | low_confidence=%s", best_score, low_confidence)
    
    if verbose:
        print(f"[DEBUG V3] Scores de rerank:")
        for i, chunk in enumerate(final):
            score = chunk.get("rerank_score", 0)
            matches = chunk.get("_keyword_matches", "?")
            print(f"   [{i+1}] score={score:.4f} | matches={matches} | {chunk['title'][:50]}")
    
    if not final and verbose:
        print("[WARN V3] Aucun résultat, tentative avec requête simplifiée...")
        simple_query = " ".join([t for t in _tokenize(query) if len(t) > 3])
        if simple_query:
            return retrieve(simple_query, top_k=top_k, verbose=verbose, filter_source=filter_source)
    
    return {
        "chunks": final,
        "low_confidence": low_confidence,
        "best_score": best_score,
        "query": query,
    }


def retrieve_context_string(
    query: str,
    top_k: int = TOP_K_RERANK,
    filter_source: str | None = None,
) -> tuple[str, list[dict], bool]:
    """Helper : retourne contexte formaté pour LLM + sources."""
    result = retrieve(query, top_k=top_k, filter_source=filter_source)
    chunks = result["chunks"]
    
    if not chunks:
        return "", [], True
    
    parts = []
    for i, chunk in enumerate(chunks):
        source_label = f"[Source {i+1}: {chunk['title']} - {chunk['url']}]"
        parts.append(f"{source_label}\n\n{chunk['content']}")
    
    context_str = "\n\n---\n\n".join(parts)
    
    sources = [
        {
            "title": chunk["title"],
            "url": chunk["url"],
            "source": chunk["source"],
            "score": round(chunk.get("rerank_score", chunk.get("rrf_score", 0)), 3),
            "has_code": chunk["has_code"],
        }
        for chunk in chunks
    ]
    
    return context_str, sources, result["low_confidence"]


if __name__ == "__main__":
    import sys
    
    query = sys.argv[1] if len(sys.argv) > 1 else "Comment configurer un health check HTTP ?"
    print(f"\n[QUERY V3] {query}\n")
    
    result = retrieve(query, verbose=True)
    
    if result["low_confidence"]:
        print("\n[WARN V3] Confiance faible")
    
    print(f"\n[OK V3] {len(result['chunks'])} chunks retournés")
    for i, chunk in enumerate(result["chunks"]):
        print(f"\n{'='*60}")
        print(f"Chunk V3 {i+1} | {chunk['title']}")
        print(f"Source  : {chunk['url']}")
        print(f"Score   : {chunk.get('rerank_score', 0):.3f}")
        print(f"Code    : {'oui' if chunk['has_code'] else 'non'}")
        print(f"\n{chunk['content'][:300]}...")
