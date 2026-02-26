"""
config.py - Configuration centralisée pour HAProxy RAG

Tous les paramètres configurables sont définis ici avec leur documentation.
Les valeurs peuvent être surchargées par des variables d'environnement.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class OllamaConfig:
    """Configuration pour Ollama (embedding et LLM)."""
    url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    embed_model: str = os.getenv("EMBED_MODEL", "qwen3-embedding:8b")
    llm_model: str = os.getenv("LLM_MODEL", "gemma3:latest")
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "300"))
    max_retries: int = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
    rate_limit_calls_per_minute: int = int(os.getenv("OLLAMA_RATE_LIMIT", "30"))


@dataclass
class RetrievalConfig:
    """Configuration pour le retrieval hybride."""
    # Nombre de candidats initiaux par méthode (vector + BM25)
    top_k_retrieval: int = int(os.getenv("TOP_K_RETRIEVAL", "50"))
    
    # Nombre de résultats après fusion RRF
    top_k_rrf: int = int(os.getenv("TOP_K_RRF", "30"))
    
    # Nombre de résultats finaux après reranking
    top_k_rerank: int = int(os.getenv("TOP_K_RERANK", "10"))
    
    # Paramètre RRF (plus élevé = plus de poids au rang)
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    
    # Seuil de confiance minimum pour une réponse
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.0"))
    
    # Activer/désactiver FlashRank
    disable_flashrank: bool = os.getenv("DISABLE_FLASHRANK", "false").lower() == "true"


@dataclass
class ChunkingConfig:
    """Configuration pour le chunking des documents."""
    # Taille minimale d'un chunk (en caractères)
    min_chunk_chars: int = int(os.getenv("MIN_CHUNK_CHARS", "300"))
    
    # Taille maximale d'un chunk
    max_chunk_chars: int = int(os.getenv("MAX_CHUNK_CHARS", "800"))
    
    # Overlap entre chunks pour préserver le contexte
    overlap_chars: int = int(os.getenv("OVERLAP_CHARS", "150"))
    
    # Taille limite pour fusionner les sections courtes
    merge_threshold: int = int(os.getenv("MERGE_THRESHOLD", "500"))


@dataclass
class IndexConfig:
    """Configuration pour l'indexation."""
    # Répertoires et fichiers
    base_dir: Path = Path(os.getenv("HAPROXY_RAG_BASE_DIR", Path.cwd()))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", "data")))
    index_dir: Path = field(default_factory=lambda: Path(os.getenv("INDEX_DIR", "index_v3")))
    
    # Noms de collection et fichiers
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "haproxy_docs_v3")
    chunks_file: str = os.getenv("CHUNKS_FILE", "chunks_v2.jsonl")
    bm25_file: str = os.getenv("BM25_FILE", "bm25.pkl")
    chunks_pkl: str = os.getenv("CHUNKS_PKL", "chunks.pkl")
    
    # Batch size pour l'embedding
    batch_size: int = int(os.getenv("EMBED_BATCH_SIZE", "100"))
    
    @property
    def chroma_dir(self) -> Path:
        return self.index_dir / "chroma"
    
    @property
    def data_path(self) -> Path:
        return self.base_dir / self.data_dir
    
    @property
    def index_path(self) -> Path:
        return self.base_dir / self.index_dir


@dataclass
class LLMConfig:
    """Configuration pour la génération LLM."""
    # Modèle par défaut
    default_model: str = os.getenv("DEFAULT_MODEL", "gemma3:latest")
    
    # Limite de contexte envoyé au LLM (en caractères)
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "4000"))
    
    # Température par défaut (faible pour rester factuel)
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    
    # Rate limiting pour les appels LLM
    rate_limit_calls_per_minute: int = int(os.getenv("LLM_RATE_LIMIT", "20"))


@dataclass
class ValidationConfig:
    """Configuration pour la validation des entrées."""
    # Longueur maximale des requêtes utilisateur
    max_query_length: int = int(os.getenv("MAX_QUERY_LENGTH", "2000"))
    
    # Longueur maximale des metadata
    max_metadata_length: int = int(os.getenv("MAX_METADATA_LENGTH", "500"))
    
    # Nombre maximum d'items dans une liste de metadata
    max_metadata_items: int = int(os.getenv("MAX_METADATA_ITEMS", "20"))
    
    # Longueur maximale par item de metadata
    max_metadata_item_length: int = int(os.getenv("MAX_METADATA_ITEM_LENGTH", "100"))


@dataclass
class LoggingConfig:
    """Configuration pour le logging."""
    # Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Fichier de log (optionnel)
    log_file: str = os.getenv("LOG_FILE", "")


# Instances globales avec valeurs par défaut
ollama_config = OllamaConfig()
retrieval_config = RetrievalConfig()
chunking_config = ChunkingConfig()
index_config = IndexConfig()
llm_config = LLMConfig()
validation_config = ValidationConfig()
logging_config = LoggingConfig()


# Aliases pour compatibilité ascendante (à déprécier)
OLLAMA_URL = ollama_config.url
EMBED_MODEL = ollama_config.embed_model
DEFAULT_MODEL = llm_config.default_model
TOP_K_RETRIEVAL = retrieval_config.top_k_retrieval
TOP_K_RRF = retrieval_config.top_k_rrf
TOP_K_RERANK = retrieval_config.top_k_rerank
RRF_K = retrieval_config.rrf_k
CONFIDENCE_THRESHOLD = retrieval_config.confidence_threshold
