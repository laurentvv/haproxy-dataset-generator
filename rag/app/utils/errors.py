"""Custom exceptions for HAProxy Chatbot."""


class ChatError(Exception):
    """Erreur de base pour le chat."""


class ValidationError(ChatError):
    """Erreur de validation d'entrée."""


class RetrievalError(ChatError):
    """Erreur lors du retrieval RAG."""


class GenerationError(ChatError):
    """Erreur lors de la génération LLM."""


class StateError(ChatError):
    """Erreur liée à l'état de l'application."""
