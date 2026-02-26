"""State manager for HAProxy Chatbot sessions."""

import asyncio
from datetime import datetime

from app.state.models import ChatSession, ChatConfig, ChatMessage
from app.utils.logging import setup_logging

logger = setup_logging(__name__)


class StateManager:
    """Gestionnaire d'état thread-safe avec support multi-session.

    Responsabilités:
    - Gestion des sessions utilisateur
    - Thread-safety avec asyncio.Lock
    - Cleanup automatique des sessions expirées
    - Statistiques sur les sessions
    """

    def __init__(self, session_timeout_hours: int = 24):
        """Initialise le State Manager.

        Args:
            session_timeout_hours: Timeout des sessions en heures
        """
        self._sessions: dict[str, ChatSession] = {}
        self._lock = asyncio.Lock()
        self._session_timeout = session_timeout_hours * 3600

    async def get_or_create_session(self, session_id: str) -> ChatSession:
        """Récupère ou crée une session.

        Args:
            session_id: Identifiant de la session

        Returns:
            Instance de ChatSession
        """
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ChatSession(session_id=session_id)
                logger.info("Created new session: %s", session_id)

            # Update last activity
            self._sessions[session_id].last_activity = datetime.now()
            return self._sessions[session_id]

    async def update_config(self, session_id: str, config: ChatConfig) -> None:
        """Met à jour la configuration d'une session.

        Args:
            session_id: Identifiant de la session
            config: Nouvelle configuration
        """
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].config = config
                logger.debug("Updated config for session: %s", session_id)
            else:
                logger.warning("Session %s not found, cannot update config", session_id)

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Ajoute un message à une session.

        Args:
            session_id: Identifiant de la session
            message: Message à ajouter
        """
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].add_message(message)
                logger.debug(
                    "Added message to session %s: %s...",
                    session_id,
                    message.content[:50],
                )
            else:
                logger.warning("Session %s not found, cannot add message", session_id)

    async def clear_session(self, session_id: str) -> None:
        """Efface l'historique d'une session.

        Args:
            session_id: Identifiant de la session
        """
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].history.clear()
                self._sessions[session_id].last_activity = datetime.now()
                logger.info("Cleared history for session: %s", session_id)
            else:
                logger.warning("Session %s not found, cannot clear", session_id)

    async def cleanup_expired_sessions(self) -> int:
        """Nettoie les sessions expirées et retourne le nombre supprimé.

        Returns:
            Nombre de sessions supprimées
        """
        now = datetime.now()
        expired_ids = []

        async with self._lock:
            for session_id, session in self._sessions.items():
                age = (now - session.last_activity).total_seconds()
                if age > self._session_timeout:
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                del self._sessions[session_id]

        if expired_ids:
            logger.info("Cleaned up %d expired sessions", len(expired_ids))

        return len(expired_ids)

    async def get_stats(self) -> dict:
        """Retourne des statistiques sur les sessions.

        Returns:
            Dictionnaire avec les statistiques
        """
        async with self._lock:
            total_sessions = len(self._sessions)
            total_messages = sum(len(s.history) for s in self._sessions.values())

            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": (
                    total_messages / total_sessions if total_sessions > 0 else 0
                ),
            }
