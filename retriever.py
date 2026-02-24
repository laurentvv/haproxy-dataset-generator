"""
retriever.py - Retrieval hybride : ChromaDB + BM25 + RRF + Reranking
Fournit la fonction principale : retrieve(query) -> dict

Pipeline :
  1. Query expansion -> synonymes et termes techniques HAProxy
  2. ChromaDB search -> top-20 par similarite cosine (vectoriel)
  3. BM25 search     -> top-20 par score lexical
  4. RRF fusion      -> score combine, top-10 candidats
  5. Reranking       -> flashrank cross-encoder, top-5 finaux
  6. Seuil confiance -> flag low_confidence si score < 0.25
"""
import os
import pickle
import re
import numpy as np
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError("Installe chromadb : uv add chromadb")

try:
    import requests as req
except ImportError:
    raise ImportError("Installe requests : uv add requests")

try:
    from flashrank import Ranker, RerankRequest
    FLASHRANK_AVAILABLE = True
except ImportError:
    FLASHRANK_AVAILABLE = False
    print("[WARN] flashrank non disponible, reranking desactive. uv add flashrank")


# Config
OLLAMA_URL        = "http://localhost:11434"
EMBED_MODEL       = "bge-m3"  # Meilleur modèle embedding pour RAG (MTEB SOTA)
CHROMA_COLLECTION = "haproxy_docs_v2"  # Collection V2

INDEX_DIR  = Path("index_v2")  # V2 avec chunks enrichis
CHROMA_DIR = INDEX_DIR / "chroma"
BM25_PATH  = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL = INDEX_DIR / "chunks.pkl"

TOP_K_RETRIEVAL      = 50  # Augmente: plus de candidats pour RRF
TOP_K_RRF            = 25  # Augmente: garder plus de candidats avant reranking
TOP_K_RERANK         = 5
RRF_K                = 60
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.0"))


# ── Query Expansion ──────────────────────────────────────────────────────────
# Synonymes et termes techniques pour HAProxy
QUERY_EXPANSIONS = {
    # Health checks
    "health check": ["health check", "check", "option httpchk", "tcp-check", "inter", "fall", "rise"],
    "httpchk": ["option httpchk", "http-check", "GET", "HEAD", "uri", "HTTP version"],
    "check": ["check", "health check", "inter", "fall", "rise", "port", "address"],
    
    # Bind
    "bind": ["bind", ":", "port", "ssl", "crt", "key", "cafile", "verify", "alpn"],
    "directive bind": ["bind", "frontend", "listen", "address", "port", "ssl"],
    
    # Connection limiting / Rate limiting
    "limiter": ["stick-table", "conn_rate", "conn_cur", "gpc0", "deny", "reject", "rate limit"],
    "connexion par ip": ["stick-table", "src", "conn_rate", "conn_cur", "track-sc", "track-sc0", "deny", "http_req_rate", "sc0_http_req_rate"],
    "connexion": ["conn_rate", "conn_cur", "connection", "connect", "maxconn"],
    "rate limit": ["stick-table", "rate", "limit", "throttle", "deny", "tarpit", "http_req_rate", "http_req_cnt"],
    "bloquer": ["deny", "reject", "block", "drop", "429", "503"],
    "trop de": ["rate", "limit", "exceed", "gt", "greater than", "too many"],
    
    # ACL
    "acl": ["acl", "path_beg", "path_end", "hdr", "host", "url", "use_backend", "if", "condition"],
    "access control": ["acl", "allow", "deny", "http-request", "tcp-request"],
    "condition": ["acl", "if", "unless", "condition", "match"],
    
    # Timeout
    "timeout": ["timeout", "connect", "client", "server", "http-request", "http-keep-alive", "queue"],
    "delai": ["timeout", "delay", "inter", "slowstart"],
    
    # Backend/Server
    "backend": ["backend", "server", "balance", "option", "dispatch"],
    "frontend": ["frontend", "bind", "default_backend", "acl", "use_backend"],
    "server": ["server", "address", "port", "check", "weight", "backup"],
    
    # SSL/TLS
    "ssl": ["ssl", "tls", "crt", "certificate", "cafile", "verify", "ciphers"],
    "https": ["ssl", "https", "redirect", "scheme", "force-ssl"],
    
    # Logging
    "log": ["log", "syslog", "format", "capture", "error"],
}


