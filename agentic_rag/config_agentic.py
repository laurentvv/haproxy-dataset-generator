"""
Configuration centralisée pour le système RAG agentic.

Ce module contient tous les paramètres de configuration
pour les différents composants du système.
"""

from pathlib import Path
from typing import Any

# Chemins de base
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data_agentic'
INDEX_DIR = BASE_DIR / 'index_agentic'
CHROMA_DIR = INDEX_DIR / 'chroma_db'
PARENT_STORE_DIR = BASE_DIR / 'parent_store'

# Configuration scraping
SCRAPER_CONFIG: dict[str, Any] = {
    'base_url': 'https://docs.haproxy.org/',
    'version': '3.2',
    'max_pages': 1000,
    'timeout': 30,
    'user_agent': 'Mozilla/5.0 (compatible; HAProxyAgenticRAG/0.1.0)',
}

# Variables pour le scraping
HAPROXY_BASE_URL = SCRAPER_CONFIG['base_url'] + SCRAPER_CONFIG['version'] + '/'
SCRAPED_PAGES_DIR = DATA_DIR / 'scraped_pages'
SCRAPED_PAGES_PATH = SCRAPED_PAGES_DIR / f'scraped_{SCRAPER_CONFIG["version"]}.json'
HIERARCHY_REPORT_PATH = DATA_DIR / 'hierarchy_report.json'
SCRAPING_DIFF_REPORT_PATH = DATA_DIR / 'scraping_diff_report.json'

# Configuration chunking parent/child
CHUNKING_CONFIG: dict[str, Any] = {
    'parent_max_tokens': 4000,
    'child_max_tokens': 500,
    'chunk_overlap': 50,
    'min_chunk_size': 100,
}

# Variables pour le chunking
CHILD_CHUNK_SIZE = CHUNKING_CONFIG['child_max_tokens']
CHILD_CHUNK_OVERLAP = CHUNKING_CONFIG['chunk_overlap']
MIN_PARENT_SIZE = 100
MAX_PARENT_SIZE = CHUNKING_CONFIG['parent_max_tokens']
CHUNKS_CHILD_PATH = DATA_DIR / 'chunks_child.json'

# Configuration ChromaDB
CHROMA_CONFIG: dict[str, Any] = {
    'collection_name': 'haproxy_child_chunks',
    'embedding_model': 'qwen3-embedding:8b',  # Identique au projet principal
    'persist_directory': str(CHROMA_DIR),
}

# Variables pour l'indexation ChromaDB
COLLECTION_NAME = CHROMA_CONFIG['collection_name']
EMBEDDING_MODEL = CHROMA_CONFIG['embedding_model']

# Configuration LangGraph
LANGGRAPH_CONFIG: dict[str, Any] = {
    'max_retrieval_steps': 3,
    'max_refinement_steps': 2,
    'temperature': 0.1,
    'max_tokens': 2000,
}

# Configuration retrieval
DEFAULT_K_CHILD = 5
DEFAULT_K_MMR = 5
MMR_FETCH_K = 20
SCORE_THRESHOLD = 0.7

# Configuration LLM
LLM_CONFIG: dict[str, Any] = {
    'model': 'qwen3:latest',  # Modèle de référence pour les stats de perf
    'temperature': 0.1,
    'top_p': 0.9,
    'num_ctx': 4096,
}

# Configuration Gradio
GRADIO_CONFIG: dict[str, Any] = {
    'title': 'HAProxy Agentic RAG Chatbot',
    'description': 'Assistant intelligent basé sur LangGraph pour la documentation HAProxy 3.2',
    'port': 7861,
    'share': False,
}

# Configuration benchmark
BENCHMARK_CONFIG: dict[str, Any] = {
    'num_questions': 50,
    'metrics': ['precision', 'recall', 'f1', 'latency'],
    'output_format': 'json',
}

# Configuration export dataset
EXPORT_CONFIG: dict[str, Any] = {
    'output_format': 'jsonl',
    'include_metadata': True,
    'include_sources': True,
}


def get_config(section: str) -> dict[str, Any]:
    """
    Récupère une section de configuration.

    Args:
        section: Nom de la section de configuration.

    Returns:
        Dictionnaire de configuration pour la section demandée.
    """
    configs = {
        'scraper': SCRAPER_CONFIG,
        'chunking': CHUNKING_CONFIG,
        'chroma': CHROMA_CONFIG,
        'langgraph': LANGGRAPH_CONFIG,
        'llm': LLM_CONFIG,
        'gradio': GRADIO_CONFIG,
        'benchmark': BENCHMARK_CONFIG,
        'export': EXPORT_CONFIG,
    }
    return configs.get(section, {})
