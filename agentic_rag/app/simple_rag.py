#!/usr/bin/env python3
"""
Simple RAG - Retrieval direct avec ChromaDB + LLM.

Architecture :
1. Embedding de la question
2. Retrieval ChromaDB avec metadata filtering (SECTION_HINTS)
3. LLM qwen3:latest avec contexte
4. Réponse basée sur le contexte

SANS LangGraph - plus rapide et simple.
"""

import logging
import time

from db.chroma_manager import ChromaManager
from langchain_ollama import ChatOllama, OllamaEmbeddings

logger = logging.getLogger(__name__)

# SECTION_HINTS pour améliorer le retrieval (copié de V3 + étendu)
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
    # Ajout pour health check keywords
    "inter": ["5.2", "5.3"],
    "fall": ["5.2", "5.3"],
    "rise": ["5.2", "5.3"],
    # Ajout pour IP/connection
    "ip": ["11.1", "11.2", "7.3"],
    "connection": ["11.1", "11.2", "7.3"],
    "limit": ["11.1", "11.2", "7.3"],
}

SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2 spécialisé dans la documentation officielle.
Ton objectif est d'aider les utilisateurs à comprendre et configurer HAProxy.

Règles CRITIQUES :
1. Utilise UNIQUEMENT les informations du contexte fourni
2. Cite toujours les sources entre parenthèses (section, page)
3. Structure ta réponse : 1) Réponse directe, 2) Détails techniques, 3) Exemple de config
4. Si l'information n'est pas dans le contexte, dis-le clairement
5. **UTILISE LES TERMES TECHNIQUES EN ANGLAIS** (path, url, if, acl, check, inter, fall, rise, 
   backend, server, balance, bind, ssl, crt, stick-table, track-sc, conn_rate, deny, etc.) 
   même si tu réponds en français. La documentation HAProxy est en anglais.

IMPORTANT : Ne donne JAMAIS de réponses génériques. Concentre-toi UNIQUEMENT sur HAProxy 3.2.
"""


class SimpleRAG:
    """Système RAG simple avec retrieval direct."""

    def __init__(self, model: str = 'qwen3:latest'):
        """
        Initialise le système.
        
        Args:
            model: Modèle LLM à utiliser (défaut: qwen3:latest)
        """
        self.model = model
        self.llm = ChatOllama(model=model, temperature=0.1, num_ctx=4096)
        self.embeddings = OllamaEmbeddings(model='qwen3-embedding:8b')
        self.chroma = ChromaManager()

    def _get_target_sections(self, query: str) -> list[str]:
        """Extrait les sections cibles d'une requête."""
        target_sections = []
        query_lower = query.lower()
        for keyword, sections in SECTION_HINTS.items():
            if keyword in query_lower:
                target_sections.extend(sections)
        return list(set(target_sections))

    def retrieve(self, query: str, k: int = 10) -> tuple[str, list[str], float]:
        """
        Récupère le contexte avec metadata filtering.
        
        Args:
            query: Requête utilisateur
            k: Nombre de chunks à récupérer
            
        Returns:
            Tuple (contexte, sources, temps_retrieval)
        """
        start = time.time()

        # 1. Générer embedding
        query_embedding = self.embeddings.embed_query(query)

        # 2. Recherche ChromaDB (récupérer plus de candidats)
        results = self.chroma.query_with_embedding(query_embedding, n_results=k * 2)

        # 3. Déterminer sections cibles
        target_sections = self._get_target_sections(query)

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
                        section_boost = 0.15
                        break

            # Threshold dynamique avec boost
            if score + section_boost >= 0.20:
                contexts.append(content)
                src = metadata.get('source', 'unknown')
                if src not in sources:
                    sources.append(src)

        # Garder top k
        contexts = contexts[:k]
        context = '\n\n'.join(contexts)
        retrieval_time = time.time() - start

        return context, sources, retrieval_time

    def generate(self, query: str, context: str) -> tuple[str, float]:
        """
        Génère la réponse avec le LLM.
        
        Args:
            query: Requête utilisateur
            context: Contexte retrieved
            
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
        
        Args:
            question: Question utilisateur
            
        Returns:
            Dict avec réponse, sources, et timings
        """
        # 1. Retrieval
        context, sources, retrieval_time = self.retrieve(question, k=10)

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
