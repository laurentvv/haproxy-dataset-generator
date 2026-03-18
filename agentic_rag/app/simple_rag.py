#!/usr/bin/env python3
"""
Simple RAG - Retrieval direct avec ChromaDB + LLM.
Mis à jour pour Gemini Embeddings.
"""

import logging
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agentic_rag.db.chroma_manager import ChromaManager
from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from agentic_rag.config_agentic import EMBEDDING_MODEL, GOOGLE_API_KEY, LLM_CONFIG

logger = logging.getLogger(__name__)

# SECTION_HINTS pour améliorer le retrieval
SECTION_HINTS = {
    "backend": ["5.1", "5.2", "5.3", "4.1", "4.3"],
    "server": ["5.1", "5.2", "5.3"],
    "balance": ["5.1", "5.2", "5.3"],
    "check": ["5.2", "5.3", "5.4"],
    "healthcheck": ["5.2", "5.3", "5.4"],
    "http-check": ["5.2", "5.3", "5.4"],
    "stick-table": ["11.1", "11.2", "7.3", "7.4", "7.5"],
    "stick": ["11.1", "11.2", "7.3"],
    "track-sc": ["11.1", "11.2", "7.3"],
    "conn_rate": ["11.1", "11.2", "7.3"],
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
    "limit": ["11.1", "11.2", "7.3"],
}

SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2 spécialisé dans la documentation officielle.
Ton objectif est d'aider les utilisateurs à comprendre et configurer HAProxy.
...
"""

class SimpleRAG:
    """Système RAG simple avec retrieval direct (Gemini)."""

    def __init__(self, model: str = None):
        """Initialise le système."""
        self.model = model or LLM_CONFIG['model']
        self.llm = ChatOllama(model=self.model, temperature=0.1, num_ctx=4096)
        
        if not GOOGLE_API_KEY:
             raise ValueError("GOOGLE_API_KEY non configurée")

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )
        self.chroma = ChromaManager()

    def _get_target_sections(self, query: str) -> list[str]:
        target_sections = []
        query_lower = query.lower()
        for keyword, sections in SECTION_HINTS.items():
            if keyword in query_lower:
                target_sections.extend(sections)
        return list(set(target_sections))

    def retrieve(self, query: str, k: int = 10) -> tuple[str, list[str], float]:
        start = time.time()
        query_embedding = self.embeddings.embed_query(query)
        results = self.chroma.query_with_embedding(query_embedding, n_results=k * 2)
        target_sections = self._get_target_sections(query)

        contexts = []
        sources = []
        for r in results:
            score = 1.0 - r.get('score', 1.0)
            content = r.get('content', '')
            metadata = r.get('metadata', {})
            section_path = metadata.get('section_path', [])

            section_boost = 0.0
            for section in section_path:
                for target in target_sections:
                    if target in section:
                        section_boost = 0.15
                        break

            if score + section_boost >= 0.20:
                contexts.append(content)
                src = metadata.get('source', 'unknown')
                if src not in sources:
                    sources.append(src)

        contexts = contexts[:k]
        context = '\n\n'.join(contexts)
        retrieval_time = time.time() - start
        return context, sources, retrieval_time

    def generate(self, query: str, context: str) -> tuple[str, float]:
        start = time.time()
        prompt = f"""{SYSTEM_PROMPT}\n\nContexte :\n{context}\n\nQuestion : {query}\n\nRéponse :"""
        response = self.llm.invoke(prompt).content
        gen_time = time.time() - start
        return response, gen_time

    def query(self, question: str) -> dict:
        context, sources, retrieval_time = self.retrieve(question, k=10)
        response, gen_time = self.generate(question, context)
        return {
            'response': response,
            'sources': sources,
            'context_length': len(context),
            'retrieval_time': retrieval_time,
            'gen_time': gen_time,
            'total_time': retrieval_time + gen_time,
        }
