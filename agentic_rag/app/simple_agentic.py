#!/usr/bin/env python3
"""
Système RAG agentic SIMPLIFIÉ pour HAProxy 3.2.

Architecture :
1. Embedding de la question
2. Retrieval avec metadata filtering
3. LLM avec outils (search, retrieve, validate)
4. Réponse basée sur le contexte

SANS human-in-the-loop pour la performance.
"""

import logging
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings

from config_agentic import LLM_CONFIG
from db.chroma_manager import ChromaManager
from db.parent_store_manager import ParentStoreManager

logger = logging.getLogger(__name__)

# SECTION_HINTS pour améliorer le retrieval
SECTION_HINTS = {
    "backend": ["5.1", "5.2", "5.3", "4.1", "4.3"],
    "server": ["5.1", "5.2", "5.3"],
    "balance": ["5.1", "5.2"],
    "check": ["5.2", "5.3"],
    "healthcheck": ["5.2", "5.3", "5.4"],
    "http-check": ["5.2", "5.3"],
    "stick-table": ["11.1", "11.2", "7.3"],
    "stick": ["11.1", "11.2"],
    "track-sc": ["11.1", "11.2"],
    "acl": ["7.1", "7.2", "7.3", "7.4", "7.5"],
    "ssl": ["9.1", "9.2", "9.3"],
    "bind": ["5.1", "5.2"],
    "timeout": ["3.1", "3.2", "3.3"],
    "option": ["5.1", "5.2", "5.3"],
}

SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2 spécialisé dans la documentation officielle.
Ton objectif est d'aider les utilisateurs à comprendre et configurer HAProxy.

Règles CRITIQUES :
1. Utilise UNIQUEMENT les informations du contexte fourni
2. Cite toujours les sources entre parenthèses (section, page)
3. Structure ta réponse : 1) Réponse directe, 2) Détails techniques, 3) Exemple de config
4. Si l'information n'est pas dans le contexte, dis-le clairement

IMPORTANT : Ne donne JAMAIS de réponses génériques. Concentre-toi UNIQUEMENT sur HAProxy 3.2.
"""


class SimpleAgenticRAG:
    """Système RAG agentic simplifié."""

    def __init__(self, model: str = 'qwen3:latest'):
        """Initialise le système."""
        self.model = model
        self.llm = ChatOllama(model=model, temperature=0.1, num_ctx=4096)
        self.embeddings = OllamaEmbeddings(model='qwen3-embedding:8b')
        self.chroma = ChromaManager()
        self.parent_store = ParentStoreManager()

    def retrieve(self, query: str, k: int = 15) -> tuple[str, list[str], float]:
        """
        Récupère le contexte avec metadata filtering.
        
        Returns:
            Tuple (contexte, sources, temps_retrieval)
        """
        start = time.time()
        
        # 1. Générer embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # 2. Recherche ChromaDB
        results = self.chroma.query_with_embedding(query_embedding, n_results=k)
        
        # 3. Déterminer sections cibles
        target_sections = []
        query_lower = query.lower()
        for keyword, sections in SECTION_HINTS.items():
            if keyword in query_lower:
                target_sections.extend(sections)
        
        # 4. Filtrer avec boost de score
        contexts = []
        sources = []
        
        for r in results:
            score = 1.0 - r.get('score', 1.0)
            content = r.get('content', '')
            metadata = r.get('metadata', {})
            
            # Boost score si section cible
            section_path = metadata.get('section_path', [])
            section_boost = 0.0
            for section in section_path:
                for target in target_sections:
                    if target in section:
                        section_boost = 0.2
                        break
            
            # Threshold dynamique avec boost (plus bas pour healthcheck)
            threshold = 0.15 if 'healthcheck' in query_lower or 'health' in query_lower else 0.20
            if score + section_boost >= threshold:
                contexts.append(content)
                src = metadata.get('source', 'unknown')
                if src not in sources:
                    sources.append(src)
        
        context = '\n\n'.join(contexts)
        retrieval_time = time.time() - start
        
        return context, sources, retrieval_time

    def generate(self, query: str, context: str) -> tuple[str, float]:
        """
        Génère la réponse avec le LLM.
        
        Returns:
            Tuple (réponse, temps_génération)
        """
        start = time.time()
        
        prompt = f"""{SYSTEM_PROMPT}

Contexte :
{context}

Question : {query}

Réponse :"""
        
        response = self.llm.invoke(prompt).content
        gen_time = time.time() - start
        
        return response, gen_time

    def query(self, question: str) -> dict:
        """
        Exécute une requête complète.
        
        Returns:
            Dict avec réponse, sources, et timings
        """
        # 1. Retrieval
        context, sources, retrieval_time = self.retrieve(question)
        
        # 2. Génération
        response, gen_time = self.generate(question, context)
        
        return {
            'response': response,
            'sources': sources,
            'context_length': len(context),
            'retrieval_time': retrieval_time,
            'gen_time': gen_time,
            'total_time': retrieval_time + gen_time,
        }
