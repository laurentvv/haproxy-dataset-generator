"""
État du graphe LangGraph pour le système RAG agentic.

Ce module définit la classe State qui étend MessagesState de LangGraph.
"""

from langgraph.graph import MessagesState


class State(MessagesState):
    """État du graphe pour l'agent RAG agentic.

    Cet état étend MessagesState de LangGraph et contient
    toutes les informations nécessaires pour le traitement
    agentic des requêtes.

    Attributes:
        questionIsClear: Indique si la question de l'utilisateur est claire.
        conversation_summary: Résumé de l'historique de conversation.
        sources_used: Liste des sources utilisées pour la réponse.
    """

    questionIsClear: bool = False
    """Indique si la question de l'utilisateur est claire et complète."""

    conversation_summary: str = ''
    """Résumé de l'historique de conversation."""

    sources_used: list[str] = []
    """Liste des sources utilisées pour la réponse."""

    tool_call_count: int = 0
    """Compteur de tool calls pour éviter les boucles infinies."""
