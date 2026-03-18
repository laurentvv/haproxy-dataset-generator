"""
Outils de retrieval pour le système RAG agentic.
OPTIMISÉ : + Metadata filtering + SECTION_HINTS + Gemini Embeddings
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.tools import tool

from agentic_rag.config_agentic import (
    DEFAULT_K_CHILD,
    EMBEDDING_MODEL,
    GOOGLE_API_KEY,
    HYBRID_RRF_K,
    HYBRID_TOP_K,
    INDEX_DIR,
)
from agentic_rag.db.chroma_manager import ChromaManager
from agentic_rag.db.parent_store_manager import ParentStoreManager

logger = logging.getLogger(__name__)

# SECTION_HINTS (conservé pour le filtrage si nécessaire)
SECTION_HINTS = {
    "backend": ["5.1", "5.2", "5.3", "4.1", "4.3"],
    "server": ["5.1", "5.2", "5.3"],
    "balance": ["5.1", "5.2", "5.3"],
    "check": ["5.2", "5.3", "5.4"],
    "healthcheck": ["5.2", "5.3", "5.4"],
    "http-check": ["5.2", "5.3", "5.4"],
    "stick-table": ["11.1", "11.2", "7.3", "7.4", "7.5"],
    "stick": ["11.1", "11.2", "7.3"],
    "table": ["11.1", "11.2"],
    "track-sc": ["11.1", "11.2", "7.3"],
    "track": ["11.1", "11.2"],
    "conn_rate": ["11.1", "11.2", "7.3"],
    "conn": ["11.1", "11.2"],
    "http_req_rate": ["11.1", "11.2", "7.3"],
    "http_req": ["11.1", "11.2"],
    "req_rate": ["11.1", "11.2"],
    "rate": ["11.1", "11.2", "7.3"],
    "limit": ["11.1", "11.2", "7.3", "7.4"],
    "deny": ["7.3", "7.4", "7.5", "11.1"],
    "acl": ["7.1", "7.2", "7.3", "7.4", "7.5", "8.1", "8.2"],
    "path": ["7.1", "7.2", "7.3", "7.4"],
    "url": ["7.1", "7.2", "7.3", "7.4"],
    "if": ["7.1", "7.2", "7.3", "7.4"],
    "ssl": ["9.1", "9.2", "9.3"],
    "bind": ["5.1", "5.2", "9.1", "9.2"],
    "crt": ["9.1", "9.2", "9.3"],
    "cert": ["9.1", "9.2", "9.3"],
    "pem": ["9.1", "9.2", "9.3"],
    "timeout": ["3.1", "3.2", "3.3", "5.2", "5.3"],
    "option": ["5.1", "5.2", "5.3"],
    "inter": ["5.2", "5.3"],
    "fall": ["5.2", "5.3"],
    "rise": ["5.2", "5.3"],
    "ip": ["11.1", "11.2", "7.3"],
    "connection": ["11.1", "11.2", "7.3"],
    "request": ["7.1", "7.2", "7.3", "11.1", "11.2"],
    "http": ["7.1", "7.2", "7.3", "11.1", "11.2"],
    "dst_port": ["7.1", "7.2", "7.3"],
    "port": ["7.1", "7.2", "7.3", "5.1", "5.2"],
    "destination": ["7.1", "7.2", "7.3"],
    "status": ["7.1", "7.2", "7.5"],
    "code": ["7.1", "7.2", "7.5"],
    "response": ["7.1", "7.2", "7.5", "3.3"],
    "src": ["7.1", "7.2", "7.3"],
    "source": ["7.1", "7.2", "7.3", "5.3"],
    "dst": ["7.1", "7.2", "7.3"],
    "host": ["7.1", "7.2", "7.3"],
    "domain": ["7.1", "7.2", "7.3"],
    "method": ["7.1", "7.2", "7.3"],
    "hdr": ["7.1", "7.2", "7.3", "7.4"],
    "header": ["7.1", "7.2", "7.3", "7.4"],
    "path_beg": ["7.1", "7.2"],
    "path_end": ["7.1", "7.2"],
    "regex": ["7.1", "7.2", "7.5"],
    "regexp": ["7.1", "7.2", "7.5"],
    "weight": ["5.1", "5.2", "5.3"],
    "backup": ["5.1", "5.2", "5.3"],
    "failover": ["5.1", "5.2", "5.3"],
    "disabled": ["5.1", "5.2", "5.3"],
    "disable": ["5.1", "5.2", "5.3"],
    "address": ["5.1", "5.2", "5.3"],
    "stats": ["3.3", "4.2"],
    "enable": ["3.3", "4.2"],
    "uri": ["3.3", "4.2"],
    "listen": ["4.1", "4.2", "4.3"],
    "auth": ["4.2"],
    "password": ["4.2"],
    "realm": ["4.2"],
    "refresh": ["4.2"],
    "socket": ["4.2"],
    "hide": ["4.2"],
    "log": ["3.1", "3.2", "8.1"],
    "global": ["3.1", "3.2"],
    "syslog": ["3.1", "3.2"],
    "facility": ["3.1", "3.2"],
    "stdout": ["3.1", "3.2"],
    "stderr": ["3.1", "3.2"],
    "local0": ["3.1", "3.2"],
    "format": ["8.1", "8.2"],
    "mode": ["3.1", "3.2", "3.3"],
    "tcp": ["3.1", "3.2", "3.3"],
    "health": ["3.1", "3.2"],
    "layer4": ["3.1", "3.2"],
    "layer7": ["3.1", "3.2"],
    "verify": ["9.1", "9.2", "9.3"],
    "ca-file": ["9.1", "9.2", "9.3"],
    "cafile": ["9.1", "9.2", "9.3"],
    "certificate": ["9.1", "9.2", "9.3"],
    "crt-list": ["9.1", "9.2", "9.3"],
    "list": ["9.1", "9.2", "9.3"],
    "client": ["9.1", "9.2", "9.3"],
    "required": ["9.1", "9.2", "9.3"],
    "sni": ["9.1", "9.2", "9.3"],
    "force-tlsv": ["9.1", "9.2", "9.3"],
    "tls": ["9.1", "9.2", "9.3"],
    "version": ["9.1", "9.2", "9.3"],
    "default-bind": ["3.1", "9.1"],
    "deny_status": ["7.3", "7.4", "7.5"],
    "429": ["7.3", "7.4", "7.5"],
    "too-many": ["7.3", "7.4", "7.5"],
    "period": ["11.1", "11.2", "7.3"],
    "entries": ["11.1", "11.2"],
    "size": ["11.1", "11.2"],
    "expire": ["11.1", "11.2"],
    "store": ["11.1", "11.2", "7.3"],
    "type": ["11.1", "11.2", "7.3"],
    "string": ["11.1", "11.2", "7.3"],
    "integer": ["11.1", "11.2", "7.3"],
    "frontend": ["5.1", "5.2", "4.1"],
    "algorithm": ["5.1", "5.2", "5.3"],
    "roundrobin": ["5.1", "5.2", "5.3"],
    "leastconn": ["5.1", "5.2", "5.3"],
    "hash": ["5.1", "5.2", "5.3"],
    "persistence": ["5.3", "11.1", "11.2"],
    "name": ["3.1", "5.1"],
    "section": ["3.1", "4.1", "5.1"],
    "interval": ["5.2", "5.3"],
    "time": ["3.1", "3.2", "3.3"],
    "s": ["3.1", "3.2", "3.3"],
    "m": ["3.1", "3.2", "3.3"],
    "begin": ["7.1", "7.2"],
    "end": ["7.1", "7.2"],
    "pattern": ["7.1", "7.2", "7.5"],
    "negation": ["7.1", "7.2"],
    "not": ["7.1", "7.2"],
    "unless": ["7.1", "7.2", "7.3"],
    "counter": ["11.1", "11.2", "7.3"],
    "sc": ["11.1", "11.2", "7.3"],
    "stickiness": ["11.1", "11.2", "3.3"],
    "load": ["3.3", "5.1", "5.2"],
    "balancing": ["5.1", "5.2", "5.3"],
    "configure": ["3.1", "3.2"],
    "configurer": ["3.1", "3.2"],
    "comment": ["3.1", "3.2"],
    "example": ["3.1", "3.2"],
    "syntaxe": ["3.1", "3.2"],
    "syntax": ["3.1", "3.2"],
    "disponible": ["3.1", "3.2", "3.3"],
    "available": ["3.1", "3.2", "3.3"],
    "utiliser": ["3.1", "3.2"],
    "utilize": ["3.1", "3.2"],
    "specify": ["3.1", "3.2"],
    "spécifier": ["3.1", "3.2"],
    "mesurer": ["11.1", "11.2"],
    "measure": ["11.1", "11.2"],
    "mesure": ["11.1", "11.2"],
    "taux": ["11.1", "11.2", "7.3"],
    "rate": ["11.1", "11.2", "7.3"],
    "retourner": ["7.3", "7.4"],
    "return": ["7.3", "7.4"],
    "temporary": ["5.1", "5.2"],
    "temporairement": ["5.1", "5.2"],
    "personnalisé": ["5.2", "5.3"],
    "personnalise": ["5.2", "5.3"],
    "custom": ["5.2", "5.3"],
    "requete": ["7.1", "7.2", "11.1"],
    "requête": ["7.1", "7.2", "11.1"],
    "request": ["7.1", "7.2", "11.1"],
    "connexion": ["11.1", "11.2", "7.3"],
    "connection": ["11.1", "11.2", "7.3"],
    "connect": ["3.1", "3.2", "5.2"],
    "client": ["3.1", "3.2", "9.1"],
    "queue": ["3.1", "3.2", "3.3"],
    "waiting": ["3.1", "3.2", "3.3"],
    "tunnel": ["3.1", "3.2", "3.3"],
    "inactivity": ["3.1", "3.2", "3.3"],
    "inactive": ["3.1", "3.2", "3.3"],
    "http-request": ["7.1", "7.2", "7.3"],
    "http-request-timeout": ["3.1", "3.2"],
    "client-fin": ["3.1", "3.2"],
    "server-fin": ["3.1", "3.2"],
    "http-keep-alive": ["3.1", "3.2"],
    "keep-alive": ["3.1", "3.2"],
    "forwardfor": ["3.3", "7.4"],
    "x-forwarded-for": ["3.3", "7.4"],
    "option": ["5.1", "5.2", "5.3"],
    "httplog": ["8.1", "8.2"],
    "dontlognull": ["8.1", "8.2"],
    "redispatch": ["5.2", "5.3"],
    "maxconn": ["3.1", "3.2", "5.1"],
    "nbproc": ["3.1", "3.2"],
    "nbthread": ["3.1", "3.2"],
    "gzip": ["3.3", "8.3"],
    "compression": ["3.3", "8.3"],
    "cookie": ["5.3", "11.1"],
    "insert": ["5.3", "11.1"],
    "indirect": ["5.3"],
    "nocache": ["5.3"],
    "postonly": ["5.3"],
    "preserve": ["5.3"],
    "secure": ["9.1", "9.2"],
    "httponly": ["9.1", "9.2"],
    "same-site": ["9.1", "9.2"],
    "http-response": ["7.1", "7.2", "7.4"],
    "set-header": ["7.4"],
    "add-header": ["7.4"],
    "set-cookie": ["7.4"],
    "add-cookie": ["7.4"],
    "redirect": ["7.4", "7.5"],
    "location": ["7.4", "7.5"],
    "prefix": ["7.4", "7.5"],
    "scheme": ["7.4", "7.5"],
    "drop": ["7.3", "7.4"],
    "allow": ["7.3", "7.4"],
    "abort": ["7.3", "7.4"],
    "tarpit": ["7.3", "7.4"],
    "converter": ["7.1", "7.2", "7.5"],
    "lower": ["7.1", "7.2"],
    "upper": ["7.1", "7.2"],
    "extract": ["7.1", "7.2"],
    "tcp-check": ["5.2", "5.3", "5.4"],
    "429": ["7.3", "7.4", "7.5"],
    "period": ["11.1", "11.2", "7.3"],
    "entries": ["11.1", "11.2"],
    "size": ["11.1", "11.2"],
    "expire": ["11.1", "11.2"],
    "store": ["11.1", "11.2", "7.3"],
    "type": ["11.1", "11.2", "7.3"],
    "string": ["11.1", "11.2", "7.3"],
    "integer": ["11.1", "11.2", "7.3"],
    "frontend": ["5.1", "5.2", "4.1"],
    "certificates": ["9.1", "9.2", "9.3"],
    "default-bind": ["3.1", "9.1"],
    "listen": ["4.1", "4.2", "4.3"],
    "enable": ["3.3", "4.2"],
    "realm": ["4.2"],
    "hide": ["4.2"],
    "chmod": ["4.2"],
    "syslog": ["3.1", "3.2"],
    "facility": ["3.1", "3.2"],
    "fd@": ["3.1", "3.2"],
    "custom": ["8.1", "8.2"],
    "disable": ["3.1", "3.2"],
    "option httpchk": ["5.2", "5.3"],
    "GET": ["5.2", "5.3"],
    "layer4": ["3.1", "3.2"],
    "layer7": ["3.1", "3.2"],
    "persistence": ["5.3", "11.1", "11.2"],
    "disabled": ["5.1", "5.2", "5.3"],
    "deny_status": ["7.3", "7.4", "7.5"],
    "combine": ["4.1", "4.2"],
    "file": ["7.1", "7.2"],
    "variable": ["7.1", "7.2"],
    "fetch": ["7.1", "7.2"],
    "add": ["7.1", "7.2", "7.4"],
    "remove": ["7.1", "7.2", "7.4"],
}


def _get_target_sections(query: str) -> list[str]:
    """Extrait les sections cibles d'une requête."""
    target_sections = []
    query_lower = query.lower()
    for keyword, sections in SECTION_HINTS.items():
        if keyword in query_lower:
            target_sections.extend(sections)
    return target_sections


