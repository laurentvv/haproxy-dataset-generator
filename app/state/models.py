"""Data models for HAProxy Chatbot state management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class ChatMessage:
    """Message de chat avec métadonnées.

    Attributes:
        role: Rôle du message ('user' ou 'assistant')
        content: Contenu du message
        timestamp: Horodatage du message
        sources: Liste des sources associées au message
        metadata: Métadonnées additionnelles
    """

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatConfig:
    """Configuration de session de chat.

    Attributes:
        model: Modèle LLM à utiliser
        top_k: Nombre de résultats RAG à récupérer
        show_sources: Afficher ou non les sources
        temperature: Température de génération
    """

    model: str = "gemma3:latest"
    top_k: int = 5
    show_sources: bool = True
    temperature: float = 0.1


@dataclass
class ChatSession:
    """Session de chat utilisateur.

    Attributes:
        session_id: Identifiant unique de la session
        created_at: Date de création de la session
        last_activity: Date de dernière activité
        history: Historique des messages
        config: Configuration de la session
    """

    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    history: list[ChatMessage] = field(default_factory=list)
    config: ChatConfig = field(default_factory=ChatConfig)

    def add_message(self, message: ChatMessage) -> None:
        """Ajoute un message à l'historique.

        Args:
            message: Message à ajouter
        """
        self.history.append(message)
        self.last_activity = datetime.now()
        self._cleanup_old_messages()

    def get_history_for_llm(self, max_turns: int = 3) -> list[tuple[str, str]]:
        """Retourne l'historique formaté pour le LLM.

        Args:
            max_turns: Nombre maximum de tours de conversation

        Returns:
            Liste de tuples (user_message, assistant_message)
        """
        llm_history = []
        user_msg = None

        for msg in self.history[-max_turns * 2 :]:
            if msg.role == "user":
                user_msg = msg.content
            elif msg.role == "assistant" and user_msg:
                llm_history.append((user_msg, msg.content))
                user_msg = None

        return llm_history

    def _cleanup_old_messages(self, max_messages: int = 50) -> None:
        """Nettoie les anciens messages pour limiter la mémoire.

        Args:
            max_messages: Nombre maximum de messages à conserver
        """
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
