"""
Nœuds du graphe LangGraph pour le système RAG agentic.
"""

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from graph_state import State
from prompts import QUERY_ANALYSIS_PROMPT, SUMMARY_PROMPT
from schemas import QueryAnalysis

logger = logging.getLogger(__name__)

_llm_instance: BaseLanguageModel | None = None


def set_llm(llm: BaseLanguageModel) -> None:
    global _llm_instance
    _llm_instance = llm


def get_llm() -> BaseLanguageModel:
    global _llm_instance
    if _llm_instance is None:
        raise RuntimeError("LLM non initialisé. Appelez set_llm() d'abord.")
    return _llm_instance


def summarize_conversation(state: State) -> dict[str, Any]:
    messages = state.get('messages', [])

    if len(messages) <= 4:
        return {'conversation_summary': ''}

    try:
        llm = get_llm()
        messages_text = '\n'.join(
            [f'{msg.type}: {msg.content[:200]}...' for msg in messages[-10:]]
        )
        summary_prompt = f"""{SUMMARY_PROMPT}

Historique de conversation:
{messages_text}

Résume cet historique en quelques phrases."""
        response = llm.invoke(summary_prompt)
        summary = response.content.strip()
        logger.info(f'Generated conversation summary: {summary[:100]}...')
        return {'conversation_summary': summary}
    except Exception as e:
        logger.error(f'Error in summarize_conversation: {e}')
        return {'conversation_summary': ''}


def analyze_and_rewrite_query(state: State) -> dict[str, Any]:
    """OPTIMISATION : Skip analysis pour questions < 15 mots."""
    messages = state.get('messages', [])
    if not messages:
        return {'questionIsClear': False}

    last_user_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg
            break

    if not last_user_msg:
        return {'questionIsClear': False}

    query = last_user_msg.content

    # Skip analysis pour questions courtes
    if len(query.split()) < 15:
        logger.info(f'Skipping analysis for short query: {query[:50]}...')
        return {'questionIsClear': True, 'rewritten_query': query}

    # Analysis avec lfm2.5-thinking (rapide)
    try:
        analysis_llm = ChatOllama(
            model='lfm2.5-thinking:1.2b-bf16',
            temperature=0.1,
            num_ctx=2048,
        )
        structured_llm = analysis_llm.with_structured_output(QueryAnalysis)
        prompt = f"""{QUERY_ANALYSIS_PROMPT}

Requête de l'utilisateur: {query}

Analyse cette requête et détermine:
1. Si elle est claire et complète
2. Si elle doit être reformulée pour être plus précise
3. Si une clarification est nécessaire"""
        analysis: QueryAnalysis = structured_llm.invoke(prompt)
        logger.info(f'Query analysis: is_clear={analysis.is_clear}')
        return {'questionIsClear': analysis.is_clear, 'rewritten_query': analysis.rewritten_query}
    except Exception as e:
        logger.error(f'Error in analyze_and_rewrite_query: {e}')
        return {'questionIsClear': True, 'rewritten_query': query}


def agent_node(state: State) -> dict[str, Any]:
    """Nœud principal utilisant les outils.

    OPTIMISATION: 
    - 1 tool call max pour questions simples (search uniquement)
    - 2 tool calls max pour questions complexes (search + retrieve si besoin)
    """
    try:
        from tools import (
            retrieve_parent_chunks,
            search_child_chunks,
            validate_haproxy_config,
        )
        from prompts import SYSTEM_PROMPT
        from langchain_core.messages import SystemMessage

        llm = get_llm()

        # Vérifier le nombre de tool calls déjà effectués
        tool_call_count = state.get('tool_call_count', 0)

        # Après 2 tool calls, on répond SANS tools (pour rester sous 30s)
        if tool_call_count >= 2:
            messages = state.get('messages', [])
            enhanced_messages = messages.copy()
            has_system = any(hasattr(msg, 'type') and msg.type == 'system' for msg in enhanced_messages)
            if not has_system:
                enhanced_messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

            # Force la réponse finale SANS tools
            response = llm.invoke(enhanced_messages)
            logger.info(f'Agent node generated FINAL response (tool limit={tool_call_count})')
            return {'messages': [response]}

        # Sinon, on utilise les tools
        llm_with_tools = llm.bind_tools(
            [search_child_chunks, retrieve_parent_chunks, validate_haproxy_config]
        )

        # Récupérer les messages
        messages = state.get('messages', [])

        # Injecter SYSTEM_PROMPT si pas présent
        enhanced_messages = messages.copy()
        has_system = any(hasattr(msg, 'type') and msg.type == 'system' for msg in enhanced_messages)
        if not has_system:
            enhanced_messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

        response = llm_with_tools.invoke(enhanced_messages)
        logger.info(f'Agent node generated response: {response.type}')

        # Incrémenter le compteur de tool calls
        result = {'messages': [response]}
        if hasattr(response, 'tool_calls') and response.tool_calls:
            num_tool_calls = len(response.tool_calls)
            result['tool_call_count'] = tool_call_count + num_tool_calls
            logger.info(f'Tool call count: {tool_call_count} + {num_tool_calls} = {result["tool_call_count"]}')

        return result
    except Exception as e:
        logger.error(f'Error in agent_node: {e}')
        error_msg = AIMessage(content=f"Désolé, une erreur s'est produite: {str(e)}")
        return {'messages': [error_msg]}