@tool
def search_child_chunks(query: str, k: int = DEFAULT_K_CHILD, use_hybrid: bool = True) -> dict:
    """Recherche hybride (Vector + BM25 + RRF) dans les chunks enfants avec Gemini."""
    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY non configurée")

        embeddings_model = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )

        print(f"DEBUG search_child_chunks (Gemini): query='{query}'", flush=True)

        query_embedding = embeddings_model.embed_query(query)
        chroma_manager = ChromaManager()

        if use_hybrid:
            try:
                from hybrid_retriever import HybridRetriever

                # Charger les chunks depuis ChromaDB pour BM25 (cache)
                if not hasattr(search_child_chunks, '_chunks_cache'):
                    # Pour Gemini, on récupère un pool plus large
                    all_results = chroma_manager.query_with_embedding(
                        query_embedding=query_embedding,
                        n_results=1000
                    )
                    search_child_chunks._chunks_cache = all_results

                chunks = search_child_chunks._chunks_cache

                # Utiliser l'index BM25 gemini
                bm25_path = INDEX_DIR / 'bm25_index_gemini.pkl'
                if not bm25_path.exists():
                    bm25_path = INDEX_DIR / 'bm25_index.pkl' # Fallback

                retriever = HybridRetriever(
                    chroma_manager,
                    chunks,
                    bm25_index_path=str(bm25_path)
                )

                results = retriever.hybrid_search(
                    query=query,
                    query_embedding=query_embedding,
                    k=HYBRID_TOP_K,
                    rrf_k=HYBRID_RRF_K
                )
            except Exception as e:
                logger.warning(f'Hybrid retrieval failed: {e}, fallback to vector-only')
                use_hybrid = False

        if not use_hybrid:
            results = chroma_manager.query_with_embedding(
                query_embedding=query_embedding, n_results=k * 3
            )

        target_sections = _get_target_sections(query)

        if not use_hybrid:
            # Filtrage post-retrieval pour vector-only
            filtered_results = []
            for r in results:
                score = 1.0 - r.get('score', 1.0)
                metadata = r.get('metadata', {})
                section_path = metadata.get('section_path', [])

                section_boost = 0.0
                for section in section_path:
                    for target in target_sections:
                        if target in section:
                            section_boost = 0.15
                            break

                source = metadata.get('source', '')
                source_boost = 0.0
                if 'configuration.html' in source:
                    source_boost = 0.25
                elif 'intro.html' in source:
                    source_boost = -0.15

                total_boost = section_boost + source_boost
                if score + total_boost >= 0.15:
                    filtered_results.append(r)

            if not filtered_results and results:
                filtered_results = results[:k]
            results = filtered_results[:k]
        else:
            filtered_results = results

        parent_ids = []
        sources = []
        for result in filtered_results:
            metadata = result.get('metadata', {})
            parent_id = metadata.get('parent_id')
            source = metadata.get('source', 'unknown')
            if parent_id and parent_id not in parent_ids:
                parent_ids.append(parent_id)
            if source and source not in sources:
                sources.append(source)

        return {'chunks': filtered_results, 'parent_ids': parent_ids, 'sources': sources, 'query': query}
    except Exception as e:
        logger.error(f'Error in search_child_chunks: {e}')
        return {'chunks': [], 'parent_ids': [], 'sources': [], 'query': query, 'error': str(e)}


