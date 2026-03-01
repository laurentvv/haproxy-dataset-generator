"""Système RAG agentic pour HAProxy 3.2."""

import sys
import uuid
from collections.abc import Iterator
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
            'created_at': None,
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