def expand_query(query: str) -> list[str]:
    """
    Étend la requête avec des synonymes et termes techniques HAProxy.
    Retourne une liste de termes à rechercher.
    """
    query_lower = query.lower()
    expanded = set()
    
    # Ajouter les mots-clés originaux (tokenisés)
    original_tokens = _tokenize(query)
    expanded.update(original_tokens)
    
    # Chercher des correspondances dans QUERY_EXPANSIONS
    for key, expansions in QUERY_EXPANSIONS.items():
        if key in query_lower:
            expanded.update(expansions)
    
    # Ajouter des variantes techniques
    if "http" in query_lower:
        expanded.update(["HTTP", "http-request", "http-response", "httpchk"])
    if "tcp" in query_lower:
        expanded.update(["TCP", "tcp-check", "tcp-request", "tcp-response"])
    if "config" in query_lower or "configuration" in query_lower:
        expanded.update(["directive", "option", "keyword", "syntax"])
    
    return list(expanded)


# Singletons - charges une seule fois
_chroma_collection = None
_bm25              = None
_chunks            = None
_reranker          = None


def _load_indexes():
    global _chroma_collection, _bm25, _chunks, _reranker

    if _chroma_collection is not None:
        return  # Deja charges

    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"Index ChromaDB manquant : {CHROMA_DIR}\nLance 03_build_index.py"
        )
    if not BM25_PATH.exists():
        raise FileNotFoundError(
            f"Index BM25 manquant : {BM25_PATH}\nLance 03_build_index.py"
        )
    if not CHUNKS_PKL.exists():
        raise FileNotFoundError(
            f"Chunks pkl manquant : {CHUNKS_PKL}\nLance 03_build_index.py"
        )

    print("[INFO] Chargement des index...")

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

    # Reranker (optionnel)
    if FLASHRANK_AVAILABLE:
        import tempfile
        # Utiliser un répertoire portable avec tempfile
        cache_dir = Path(tempfile.gettempdir()) / "flashrank_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        _reranker = Ranker(
            model_name="ms-marco-MiniLM-L-12-v2",
            cache_dir=str(cache_dir),
        )

    print(f"   [OK] {len(_chunks)} chunks | ChromaDB: {_chroma_collection.count()} docs")


def _get_embedding(text: str) -> list[float] | None:
    """Embedding de la query via Ollama."""
    try:
        response = req.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"[ERROR] Embedding query : {e}")
        return None


def _tokenize(text: str) -> list[str]:
    """Meme tokenisation que build_index pour coherence BM25."""
    text = text.lower()
    tokens = re.findall(r'[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]', text)
    stopwords = {
        'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou',
        'en', 'au', 'aux', 'the', 'a', 'an', 'is', 'are', 'was', 'were',
        'for', 'in', 'on', 'at', 'to', 'of', 'with', 'by', 'from', 'this', 'that',
    }
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _chroma_search(query_embedding: list[float], top_k: int) -> list[tuple[int, float]]:
    """
    Recherche vectorielle ChromaDB.
    Retourne [(chunk_id_int, distance)] tries par distance croissante (cosine).
    On convertit l'id "chunk_X" -> int X pour l'alignement avec _chunks[].
    """
    results = _chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, _chroma_collection.count()),
        include=["distances", "metadatas"],
    )

    ids       = results["ids"][0]
    distances = results["distances"][0]

    output = []
    for chroma_id, dist in zip(ids, distances):
        # ChromaDB cosine distance : 0 = identique, 2 = oppose
        # Convertir en similarite : score = 1 - dist (range [−1, 1] apres normalisation)
        chunk_idx = int(chroma_id.replace("chunk_", ""))
        similarity = 1.0 - dist
        output.append((chunk_idx, similarity))

    return output  # Deja tries par ChromaDB (distance croissante = similarite decroissante)


def _bm25_search(query: str, top_k: int) -> list[tuple[int, float]]:
    """
    Recherche BM25 avec query expansion.
    Retourne [(chunk_id, score)].
    """
    # Tokens originaux
    original_tokens = _tokenize(query)
    
    # Tokens étendus
    expanded_tokens = expand_query(query)
    expanded_tokens_lower = [t.lower() for t in expanded_tokens if len(t) > 1]
    
    # Combiner les tokens (avec pondération)
    # Les tokens originaux comptent double
    all_tokens = original_tokens + original_tokens + expanded_tokens_lower
    
    if not all_tokens:
        return []
    
    scores = _bm25.get_scores(all_tokens)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]


