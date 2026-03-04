"""
Arêtes conditionnelles du graphe LangGraph pour le système RAG agentic.
"""

import logging
import sys
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent))

from graph_state import State

logger = logging.getLogger(__name__)


def should_use_tools(state: State) -> str:
    """Détermine si l'agent doit utiliser les outils.

    OPTIMISATION: Max 2 tool calls pour rester sous 45s/question.
    ORDRE DES CHECKS:
    1. dernier message a des tool_calls → 'tools' (pour exécuter) PRIORITAIRE
    2. dernier message est AI avec contenu → 'end' (réponse finale) PRIORITAIRE
    3. tool_call_count >= 2 → 'agent' (forcer réponse finale SANS tools)
    4. Sinon → 'tools' (premier appel)
    """
    messages = state.get('messages', [])
    tool_call_count = state.get('tool_call_count', 0)

    # Debug
    print(f"DEBUG should_use_tools: {len(messages)} messages, tool_call_count={tool_call_count}", flush=True)

    if messages:
        last_msg = messages[-1]
        print(f"  last_msg.type={last_msg.type}, has_tool_calls={hasattr(last_msg, 'tool_calls')}", flush=True)
        print(f"  tool_calls={getattr(last_msg, 'tool_calls', None)}", flush=True)
        print(f"  has_content={bool(getattr(last_msg, 'content', ''))}", flush=True)

        # 1. Si tool_calls → tools pour exécuter (PRIORITAIRE)
        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            print(f"  → RETURN 'tools' (execute tool calls)", flush=True)
            return 'tools'

        # 2. Si réponse AI avec contenu → END (réponse finale) PRIORITAIRE
        if hasattr(last_msg, 'type') and last_msg.type == 'ai':
            if hasattr(last_msg, 'content') and last_msg.content:
                print("  → RETURN 'end' (AI response with content)", flush=True)
                return 'end'
            else:
                print("  → CONTINUE (AI but no content)", flush=True)

        # 3. Si tool_call_count >= 2, on force l'agent à répondre SANS tools
        if tool_call_count >= 2:
            print("  → RETURN 'agent' (force final response WITHOUT tools)", flush=True)
            return 'agent'

    # 4. Premier appel → tools
    print("  → RETURN 'tools' (first call)", flush=True)
    return 'tools'


def should_summarize(state: State) -> Literal['summarize', 'continue']:
    """Détermine si l'historique doit être résumé (> 4 messages)."""
    messages = state.get('messages', [])
    
    if len(messages) > 4:
        return 'summarize'
    
    return 'continue'