@tool
def retrieve_parent_chunks(parent_ids: list[str]) -> dict:
    """Récupère les chunks parents complets à partir de leurs IDs."""
    try:
        parent_manager = ParentStoreManager()
        parents = parent_manager.get_parents(parent_ids)
        parent_contents = []
        sources = []
        for parent in parents:
            if parent:
                content = parent.get('page_content', '') or parent.get('content', '')
                parent_contents.append({
                    'id': parent.get('id'),
                    'content': content,
                    'metadata': parent.get('metadata', {})
                })
                source = parent.get('metadata', {}).get('source', 'unknown')
                if source and source not in sources:
                    sources.append(source)
        return {'parents': parent_contents, 'sources': sources}
    except Exception as e:
        logger.error(f'Error in retrieve_parent_chunks: {e}')
        return {'parents': [], 'sources': [], 'error': str(e)}


@tool
def validate_haproxy_config(config_block: str) -> dict:
    """Valide un bloc de configuration HAProxy."""
    try:
        root_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(root_dir))
        from haproxy_validator import HAProxyValidator
        validator = HAProxyValidator()
        result = validator.validate(config_block)
        return {
            'is_valid': result.is_valid,
            'errors': [{'line': e.line, 'message': e.message, 'severity': e.severity.value, 'suggestion': e.suggestion} for e in result.errors],
            'warnings': [{'line': w.line, 'message': w.message, 'severity': w.severity.value, 'suggestion': w.suggestion} for w in result.warnings],
        }
    except Exception as e:
        logger.error(f'Error in validate_haproxy_config: {e}')
        return {'is_valid': False, 'errors': [{'message': f'Validation error: {e}', 'severity': 'error'}], 'warnings': []}
