#!/usr/bin/env python3
"""
retriever_v3.py - Retrieval hybride V3+ avec metadata IA

Entree  : index_v3/ (chunks + embeddings qwen3-embedding:8b + metadata IA)
Sortie  : context + sources pour LLM

Features V3+ :
- Embedding : qwen3-embedding:8b (MTEB 70.58, 4096 dims)
- Metadata IA : keywords, synonyms, category (de gemma3:latest)
- IA Category Filtering pour retrieval cible
- IA Keyword Boosting pour meilleur ranking
"""

import os
import pickle
import re
import time
from datetime import datetime, timedelta

import numpy as np
from pathlib import Path

# Import configuration (must be before logging_config to avoid circular imports)
from config import ollama_config, retrieval_config, validation_config

# Use centralized logging configuration
from logging_config import setup_logging

logger = setup_logging(__name__)

# Re-export config values for backward compatibility
OLLAMA_URL = ollama_config.url
EMBED_MODEL = ollama_config.embed_model
CHROMA_COLLECTION = "haproxy_docs_v3"
INDEX_DIR = Path("index_v3")
TOP_K_RETRIEVAL = retrieval_config.top_k_retrieval
TOP_K_RRF = retrieval_config.top_k_rrf
TOP_K_RERANK = retrieval_config.top_k_rerank
RRF_K = retrieval_config.rrf_k
CONFIDENCE_THRESHOLD = retrieval_config.confidence_threshold


