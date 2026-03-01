"""Fixtures pytest pour les tests du système RAG agentic."""

import shutil
import tempfile
from pathlib import Path

import pytest
from langchain_ollama import ChatOllama, OllamaEmbeddings

from agentic_rag.config_agentic import EMBEDDING_MODEL, LLM_CONFIG
from agentic_rag.db.chroma_manager import ChromaManager
from agentic_rag.db.parent_store_manager import ParentStoreManager


@pytest.fixture
def temp_dir():
    """Crée un répertoire temporaire pour les tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_scraped_data():
    """Données scrapées de test."""
    return [
        {
            'url': 'https://docs.haproxy.org/3.2/configuration.html',
            'title': 'Configuration Manual',
            'content': (
                'This is the HAProxy 3.2 configuration manual. '
                'It contains detailed information about configuring HAProxy.'
            ),
            'parent_url': '',
            'parent_title': '',
            'depth': 1,
            'section_path': ['Configuration Manual'],
            'anchor': '',
            'source_file': 'configuration',
        },
        {
            'url': 'https://docs.haproxy.org/3.2/configuration.html#4',
            'title': '4. Global Parameters',
            'content': (
                'Global parameters are settings that apply to the entire '
                "HAProxy process. They are defined in the 'global' section "
                'of the configuration file.'
            ),
            'parent_url': 'https://docs.haproxy.org/3.2/configuration.html',
            'parent_title': 'Configuration Manual',
            'depth': 2,
            'section_path': ['Configuration Manual', 'Global Parameters'],
            'anchor': '4',
            'source_file': 'configuration',
        },
    ]


@pytest.fixture
def sample_chunks():
    """Chunks de test."""
    return [
        {
            'content': 'This is the HAProxy 3.2 configuration manual.',
            'metadata': {
                'parent_id': 'parent_config',
                'source': 'https://docs.haproxy.org/3.2/configuration.html',
                'section_path': ['Configuration Manual'],
                'depth': 1,
            },
        },
        {
            'content': 'Global parameters are settings that apply to the entire HAProxy process.',
            'metadata': {
                'parent_id': 'parent_global',
                'source': 'https://docs.haproxy.org/3.2/configuration.html#4',
                'section_path': ['Configuration Manual', 'Global Parameters'],
                'depth': 2,
            },
        },
    ]


@pytest.fixture
def mock_llm():
    """Mock du LLM pour les tests."""
    return ChatOllama(model=LLM_CONFIG['model'], temperature=0.7)


@pytest.fixture
def mock_embeddings():
    """Mock des embeddings pour les tests."""
    return OllamaEmbeddings(model=EMBEDDING_MODEL)


@pytest.fixture
def chroma_manager(temp_dir, mock_embeddings):
    """Fixture pour ChromaManager."""
    manager = ChromaManager(
        persist_directory=temp_dir / 'chroma',
        collection_name='test_collection',
    )
    manager.create_collection()
    yield manager
    manager.delete_collection()


@pytest.fixture
def parent_store_manager(temp_dir):
    """Fixture pour ParentStoreManager."""
    return ParentStoreManager(store_dir=temp_dir / 'parent_store')
