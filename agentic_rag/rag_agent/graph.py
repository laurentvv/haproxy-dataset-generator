"""
Construction du graphe LangGraph pour le système RAG agentic.

Ce module définit la structure du graphe d'agent et ses connexions.
Le graphe implémente un flux RAG agentic avec :
- Résumé de conversation automatique
- Analyse et réécriture de requête
- Human-in-the-loop via interrupt_before
- Outils de retrieval (child chunks, parent chunks, validation HAProxy)
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
# Quand appelé depuis app/, on doit pouvoir importer
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from edges import should_summarize, should_use_tools
from graph_state import State
from nodes import (
    agent_node,
    analyze_and_rewrite_query,
    summarize_conversation,
)
from tools import (
    retrieve_parent_chunks,
    search_child_chunks,
    validate_haproxy_config,
)

logger = logging.getLogger(__name__)


def build_agentic_graph(llm, checkpointer=None):
    """
    Construit le graphe de l'agent RAG agentic.

    Cette fonction construit le graphe LangGraph avec tous les nœuds
    et les arêtes conditionnelles pour l'agent RAG agentic.

    Architecture du graphe :
        START → summarize_conversation → analyze_and_rewrite_query → [INTERRUPT]
        [INTERRUPT] → agent → tools → agent (loop) → END

    Human-in-the-loop :
        Le graphe s'interrompt AVANT le nœud 'agent' pour permettre
        à l'utilisateur de valider ou modifier la requête.

    Args:
        llm: Instance du LLM à utiliser.
        checkpointer: Checkpointer pour la persistance (optionnel).

    Returns:
        Graphe LangGraph compilé.
    """
    # Initialiser le LLM global pour les nœuds
    import nodes

    nodes.set_llm(llm)

    builder = StateGraph(State)

    # ─────────────────────────────────────────────────────────────
    # Ajout des nœuds
    # ─────────────────────────────────────────────────────────────
    builder.add_node('summarize_conversation', summarize_conversation)
    builder.add_node('analyze_and_rewrite_query', analyze_and_rewrite_query)
    builder.add_node('agent', agent_node)

    # Nœud d'outils avec les trois outils de retrieval
    tools_node = ToolNode([search_child_chunks, retrieve_parent_chunks, validate_haproxy_config])
    builder.add_node('tools', tools_node)

    # ─────────────────────────────────────────────────────────────
    # Ajout des edges
    # ─────────────────────────────────────────────────────────────
    
    # START -> summarize_conversation
    builder.add_edge(START, 'summarize_conversation')

    # summarize_conversation -> analyze_and_rewrite_query (conditionnel)
    builder.add_conditional_edges(
        'summarize_conversation',
        should_summarize,
        {
            'summarize': 'analyze_and_rewrite_query',
            'continue': 'analyze_and_rewrite_query',
        },
    )

    # analyze_and_rewrite_query -> agent
    builder.add_edge('analyze_and_rewrite_query', 'agent')

    # agent -> tools ou end (conditionnel via should_use_tools)
    # CRITIQUE: tool_call_count >= 4 → 'end', tool_calls detected → 'tools', AI response → 'end'
    builder.add_conditional_edges(
        'agent',
        should_use_tools,
        {
            'tools': 'tools',  # ← Exécuter les tool calls
            'agent': 'agent',  # ← Cas rare (continuer sans tools)
            'end': END,  # ← Tool limit atteint ou réponse finale
        },
    )

    # tools -> agent (loop de retrieval)
    builder.add_edge('tools', 'agent')

    # ─────────────────────────────────────────────────────────────
    # Compilation du graphe
    # ─────────────────────────────────────────────────────────────
    logger.info('Compiling agentic RAG graph')
    
    # Mode automatique : pas d'interruption humaine
    # Pour activer human-in-the-loop, utiliser : interrupt_before=['agent']
    graph = builder.compile(checkpointer=checkpointer)

    return graph


def main() -> None:
    """
    Point d'entrée principal pour tester le graphe.

    Cette fonction permet de tester la construction du graphe
    et d'afficher sa structure.
    """
    from config_agentic import LLM_CONFIG
    from langchain_ollama import ChatOllama

    # Créer le LLM
    llm = ChatOllama(
        model=LLM_CONFIG['model'],
        temperature=LLM_CONFIG['temperature'],
    )

    # Construire le graphe
    graph = build_agentic_graph(llm)

    print('=' * 60)
    print('Graphe LangGraph créé avec succès')
    print('=' * 60)
    print(f'Graphe: {graph}')
    print(f'Checkpointer: Oui (InMemorySaver)')
    print(f'Mode: Automatique (pas d\'interruption humaine)')
    print('\nNoeuds du graphe:')
    for node in graph.nodes:
        print(f'  - {node}')
    print('\nFlux: START -> summarize -> analyze -> agent -> tools -> agent (loop) -> END')


if __name__ == '__main__':
    main()
