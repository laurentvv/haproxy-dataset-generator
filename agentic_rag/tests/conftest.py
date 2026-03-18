"""Fixtures pytest pour les tests du système RAG agentic (Gemini)."""

import shutil
import tempfile
from pathlib import Path
import pytest
from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from agentic_rag.config_agentic import EMBEDDING_MODEL, LLM_CONFIG, GOOGLE_API_KEY
from agentic_rag.db.chroma_manager import ChromaManager
from agentic_rag.db.parent_store_manager import ParentStoreManager

@pytest.fixture
def temp_dir():
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_embeddings():
    """Mock des embeddings pour les tests (utilisation d'une clé fictive)."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY or "dummy_key"
    )

@pytest.fixture
def chroma_manager(temp_dir, mock_embeddings):
    manager = ChromaManager(
        persist_directory=temp_dir / 'chroma',
        collection_name='test_collection',
    )
    yield manager

@pytest.fixture
def parent_store_manager(temp_dir):
    return ParentStoreManager(store_dir=temp_dir / 'parent_store')

# Garder les autres fixtures (sample_scraped_data, sample_chunks, mock_llm) inchangées...