# ── Rate Limiting ───────────────────────────────────────────────────────────
class RateLimiter:
    """Rate limiter for API calls using token bucket algorithm."""

    def __init__(self, calls_per_minute: int = 30):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum number of calls allowed per minute
        """
        self.min_interval = timedelta(seconds=60 / calls_per_minute)
        self.last_call = datetime.min

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        now = datetime.now()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            wait_time = (self.min_interval - elapsed).total_seconds()
            if wait_time > 0:
                time.sleep(wait_time)
        self.last_call = datetime.now()


# Global rate limiter for Ollama API calls
_ollama_limiter = RateLimiter(
    calls_per_minute=ollama_config.rate_limit_calls_per_minute
)


# ── Input Validation ───────────────────────────────────────────────────────
def validate_query(query: str, max_length: int = None) -> str:
    """
    Validate and sanitize user query before processing.

    Args:
        query: User input string
        max_length: Maximum allowed query length (default: from config)

    Returns:
        Sanitized query string

    Raises:
        ValueError: If query is invalid or contains dangerous content
    """
    if max_length is None:
        max_length = validation_config.max_query_length

    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")

    # Strip whitespace and truncate
    query = query.strip()[:max_length]

    if not query:
        raise ValueError("Query contains no valid content")

    # Reject potentially dangerous patterns (prompt injection, XSS, etc.)
    dangerous_patterns = [
        (r"<script[^>]*>.*?</script>", "script tags"),
        (r"javascript:", "javascript protocol"),
        (r"{{.*}}", "template injection"),
        (r"<[^>]*>", "HTML tags"),
    ]

    for pattern, description in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE | re.DOTALL):
            logger.warning(
                "Query contains potentially dangerous content: %s", description
            )
            raise ValueError(f"Query rejected: {description} detected")

    # Remove control characters except newlines and tabs
    query = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)

    if not query.strip():
        raise ValueError("Query contains no valid content after sanitization")

    return query


def validate_filter_source(
    filter_source: str | None, allowed_sources: set[str] | None = None
) -> str | None:
    """
    Validate and sanitize filter_source parameter before using in ChromaDB query.

    Args:
        filter_source: User-provided source filter value
        allowed_sources: Set of allowed source values (optional, validates against known sources)

    Returns:
        Sanitized filter_source or None if invalid

    Raises:
        ValueError: If filter_source contains dangerous content
    """
    if filter_source is None:
        return None

    if not isinstance(filter_source, str):
        logger.warning("Invalid filter_source type: %s", type(filter_source))
        return None

    # Strip whitespace
    filter_source = filter_source.strip()

    # Check for empty string
    if not filter_source:
        return None

    # Check for potentially dangerous patterns (SQL injection, NoSQL injection, etc.)
    dangerous_patterns = [
        (r"\$where", "MongoDB $where operator"),
        (r"\$ne", "MongoDB inequality operator"),
        (r"\$gt|\$lt|\$gte|\$lte", "MongoDB comparison operators"),
        (r"\$in|\$nin", "MongoDB array operators"),
        (r"\$or|\$and|\$not", "MongoDB logical operators"),
        (r"\$regex|\$expr", "MongoDB regex/expression operators"),
        (r"__proto__|__defineGetter__|constructor", "JavaScript prototype pollution"),
        (r"eval\(|Function\(", "JavaScript eval/Function"),
        (r"<script[^>]*>", "script tags"),
        (r"javascript:", "javascript protocol"),
    ]

    for pattern, description in dangerous_patterns:
        if re.search(pattern, filter_source, re.IGNORECASE):
            logger.warning(
                "filter_source contains potentially dangerous content: %s", description
            )
            raise ValueError(f"Invalid filter_source: {description} detected")

    # If allowed_sources is provided, validate against it
    if allowed_sources is not None:
        if filter_source not in allowed_sources:
            logger.warning(
                "Invalid filter_source: %s (not in allowed sources)", filter_source
            )
            return None

    return filter_source


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

    FLASHRANK_AVAILABLE = True  # Set to False to disable FlashRank
except ImportError:
    FLASHRANK_AVAILABLE = False
    logger.warning("flashrank non disponible, reranking desactive")

# Configuration: FlashRank can be disabled via environment variable
# DISABLE_FLASHRANK=true uv run python 04_chatbot.py
if os.getenv("DISABLE_FLASHRANK", "false").lower() == "true":
    FLASHRANK_AVAILABLE = False
    logger.info("FlashRank desactive via DISABLE_FLASHANK=true")


# ── HTTP Session Pooling ─────────────────────────────────────────────────────
# Session globale pour le pooling de connexions HTTP
_retriever_session = requests.Session()
_retriever_session.mount(
    "http://",
    requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=3,
    ),
)


# Paths (derived from config)
CHROMA_DIR = INDEX_DIR / "chroma"
BM25_PATH = INDEX_DIR / "bm25.pkl"
CHUNKS_PKL = INDEX_DIR / "chunks.pkl"

# Retrieval parameters (from config, kept for backward compatibility)
TOP_K_RETRIEVAL = retrieval_config.top_k_retrieval
TOP_K_RRF = 30
TOP_K_RERANK = 10
RRF_K = 60
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.0"))


# ── Metadata Filtering V3+ ───────────────────────────────────────────────────
# Mapping IA (keywords → categories) - ENRICHED WITH SYNONYMS
# Note: Categories are assigned by IA (gemma3) during indexing
IA_CATEGORY_HINTS = {
    # Backend / Server / Load Balancing (related categories)
    "backend": "backend",
    "server": "backend",
    "serveur": "backend",  # French
    "désactiver": "backend",  # French
    "desactiver": "backend",  # French sans accents
    "disable": "backend",
    "disabled": "backend",
    "down": "backend",
    "inactive": "backend",
    "backup": "backend",
    "weight": "backend",
    "balance": "loadbalancing",
    "roundrobin": "loadbalancing",
    "leastconn": "loadbalancing",
    "source": "loadbalancing",
    "load balancing": "loadbalancing",
    "loadbalancing": "loadbalancing",
    # ACL
    "acl": "acl",
    "access control": "acl",
    "condition": "acl",
    "filter": "acl",
    # Stick-table
    "stick-table": "stick-table",
    "stick table": "stick-table",
    "stick": "stick-table",
    "rate limit": "stick-table",
    "rate": "stick-table",
    "limit": "stick-table",
    "track": "stick-table",
    "track-sc": "stick-table",
    "conn_rate": "stick-table",
    "conn_cur": "stick-table",
    "http_req_rate": "stick-table",
    "store": "stick-table",
    "store-request": "stick-table",
    "store-response": "stick-table",
    "gpc": "stick-table",
    "server_id": "stick-table",
    "expire": "stick-table",
    "exp": "stick-table",
    "table": "stick-table",  # stick-table = table de stick
    # Frontend / Bind
    "bind": "frontend",
    "frontend": "frontend",
    "listen": "frontend",
    # Timeout
    "timeout": "timeout",
    "delai": "timeout",
    "délai": "timeout",
    # Healthcheck
    "health": "healthcheck",
    "healthcheck": "healthcheck",
    "check": "healthcheck",
    "httpchk": "healthcheck",
    "tcp-check": "healthcheck",
    # SSL
    "ssl": "ssl",
    "tls": "ssl",
    "certificate": "ssl",
    "certificat": "ssl",  # French
    "crt": "ssl",
    "cafile": "ssl",
    "ca-file": "ssl",
    "verify": "ssl",
    "crl": "ssl",
    "crl-file": "ssl",
    "ciphers": "ssl",
    "client certificate": "ssl",
    "verify required": "ssl",
    "verify none": "ssl",
    "sni": "ssl",
    "alpn": "ssl",
    # Logs
    "log": "logs",
    "logs": "logs",
    "logging": "logs",
    "syslog": "logs",
    # Stats
    "stats": "stats",
    "statistics": "stats",
    "monitoring": "stats",
    "surveillance": "stats",  # French
    "show": "stats",
    "hide": "stats",
    "socket": "stats",
    "uri": "stats",
    "admin": "stats",
    # Map / Converters (advanced)
    "map": "advanced",
    "maps": "advanced",
    "converter": "advanced",
    "converters": "advanced",
    "convert": "advanced",
    "lower": "advanced",
    "upper": "advanced",
    "lowercase": "advanced",
    "uppercase": "advanced",
    "lc": "advanced",
    "uc": "advanced",
}

# Mapping sections (legacy - pour retrocompatibilite)
SECTION_HINTS = {
    "stick-table": ["11.1", "11.2", "7.3"],
    "acl": ["7.1", "7.2", "7.3", "7.4"],
    "bind": ["4.2", "5.1", "5.3"],
    "backend": ["5.1", "5.2", "5.3"],
    "server": ["5.2", "5.3"],
    "timeout": ["4.2", "5.2", "5.3"],
    "health": ["5.2", "5.3"],
    "check": ["5.2", "5.3"],
    "ssl": ["4.2", "5.1", "5.3"],
    "balance": ["5.1", "5.2"],
}


def extract_section_hints(query: str) -> list[str] | None:
    """Extrait les sections HAProxy probables."""
    query_lower = query.lower()
    hints = set()

    match = re.search(r"(?:section|chapitre)\s*(\d+(?:\.\d+)?)", query_lower)
    if match:
        section = match.group(1)
        if "." not in section:
            section = f"{section}.0"
        hints.add(section)
        return list(hints)

    for keyword, sections in SECTION_HINTS.items():
        if keyword in query_lower:
            hints.update(sections)

    return list(hints) if hints else None


def extract_category_hints(query: str) -> str | None:
    """Extrait la categorie IA probable."""
    query_lower = query.lower()
    for keyword, category in IA_CATEGORY_HINTS.items():
        if keyword in query_lower:
            return category
    return None


# ── Query Expansion ──────────────────────────────────────────────────────────
QUERY_EXPANSIONS = {
    "health check": [
        "health check",
        "check",
        "option httpchk",
        "tcp-check",
        "inter",
        "fall",
        "rise",
    ],
    "httpchk": ["option httpchk", "http-check", "GET", "HEAD", "uri"],
    "bind": ["bind", "port", "ssl", "crt", "key", "cafile", "verify"],
    # Stick-table / Rate limiting
    "rate limit": [
        "stick-table",
        "rate",
        "limit",
        "deny",
        "http_req_rate",
        "conn_rate",
        "conn_cur",
        "track-sc",
        "track-sc0",
        "track-sc1",
        "track-sc2",
    ],
    "stick-table": [
        "stick-table",
        "stick table",
        "stick",
        "store",
        "store-request",
        "store-response",
        "track-sc",
        "http_req_rate",
        "conn_rate",
        "conn_cur",
        "gpc0",
        "gpc1",
        "server_id",
    ],
    "stick": [
        "stick-table",
        "stick table",
        "store-request",
        "store-response",
        "track-sc",
        "on",
        "match",
    ],
    "rate": [
        "stick-table",
        "rate",
        "limit",
        "http_req_rate",
        "conn_rate",
        "sess_rate",
        "exp",
        "expire",
    ],
    "limit": ["stick-table", "limit", "rate", "deny", "tarpit", "throttle"],
    "conn_rate": [
        "stick-table",
        "conn_rate",
        "conn_cur",
        "connection rate",
        "track-sc",
        "deny",
    ],
    "tracker": ["stick-table", "track-sc", "track-sc0", "stick on"],
    # ACL
    "acl": [
        "acl",
        "path_beg",
        "path_end",
        "hdr",
        "host",
        "url",
        "use_backend",
        "if",
        "path_reg",
        "path_sub",
        "path",
    ],
    "access control": ["acl", "condition", "filter", "path_beg", "hdr", "deny"],
    "regex": ["acl", "regex", "regexp", "path_reg", "hdr_reg", "url_reg", "pattern"],
    "negation": ["acl", "!", "not", "negation", "negated", "unless"],
    # Timeout
    "timeout": ["timeout", "connect", "client", "server", "http-request", "queue"],
    # SSL / TLS
    "ssl": [
        "ssl",
        "tls",
        "crt",
        "certificate",
        "cafile",
        "verify",
        "ciphers",
        "ca-file",
        "crl-file",
        "verify required",
        "verify none",
    ],
    "tls": ["ssl", "tls", "certificate", "crt", "cafile", "verify"],
    "certificate": ["ssl", "crt", "certificate", "cafile", "pem", "chain"],
    "cafile": ["ssl", "cafile", "ca-file", "CA certificate", "verify"],
    "verify": [
        "ssl",
        "verify",
        "cafile",
        "verify required",
        "verify none",
        "client certificate",
    ],
    # Stats / Monitoring
    "stats": [
        "stats",
        "statistics",
        "monitoring",
        "show",
        "hide",
        "uri",
        "admin",
        "socket",
    ],
    "statistics": ["stats", "statistics", "monitoring", "table", "show"],
    "monitoring": ["stats", "monitoring", "health", "status", "show"],
    # Map / Converters
    "map": ["map", "converters", "convert", "lower", "upper", "table", "file"],
    "converter": [
        "converters",
        "convert",
        "map",
        "lower",
        "upper",
        "str",
        "int",
        "ipmask",
    ],
    "lower": ["converters", "lower", "lc", "lowercase", "string"],
    "upper": ["converters", "upper", "uc", "uppercase", "string"],
}


def expand_query(query: str) -> list[str]:
    """Etend la requete avec synonymes techniques."""
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
_allowed_sources: set[str] | None = None


def _get_allowed_sources() -> set[str]:
    """Extract unique source values from loaded chunks for validation."""
    global _allowed_sources
    if _allowed_sources is not None:
        return _allowed_sources

    if _chunks is None:
        return set()

    _allowed_sources = set()
    for chunk in _chunks:
        source = chunk.get("source")
        if source and isinstance(source, str):
            _allowed_sources.add(source)

    logger.debug("Extracted %d unique sources from chunks", len(_allowed_sources))
    return _allowed_sources


def _load_indexes():
    """Charge les index V3+."""
    global _chroma_collection, _bm25, _chunks, _reranker

    if _chroma_collection is not None:
        return

    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            f"Index V3 manquant : {CHROMA_DIR}\nLance 03_indexing.py"
        )
    if not BM25_PATH.exists():
        raise FileNotFoundError(
            f"Index BM25 manquant : {BM25_PATH}\nLance 03_indexing.py"
        )
    if not CHUNKS_PKL.exists():
        raise FileNotFoundError(f"Chunks manquant : {CHUNKS_PKL}\nLance 03_indexing.py")

    logger.info("Chargement des index V3+ (qwen3-embedding:8b + metadata IA)...")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    _chroma_collection = client.get_collection(CHROMA_COLLECTION)

    with open(BM25_PATH, "rb") as f:
        _bm25 = pickle.load(f)
    with open(CHUNKS_PKL, "rb") as f:
        _chunks = pickle.load(f)

    if FLASHRANK_AVAILABLE:
        import tempfile

        cache_dir = Path(tempfile.gettempdir()) / "flashrank_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        _reranker = Ranker(
            model_name="ms-marco-MiniLM-L-12-v2", cache_dir=str(cache_dir)
        )

    logger.info(
        f"✅ Index V3+ charges : {len(_chunks)} chunks | ChromaDB: {_chroma_collection.count()} docs"
    )


def _get_embedding(text: str, max_retries: int = None) -> list[float] | None:
    """
    Embedding via qwen3-embedding:8b with retry logic and rate limiting.

    Args:
        text: Text to embed
        max_retries: Maximum number of retry attempts (default: from config)

    Returns:
        Embedding vector or None if all retries failed
    """
    if max_retries is None:
        max_retries = ollama_config.max_retries

    for attempt in range(max_retries):
        try:
            # Wait if needed to respect rate limit
            _ollama_limiter.wait_if_needed()

            with _retriever_session.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=120,
            ) as response:
                response.raise_for_status()
                return response.json()["embedding"]
        except requests.exceptions.ConnectionError as e:
            if attempt == max_retries - 1:
                logger.error(
                    "Embedding service unavailable after %d attempts", max_retries
                )
                return None
            wait_time = 2**attempt  # Exponential backoff
            logger.warning(
                "Embedding attempt %d/%d failed, retrying in %ds: %s",
                attempt + 1,
                max_retries,
                wait_time,
                e,
            )
            time.sleep(wait_time)
        except requests.exceptions.Timeout as e:
            if attempt == max_retries - 1:
                logger.error("Embedding request timeout after %d attempts", max_retries)
                return None
            wait_time = 2**attempt
            logger.warning(
                "Embedding timeout attempt %d/%d, retrying in %ds: %s",
                attempt + 1,
                max_retries,
                wait_time,
                e,
            )
            time.sleep(wait_time)
        except Exception as e:
            logger.error("Embedding error: %s", e)
            return None

    return None


def _tokenize(text: str) -> list[str]:
    """Tokenisation pour BM25."""
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


def _chroma_search(
    query_embedding: list[float], top_k: int, query_text: str = ""
) -> list[tuple[int, float]]:
    """Recherche vectorielle ChromaDB SANS filtrage (boosting dans rerank)."""
    # Pas de filtrage restrictif - on recupere tous les candidats
    # Le category boosting sera fait dans le reranking
    # Note: query_text is kept for API compatibility but not used in V3+

    results = _chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k * 2, _chroma_collection.count()),
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
    """Fusion RRF."""
    rrf_scores: dict[int, float] = {}

    for rank, (chunk_id, _) in enumerate(chroma_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    for rank, (chunk_id, _) in enumerate(bm25_results):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


def _apply_boosting(
    chunk: dict,
    query_keywords: set[str],
    expanded_query_keywords: set[str],
    category_hint: str | None,
    strong_keywords: list[str],
) -> dict:
    """
    Applique le boosting IA metadata (keywords, synonyms, category, title) à un chunk.

    Args:
        chunk: Chunk à booster (avec keys: content, title, ia_keywords, ia_synonyms, ia_category)
        query_keywords: Mots-clés extraits de la requête
        expanded_query_keywords: Mots-clés étendus de la requête
        category_hint: Catégorie IA suggérée par la requête
        strong_keywords: Liste des mots-clés forts pour le boost de titre

    Returns:
        Chunk modifié avec les scores de boosting appliqués
    """
    content_lower = chunk.get("content", "").lower()
    title_lower = chunk.get("title", "").lower()

    # Match keywords de base
    matches_base = sum(
        1 for kw in query_keywords if kw in content_lower or kw in title_lower
    )
    matches_expanded = sum(
        1 for kw in expanded_query_keywords if kw in content_lower or kw in title_lower
    )
    matches = max(matches_base, matches_expanded)
    match_ratio = (
        matches / len(expanded_query_keywords) if expanded_query_keywords else 0
    )

    # IA keywords boost
    ia_keywords = chunk.get("ia_keywords", [])
    if ia_keywords:
        ia_matches = sum(
            1
            for kw in ia_keywords
            if kw.lower() in expanded_query_keywords
            or kw.lower() in content_lower
            or kw.lower() in title_lower
        )
        ia_boost = 0.3 * (ia_matches / len(ia_keywords))
    else:
        ia_matches = 0
        ia_boost = 0

    # IA synonyms boost
    ia_synonyms = chunk.get("ia_synonyms", [])
    if ia_synonyms:
        synonym_matches = sum(
            1
            for syn in ia_synonyms
            if syn.lower() in expanded_query_keywords
            or syn.lower() in content_lower
            or syn.lower() in title_lower
        )
        synonym_boost = 0.2 * (synonym_matches / len(ia_synonyms))
    else:
        synonym_matches = 0
        synonym_boost = 0

    # IA Category Boost (SOFT - backend ↔ loadbalancing, ssl ↔ frontend related)
    category_boost = 0.0
    if category_hint:
        chunk_category = chunk.get("ia_category", "")
        # Direct match
        if chunk_category == category_hint:
            category_boost = 0.5
        # Related categories
        elif category_hint == "backend" and chunk_category == "loadbalancing":
            category_boost = 0.3
        elif category_hint == "loadbalancing" and chunk_category == "backend":
            category_boost = 0.3
        elif category_hint == "ssl" and chunk_category == "frontend":
            category_boost = 0.3  # SSL config souvent dans bind options (frontend)
        elif category_hint == "frontend" and chunk_category == "ssl":
            category_boost = 0.3
        elif category_hint == "healthcheck" and chunk_category == "loadbalancing":
            category_boost = 0.3  # Health checks dans server options
        elif category_hint == "acl" and chunk_category == "general":
            category_boost = 0.2  # ACL dans toutes sections

    # Title boost
    title_boost = 0.0
    for strong_kw in strong_keywords:
        if strong_kw in title_lower:
            title_boost += 0.3

    original_score = chunk.get("rerank_score", 0)
    chunk["rerank_score"] = original_score * (
        1.0
        + 0.5 * match_ratio
        + ia_boost
        + synonym_boost
        + category_boost
        + title_boost
    )
    chunk["_keyword_matches"] = matches
    chunk["_ia_matches"] = ia_matches
    chunk["_match_ratio"] = match_ratio
    chunk["_ia_boost"] = ia_boost
    chunk["_category_boost"] = category_boost
    chunk["_title_boost"] = title_boost

    return chunk


def _rerank(query: str, candidates: list[dict], verbose: bool = False) -> list[dict]:
    """Reranking avec FlashRank + IA metadata boosting (SOFT)."""

    # IA Category Boosting and keyword matching (applied even without FlashRank)
    category_hint = extract_category_hints(query)
    query_keywords = set(_tokenize(query.lower()))
    expanded_query_keywords = set(expand_query(query.lower()))
    strong_keywords = [
        "stick-table",
        "track-sc",
        "http_req_rate",
        "conn_rate",
        "deny",
        "acl",
    ]

    # DEBUG: Log query keywords for debugging
    logger.debug("Query keywords: %s", query_keywords)
    logger.debug("Expanded query keywords: %s", expanded_query_keywords)
    logger.debug("Category hint: %s", category_hint)

    if not FLASHRANK_AVAILABLE or _reranker is None:
        # No FlashRank: apply simple boosting based on keyword/category matching
        for chunk in candidates:
            chunk["rerank_score"] = chunk.get("rrf_score", 0.5)
            _apply_boosting(
                chunk,
                query_keywords,
                expanded_query_keywords,
                category_hint,
                strong_keywords,
            )

        candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return candidates

    # Option 3: Injecter IA keywords dans le texte pour FlashRank
    # FlashRank va ainsi mieux scorer les chunks avec metadata pertinente
    passages = []
    for i, c in enumerate(candidates):
        # Ajouter metadata IA au texte pour le reranking
        ia_context = []
        if c.get("ia_keywords"):
            ia_context.append("Keywords: " + ", ".join(c["ia_keywords"][:10]))
        if c.get("ia_synonyms"):
            ia_context.append("Synonyms: " + ", ".join(c["ia_synonyms"][:5]))
        if c.get("ia_category"):
            ia_context.append("Category: " + c["ia_category"])

        text_with_metadata = c["content"]
        if ia_context:
            text_with_metadata += "\n\n[" + " | ".join(ia_context) + "]"

        passages.append({"id": i, "text": text_with_metadata, "meta": c})

    expanded_query = " ".join(expand_query(query))
    results = _reranker.rerank(RerankRequest(query=expanded_query, passages=passages))

    reranked = []
    for result in results:
        if isinstance(result, dict):
            chunk = result.get("meta", {}).copy() if result.get("meta") else {}
            if not chunk:
                chunk = candidates[result.get("id", 0)].copy()
            chunk["rerank_score"] = float(result.get("score", 0.0))
        elif hasattr(result, "meta"):
            chunk = result.meta.copy()
            chunk["rerank_score"] = float(result.score)
        else:
            continue
        reranked.append(chunk)

    # Apply boosting (category, keywords, title) to FlashRank results
    for chunk in reranked:
        _apply_boosting(
            chunk,
            query_keywords,
            expanded_query_keywords,
            category_hint,
            strong_keywords,
        )

    reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    return reranked


def retrieve(
    query: str,
    top_k: int = TOP_K_RERANK,
    verbose: bool = False,
    filter_source: str | None = None,
) -> dict:
    """Pipeline complet retrieval V3+."""
    _load_indexes()

    # Validate and sanitize query
    try:
        query = validate_query(query)
    except ValueError as e:
        logger.error("Query validation failed: %s", e)
        return {
            "chunks": [],
            "low_confidence": True,
            "query": query,
            "best_score": 0.0,
            "error": str(e),
        }

    query_emb = _get_embedding(query)
    if query_emb is None:
        return {"chunks": [], "low_confidence": True, "query": query, "best_score": 0.0}

    # Validate and sanitize filter_source before using in ChromaDB query
    if filter_source:
        try:
            allowed_sources = _get_allowed_sources()
            filter_source = validate_filter_source(filter_source, allowed_sources)
        except ValueError as e:
            logger.error("filter_source validation failed: %s", e)
            return {
                "chunks": [],
                "low_confidence": True,
                "query": query,
                "best_score": 0.0,
                "error": str(e),
            }

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
        chroma_results = _chroma_search(query_emb, TOP_K_RETRIEVAL, query_text=query)

    if verbose:
        print("\n[ChromaDB V3+] top-5 :")
        for rank, (cid, score) in enumerate(chroma_results[:5]):
            chunk = _chunks[cid]
            ia_cat = chunk.get("ia_category", "N/A")
            print(
                f"   [{rank + 1}] sim={score:.3f} | cat={ia_cat} | {_chunks[cid]['title'][:50]}"
            )

    bm25_results = _bm25_search(query, TOP_K_RETRIEVAL)

    if verbose:
        print("\n[BM25 V3+] top-5 (query expansion):")
        for rank, (cid, score) in enumerate(bm25_results[:5]):
            print(f"   [{rank + 1}] score={score:.3f} | {_chunks[cid]['title'][:50]}")

    rrf_results = _reciprocal_rank_fusion(chroma_results, bm25_results)[:TOP_K_RRF]

    if verbose:
        print("\n[RRF V3+] top-5 :")
        for rank, (cid, score) in enumerate(rrf_results[:5]):
            print(f"   [{rank + 1}] rrf={score:.4f} | {_chunks[cid]['title'][:50]}")

    candidates = []
    for chunk_id, rrf_score in rrf_results:
        chunk = _chunks[chunk_id].copy()
        chunk["rrf_score"] = rrf_score
        chunk["chunk_id"] = chunk_id
        candidates.append(chunk)

    reranked = _rerank(query, candidates, verbose=verbose)
    final = reranked[:top_k]

    if verbose:
        print("\n[Reranking V3+] resultats finaux :")
        for rank, chunk in enumerate(final):
            code_icon = "[code]" if chunk["has_code"] else "      "
            ia_cat = chunk.get("ia_category", "N/A")
            score = chunk.get("rerank_score", 0)
            ia_matches = chunk.get("_ia_matches", 0)
            category_boost = chunk.get("_category_boost", 0)
            print(
                f"   [{rank + 1}] score={score:.3f} | ia_cat={ia_cat} | ia_matches={ia_matches} | cat_boost={category_boost:.1f} | {code_icon} | {chunk['title'][:40]}"
            )

    best_score = final[0].get("rerank_score", 0) if final else 0.0
    low_confidence = best_score < CONFIDENCE_THRESHOLD

    logger.debug("Score V3+: %.4f | low_confidence=%s", best_score, low_confidence)

    if not final and verbose:
        print("[WARN V3+] Aucun resultat, tentative avec requete simplifiee...")
        simple_query = " ".join([t for t in _tokenize(query) if len(t) > 3])
        if simple_query:
            return retrieve(
                simple_query, top_k=top_k, verbose=verbose, filter_source=filter_source
            )

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
    """Helper : retourne contexte formate pour LLM + sources."""
    result = retrieve(query, top_k=top_k, filter_source=filter_source)
    chunks = result["chunks"]

    if not chunks:
        return "", [], True

    parts = []
    for i, chunk in enumerate(chunks):
        source_label = f"[Source {i + 1}: {chunk['title']} - {chunk['url']}]"
        parts.append(f"{source_label}\n\n{chunk['content']}")

    context_str = "\n\n---\n\n".join(parts)

    sources = [
        {
            "title": chunk["title"],
            "url": chunk["url"],
            "source": chunk["source"],
            "score": round(chunk.get("rerank_score", chunk.get("rrf_score", 0)), 3),
            "has_code": chunk["has_code"],
            "ia_category": chunk.get("ia_category", "N/A"),
            "ia_keywords": chunk.get("ia_keywords", []),
        }
        for chunk in chunks
    ]

    return context_str, sources, result["low_confidence"]


if __name__ == "__main__":
    import sys

    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Comment configurer un health check HTTP ?"
    )
    print(f"\n[QUERY V3+] {query}\n")

    result = retrieve(query, verbose=True)

    if result["low_confidence"]:
        print("\n[WARN V3+] Confiance faible")

    print(f"\n[OK V3+] {len(result['chunks'])} chunks retournes")
    for i, chunk in enumerate(result["chunks"]):
        print(f"\n{'=' * 60}")
        print(f"Chunk V3+ {i + 1} | {chunk['title']}")
        print(f"Source   : {chunk['url']}")
        print(f"IA Cat   : {chunk.get('ia_category', 'N/A')}")
        print(f"IA Kw    : {', '.join(chunk.get('ia_keywords', [])[:5])}")
        print(f"Score    : {chunk.get('rerank_score', 0):.3f}")
        print(f"\n{chunk['content'][:300]}...")