def _reciprocal_rank_fusion(
    chroma_results: list[tuple[int, float]],
    bm25_results:   list[tuple[int, float]],
    k: int = RRF_K,
) -> list[tuple[int, float]]:
    """
    Reciprocal Rank Fusion :
    score(doc) = 1/(k + rank_chroma) + 1/(k + rank_bm25)
    """
    rrf_scores: dict[int, float] = {}

    for rank, (chunk_id, _) in enumerate(chroma_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    for rank, (chunk_id, _) in enumerate(bm25_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """
    Reranking avec flashrank cross-encoder + scoring hybride.
    """
    if not FLASHRANK_AVAILABLE or _reranker is None:
        for c in candidates:
            c["rerank_score"] = c.get("rrf_score", 0.5)
        return candidates

    # Préparer les passages
    passages = [
        {"id": i, "text": c["content"], "meta": c}
        for i, c in enumerate(candidates)
    ]
    
    # Rerank avec la requête étendue + termes techniques
    expanded_query = " ".join(expand_query(query))
    
    # Ajouter les termes techniques forts pour le reranking
    strong_terms = ["stick-table", "track-sc", "http_req_rate", "conn_rate", "deny", "acl"]
    for term in strong_terms:
        if term in query.lower() and term not in expanded_query:
            expanded_query += f" {term}"
    
    results = _reranker.rerank(RerankRequest(query=expanded_query, passages=passages))

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
            print(f"[ERROR] Type de result flashrank inconnu: {type(result)}")
            continue
        reranked.append(chunk)

    # Boosting post-rerank : ajuster les scores basé sur la présence de mots-clés
    query_keywords = set(_tokenize(query.lower()))
    
    # Ajouter les termes étendus pour le matching
    expanded_query_keywords = set(expand_query(query.lower()))
    
    # Mots-clés "forts" qui doivent booster significativement
    strong_keywords = ["stick-table", "track-sc", "http_req_rate", "conn_rate", "deny", "acl", "path_beg", "path_end", "hdr"]
    
    for chunk in reranked:
        content_lower = chunk.get("content", "").lower()
        title_lower = chunk.get("title", "").lower()
        
        # Compter les mots-clés présents (version étendue)
        matches_base = sum(1 for kw in query_keywords if kw in content_lower or kw in title_lower)
        matches_expanded = sum(1 for kw in expanded_query_keywords if kw in content_lower or kw in title_lower)
        matches = max(matches_base, matches_expanded)  # Prend le meilleur
        
        match_ratio = matches / len(expanded_query_keywords) if expanded_query_keywords else 0
        
        # Boost additionnel pour les "strong keywords" dans le titre
        title_boost = 0.0
        for strong_kw in strong_keywords:
            if strong_kw in title_lower:
                title_boost += 0.3  # +30% pour chunk avec stick-table dans le titre
        
        # Ajustement : score final = rerank_score * (1 + 0.5 * match_ratio + title_boost)
        original_score = chunk.get("rerank_score", 0)
        chunk["rerank_score"] = original_score * (1.0 + 0.5 * match_ratio + title_boost)
        
        # Debug info
        chunk["_keyword_matches"] = matches
        chunk["_match_ratio"] = match_ratio
        chunk["_title_boost"] = title_boost

    # Retrier par score ajusté
    reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

    return reranked


def retrieve(
    query: str,
    top_k: int = TOP_K_RERANK,
    verbose: bool = False,
    filter_source: str | None = None,   # "intro" | "configuration" | "management"
) -> dict:
    """
    Pipeline complet de retrieval hybride.

    Args:
        query         : Question de l'utilisateur
        top_k         : Nombre de chunks a retourner
        verbose       : Afficher les scores intermediaires
        filter_source : Filtrer par page source (optionnel, grace a ChromaDB metadata)

    Returns:
        dict avec :
          - chunks         : list[dict] chunks rerankes
          - low_confidence : bool
          - best_score     : float
          - query          : str
    """
    _load_indexes()

    # 1. Embedding de la query
    query_emb = _get_embedding(query)
    if query_emb is None:
        return {"chunks": [], "low_confidence": True, "query": query, "best_score": 0.0}

    # 2. Recherche ChromaDB (vectorielle)
    if filter_source:
        chroma_results_raw = _chroma_collection.query(
            query_embeddings=[query_emb],
            n_results=min(TOP_K_RETRIEVAL, _chroma_collection.count()),
            where={"source": filter_source},
            include=["distances", "metadatas"],
        )
        ids       = chroma_results_raw["ids"][0]
        distances = chroma_results_raw["distances"][0]
        chroma_results = [
            (int(cid.replace("chunk_", "")), 1.0 - dist)
            for cid, dist in zip(ids, distances)
        ]
    else:
        chroma_results = _chroma_search(query_emb, TOP_K_RETRIEVAL)

    if verbose:
        print(f"\n[ChromaDB] top-5 :")
        for rank, (cid, score) in enumerate(chroma_results[:5]):
            print(f"   [{rank+1}] sim={score:.3f} | {_chunks[cid]['title'][:60]}")

    # 3. Recherche BM25 (lexicale) avec query expansion
    bm25_results = _bm25_search(query, TOP_K_RETRIEVAL)

    if verbose:
        print(f"\n[BM25] top-5 (avec query expansion):")
        for rank, (cid, score) in enumerate(bm25_results[:5]):
            print(f"   [{rank+1}] score={score:.3f} | {_chunks[cid]['title'][:60]}")

    # 4. RRF Fusion
    rrf_results = _reciprocal_rank_fusion(chroma_results, bm25_results)[:TOP_K_RRF]

    if verbose:
        print(f"\n[RRF] top-5 :")
        for rank, (cid, score) in enumerate(rrf_results[:5]):
            print(f"   [{rank+1}] rrf={score:.4f} | {_chunks[cid]['title'][:60]}")

    # Construire les candidats
    candidates = []
    for chunk_id, rrf_score in rrf_results:
        chunk = _chunks[chunk_id].copy()
        chunk["rrf_score"]  = rrf_score
        chunk["chunk_id"]   = chunk_id
        candidates.append(chunk)

    # 5. Reranking avec boosting
    reranked = _rerank(query, candidates)
    final    = reranked[:top_k]

    if verbose:
        print(f"\n[Reranking] resultats finaux :")
        for rank, chunk in enumerate(final):
            code_icon = "[code]" if chunk["has_code"] else "      "
            print(f"   [{rank+1}] score={chunk.get('rerank_score', 0):.3f} "
                  f"| {code_icon} | {chunk['title'][:60]}")

    # 6. Seuil de confiance
    best_score     = final[0].get("rerank_score", 0) if final else 0.0
    low_confidence = best_score < CONFIDENCE_THRESHOLD

    # DEBUG: Log les scores
    print(f"[DEBUG] Seuil de confiance: {CONFIDENCE_THRESHOLD}")
    print(f"[DEBUG] Meilleur score de rerank: {best_score:.4f}")
    print(f"[DEBUG] low_confidence: {low_confidence}")
    if verbose:
        print(f"[DEBUG] Scores de rerank pour tous les chunks:")
        for i, chunk in enumerate(final):
            score = chunk.get("rerank_score", 0)
            matches = chunk.get("_keyword_matches", "?")
            print(f"   [{i+1}] score={score:.4f} | matches={matches} | title={chunk['title'][:50]}")

    # Fallback: si aucun résultat, essayer avec une requête simplifiée
    if not final and verbose:
        print("[WARN] Aucun résultat trouvé, tentative avec requête simplifiée...")
        # Extraire les mots-clés principaux (noms communs)
        simple_query = " ".join([t for t in _tokenize(query) if len(t) > 3])
        if simple_query:
            return retrieve(simple_query, top_k=top_k, verbose=verbose, filter_source=filter_source)

    return {
        "chunks"         : final,
        "low_confidence" : low_confidence,
        "best_score"     : best_score,
        "query"          : query,
    }


def retrieve_context_string(
    query: str,
    top_k: int = TOP_K_RERANK,
    filter_source: str | None = None,
) -> tuple[str, list[dict], bool]:
    """
    Helper : retourne la chaine de contexte formatee pour le LLM + les sources.

    Returns:
        (context_str, sources, low_confidence)
    """
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
            "title"   : chunk["title"],
            "url"     : chunk["url"],
            "source"  : chunk["source"],
            "score"   : round(chunk.get("rerank_score", chunk.get("rrf_score", 0)), 3),
            "has_code": chunk["has_code"],
        }
        for chunk in chunks
    ]

    return context_str, sources, result["low_confidence"]


# Test CLI
if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "Comment configurer un health check HTTP ?"
    print(f"\n[QUERY] {query}\n")

    result = retrieve(query, verbose=True)

    if result["low_confidence"]:
        print("\n[WARN] Confiance faible - information peut-etre absente de la doc")

    print(f"\n[OK] {len(result['chunks'])} chunks retournes")
    for i, chunk in enumerate(result["chunks"]):
        print(f"\n{'='*60}")
        print(f"Chunk {i+1} | {chunk['title']}")
        print(f"Source  : {chunk['url']}")
        print(f"Score   : {chunk.get('rerank_score', 0):.3f}")
        print(f"Code    : {'oui' if chunk['has_code'] else 'non'}")
        print(f"\n{chunk['content'][:300]}...")
