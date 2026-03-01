"""
Outils de retrieval pour le système RAG agentic.
OPTIMISÉ : + Metadata filtering + SECTION_HINTS
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.tools import tool

from config_agentic import DEFAULT_K_CHILD, SCORE_THRESHOLD
from db.chroma_manager import ChromaManager
from db.parent_store_manager import ParentStoreManager

logger = logging.getLogger(__name__)

# SECTION_HINTS pour améliorer le retrieval (copié de V3)
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
    # Health check keywords
    "inter": ["5.2", "5.3"],
    "fall": ["5.2", "5.3"],
    "rise": ["5.2", "5.3"],
    # IP/connection
    "ip": ["11.1", "11.2", "7.3"],
    "connection": ["11.1", "11.2", "7.3"],
    "request": ["7.1", "7.2", "7.3", "11.1", "11.2"],
    "http": ["7.1", "7.2", "7.3", "11.1", "11.2"],
    # ACL extensions (for failed questions)
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
    # Server options
    "weight": ["5.1", "5.2", "5.3"],
    "backup": ["5.1", "5.2", "5.3"],
    "failover": ["5.1", "5.2", "5.3"],
    "disabled": ["5.1", "5.2", "5.3"],
    "disable": ["5.1", "5.2", "5.3"],
    "address": ["5.1", "5.2", "5.3"],
    # Stats
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
    # Logs
    "log": ["3.1", "3.2", "8.1"],
    "global": ["3.1", "3.2"],
    "syslog": ["3.1", "3.2"],
    "facility": ["3.1", "3.2"],
    "stdout": ["3.1", "3.2"],
    "stderr": ["3.1", "3.2"],
    "local0": ["3.1", "3.2"],
    "format": ["8.1", "8.2"],
    # TCP/Mode
    "mode": ["3.1", "3.2", "3.3"],
    "tcp": ["3.1", "3.2", "3.3"],
    "health": ["3.1", "3.2"],
    "layer4": ["3.1", "3.2"],
    "layer7": ["3.1", "3.2"],
    # SSL extensions
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
    # Rate limiting / deny
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
    # Frontend
    "frontend": ["5.1", "5.2", "4.1"],
    # Algorithm
    "algorithm": ["5.1", "5.2", "5.3"],
    "roundrobin": ["5.1", "5.2", "5.3"],
    "leastconn": ["5.1", "5.2", "5.3"],
    "hash": ["5.1", "5.2", "5.3"],
    "persistence": ["5.3", "11.1", "11.2"],
    # General
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
    "utiliser": ["7.1", "7.2"],
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
def search_child_chunks(query: str, k: int = DEFAULT_K_CHILD) -> dict:
    """Recherche vectorielle dans les chunks enfants de ChromaDB.
    OPTIMISÉ : + Metadata filtering avec SECTION_HINTS
    """
    try:
        from langchain_ollama import OllamaEmbeddings
        embeddings_model = OllamaEmbeddings(model='qwen3-embedding:8b')
        query_embedding = embeddings_model.embed_query(query)
        chroma_manager = ChromaManager()

        # Récupérer plus de candidats pour le filtering (3x pour avoir du choix)
        results = chroma_manager.query_with_embedding(
            query_embedding=query_embedding, n_results=k * 3
        )

        # Déterminer sections cibles
        target_sections = _get_target_sections(query)
        logger.info(f'Target sections for query: {target_sections}')

        # Filtrer avec boost de score
        filtered_results = []
        for r in results:
            score = 1.0 - r.get('score', 1.0)
            metadata = r.get('metadata', {})

            # Boost score si section cible
            section_path = metadata.get('section_path', [])
            section_boost = 0.0
            for section in section_path:
                for target in target_sections:
                    if target in section:
                        section_boost = 0.15
                        break

            # Threshold dynamique avec boost (plus permissif si pas de résultats)
            threshold = 0.20
            if len(filtered_results) < k and score + section_boost >= threshold - 0.10:
                filtered_results.append(r)
            elif score + section_boost >= threshold:
                filtered_results.append(r)

        # Si toujours pas de résultats, retourner les meilleurs sans filtering
        if not filtered_results and results:
            logger.warning(f'No results after filtering, returning top {k} raw results')
            filtered_results = results[:k]

        # Garder top k
        filtered_results = filtered_results[:k]

        # Extraire parent_ids et sources
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

        logger.info(f'Retrieved {len(filtered_results)} chunks for query: {query[:50]}...')
        logger.info(f'Parent IDs: {parent_ids}')
        logger.info(f'Sources: {sources}')
        return {'chunks': filtered_results, 'parent_ids': parent_ids, 'sources': sources, 'query': query}
    except Exception as e:
        logger.error(f'Error in search_child_chunks: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return {'chunks': [], 'parent_ids': [], 'sources': [], 'query': query, 'error': str(e)}


@tool
def retrieve_parent_chunks(parent_ids: list[str]) -> dict:
    """Récupère les chunks parents complets à partir de leurs IDs."""
    try:
        logger.info(f'retrieve_parent_chunks appelé avec: {parent_ids}')
        parent_manager = ParentStoreManager()
        parents = parent_manager.get_parents(parent_ids)
        logger.info(f'{len(parents)} parents récupérés')
        parent_contents = []
        sources = []
        total_chars = 0
        for parent in parents:
            if parent:
                # CORRECTION: 'page_content' au lieu de 'content'
                content = parent.get('page_content', '') or parent.get('content', '')
                total_chars += len(content)
                logger.info(f'Parent {parent.get("id")}: {len(content)} chars')
                parent_contents.append({
                    'id': parent.get('id'),
                    'content': content,
                    'metadata': parent.get('metadata', {})
                })
                source = parent.get('metadata', {}).get('source', 'unknown')
                if source and source not in sources:
                    sources.append(source)
        logger.info(f'Total: {len(parent_contents)} parents, {total_chars} chars')
        result = {'parents': parent_contents, 'sources': sources}
        logger.info(f'retrieve_parent_chunks retourne: {len(parent_contents)} parents')
        return result
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
        logger.info(f'Validation result: valid={result.is_valid}')
        return {
            'is_valid': result.is_valid,
            'errors': [{'line': e.line, 'message': e.message, 'severity': e.severity.value, 'suggestion': e.suggestion} for e in result.errors],
            'warnings': [{'line': w.line, 'message': w.message, 'severity': w.severity.value, 'suggestion': w.suggestion} for w in result.warnings],
        }
    except Exception as e:
        logger.error(f'Error in validate_haproxy_config: {e}')
        return {'is_valid': False, 'errors': [{'message': f'Validation error: {e}', 'severity': 'error'}], 'warnings': []}
