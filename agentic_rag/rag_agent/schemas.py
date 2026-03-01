"""
Schémas Pydantic v2 pour le système RAG agentic.

Ce module définit les schémas pour les sorties structurées.
"""

from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    """Analyse et réécriture de requête.

    Ce schéma définit le résultat de l'analyse d'une requête utilisateur,
    incluant la détermination de sa clarté et sa réécriture si nécessaire.

    Attributes:
        is_clear: Indique si la requête est claire et complète.
        rewritten_query: Requête réécrite si nécessaire.
        clarification_needed: Indique si une clarification est nécessaire.
        clarification_question: Question de clarification si nécessaire.
    """

    is_clear: bool = Field(description='La requête est-elle claire et complète ?')
    rewritten_query: str = Field(description='Requête réécrite si nécessaire')
    clarification_needed: bool = Field(description='Une clarification est-elle nécessaire ?')
    clarification_question: str | None = Field(
        default=None, description='Question de clarification'
    )


class RetrievalResult(BaseModel):
    """Résultat de retrieval.

    Ce schéma définit le résultat d'une opération de retrieval
    dans la base de données vectorielle.

    Attributes:
        chunks: Liste des chunks récupérés.
        parent_ids: Liste des IDs des parents des chunks.
        sources: Liste des sources des chunks.
    """

    chunks: list[dict] = Field(description='Chunks récupérés')
    parent_ids: list[str] = Field(description='IDs des parents')
    sources: list[str] = Field(description='Sources des chunks')
