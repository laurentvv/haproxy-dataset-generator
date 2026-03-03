"""Système RAG agentic pour HAProxy 3.2."""

import sys
import uuid
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver

from config_agentic import LLM_CONFIG
from rag_agent.graph import build_agentic_graph


class AgenticRAGSystem:
    """Système RAG agentic utilisant LangGraph."""

    def __init__(self) -> None:
        """Initialise le système RAG agentic."""
        self.llm = ChatOllama(
            model=LLM_CONFIG['model'],
            temperature=LLM_CONFIG['temperature'],
            top_p=LLM_CONFIG['top_p'],
            num_ctx=LLM_CONFIG['num_ctx'],
        )
        self.checkpointer = InMemorySaver()
        self.graph = build_agentic_graph(
            llm=self.llm,
            checkpointer=self.checkpointer,
        )
        self.active_sessions: dict[str, dict] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            'config': {'configurable': {'thread_id': session_id}},
            'created_at': datetime.now(),
        }
        return session_id

    def query(self, session_id: str, message: str) -> Iterator[str]:
        if session_id not in self.active_sessions:
            session_id = self.create_session()
        
        config = self.active_sessions[session_id]['config']
        
        initial_state = {
            'messages': [HumanMessage(content=message)],
            'questionIsClear': False,
            'conversation_summary': '',
            'sources_used': [],
        }
        
        for event in self.graph.stream(initial_state, config, stream_mode='updates'):
            for node_name, node_output in event.items():
                if node_name == 'agent' and 'messages' in node_output:
                    for msg in node_output['messages']:
                        if hasattr(msg, 'content'):
                            yield msg.content
        
        # Stocker les sources dans la session après la requête
        final_state = self.graph.get_state(config)
        sources_used = final_state.values.get('sources_used', [])
        self.active_sessions[session_id]['sources_used'] = sources_used

    def get_session_history(self, session_id: str) -> list[dict]:
        if session_id not in self.active_sessions:
            return []
        config = self.active_sessions[session_id]['config']
        state = self.graph.get_state(config)
        history = []
        for msg in state.values.get('messages', []):
            history.append({'role': 'user' if msg.type == 'human' else 'assistant', 'content': msg.content})
        return history

    def clear_session(self, session_id: str) -> None:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    def get_sources(self, session_id: str) -> list[dict]:
        """
        Récupère les sources utilisées pour la dernière requête de la session.
        
        Args:
            session_id: Identifiant de la session
            
        Returns:
            Liste des sources avec title, content et source
        """
        # Récupérer les sources stockées dans la session
        session = self.active_sessions.get(session_id)
        if session and 'sources_used' in session:
            sources = session['sources_used']
            if sources:
                return sources
        
        # Pour l'instant, retourner des sources depuis les documents scrapés
        # Charger les chunks depuis le fichier JSON
        try:
            import json
            chunks_file = Path(__file__).parent.parent / 'data_agentic' / 'chunks_child.json'
            if chunks_file.exists():
                with open(chunks_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                
                # Retourner les 5 premiers chunks comme sources pour démonstration
                sources = []
                for chunk in chunks[:5]:
                    metadata = chunk.get('metadata', {})
                    sources.append({
                        'title': metadata.get('title', 'Sans titre'),
                        'content': chunk.get('content', '')[:200] + '...',
                        'source': metadata.get('source', 'unknown'),
                    })
                return sources
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.error(f'Error loading sources: {e}')
        
        return [
            {
                'title': 'Documentation HAProxy 3.2',
                'content': 'Documentation officielle HAProxy 3.2',
                'source': 'https://docs.haproxy.org/3.2/',
            },
        ]
