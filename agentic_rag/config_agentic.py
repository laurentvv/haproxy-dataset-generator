"""
Configuration centralisée pour le système RAG agentic.

Ce module contient tous les paramètres de configuration
pour les différents composants du système.
"""

import os
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
# Stratégie parent/child pour le RAG :
# - Parent : Document complet (max 4000 chars) pour le contexte
# - Child : Chunk plus petit pour la recherche vectorielle
# OPTIMISATION V2 : Chunking plus fin pour meilleure granularité
#   - child_max_chars: 500 → 300 (plus de chunks, meilleure précision)
#   - chunk_overlap: 100 → 150 (50% pour préserver le contexte)
#   - min_child_size: 50 → 30 (garder plus de petits chunks pertinents)
CHUNKING_CONFIG: dict[str, Any] = {
    'parent_max_chars': 4000,       # Taille max d'un parent en caractères
    'child_max_chars': 300,         # OPTIM: 500 → 300 (plus de granularité)
    'chunk_overlap': 150,           # OPTIM: 100 → 150 (50% overlap, meilleur contexte)
    'min_chunk_size': 100,          # Taille min d'un chunk à considérer
    'min_child_size': 30,           # OPTIM: 50 → 30 (garder petits chunks pertinents)
    'max_children_per_parent': 30,  # OPTIM: 20 → 30 (plus d'enfants par parent)
}

# Variables pour le chunking
CHILD_CHUNK_SIZE = CHUNKING_CONFIG['child_max_chars']
CHILD_CHUNK_OVERLAP = CHUNKING_CONFIG['chunk_overlap']
MIN_PARENT_SIZE = CHUNKING_CONFIG['min_chunk_size']  # Utilise la valeur centralisée
MAX_PARENT_SIZE = CHUNKING_CONFIG['parent_max_chars']
MIN_CHILD_SIZE = CHUNKING_CONFIG['min_child_size']  # Ajouté pour éviter les magic numbers
MAX_CHILDREN_PER_PARENT = CHUNKING_CONFIG['max_children_per_parent']  # Ajouté pour éviter les magic numbers
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
# OPTIMISATION V2 : Plus de résultats pour meilleur retrieval
DEFAULT_K_CHILD = 10       # OPTIM: 5 → 10 (plus de candidats)
DEFAULT_K_MMR = 10         # OPTIM: 5 → 10 (diversité MMR)
MMR_FETCH_K = 30           # OPTIM: 20 → 30 (pool plus large)
SCORE_THRESHOLD = 0.5      # OPTIM: 0.7 → 0.5 (seuil plus permissif)

# OPTIMISATION V3 : Hybrid retrieval (Vector + BM25 + RRF)
HYBRID_RETRIEVAL_ENABLED = True
HYBRID_TOP_K = 15          # Nombre de résultats après fusion RRF
HYBRID_RRF_K = 60          # Paramètre RRF (comme V3)
HYBRID_VECTOR_WEIGHT = 0.5  # Poids du vector (0.5 = égal avec BM25)
HYBRID_BM25_WEIGHT = 0.5    # Poids de BM25

# Configuration LLM
# Modèles alignés avec le RAG standard (config.py) pour comparaison équitable
LLM_CONFIG: dict[str, Any] = {
    'model': os.getenv('LLM_MODEL', 'qwen3.5:9b'),  # Même modèle que RAG standard
    'temperature': 0.1,
    'top_p': 0.9,
    'num_ctx': 4096,
}

# Configuration Ollama (alignée avec config.py)
OLLAMA_CONFIG: dict[str, Any] = {
    'url': os.getenv('OLLAMA_URL', 'http://localhost:11434'),
    'embed_model': os.getenv('EMBED_MODEL', 'qwen3-embedding:8b'),
    'llm_model': os.getenv('LLM_MODEL', 'qwen3.5:9b'),
    'fast_model': os.getenv('FAST_MODEL', 'lfm2.5-thinking:1.2b-bf16'),
    'timeout': int(os.getenv('OLLAMA_TIMEOUT', '120')),
    'llm_timeout': int(os.getenv('LLM_TIMEOUT', '300')),
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
