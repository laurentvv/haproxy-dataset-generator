"""Chat service for HAProxy Chatbot."""

from typing import AsyncGenerator

from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.state.manager import StateManager
from app.state.models import ChatMessage, ChatConfig
from app.utils.validators import InputValidator
from app.utils.errors import ValidationError
from app.utils.logging import setup_logging

logger = setup_logging(__name__)


class ChatService:
    """Service principal gérant la logique du chat.

    Responsabilités:
    - Validation des entrées
    - Coordination RAG + LLM
    - Gestion de l'état de session
    - Streaming des réponses
    """

    def __init__(
        self,
        rag_service: RAGService,
        llm_service: LLMService,
        state_manager: StateManager,
    ):
        """Initialise le service de chat.

        Args:
            rag_service: Service RAG
            llm_service: Service LLM
            state_manager: Gestionnaire d'état
        """
        self.rag = rag_service
        self.llm = llm_service
        self.state = state_manager
        self.validator = InputValidator()

    async def process_message(
        self,
        message: str,
        session_id: str,
        config: ChatConfig,
    ) -> AsyncGenerator[str, None]:
        """Traite un message utilisateur avec streaming.

        Args:
            message: Message utilisateur
            session_id: Identifiant de session
            config: Configuration de la session

        Yields:
            Tokens de la réponse au fur et à mesure

        Raises:
            ValidationError: Si l'entrée est invalide
            ChatError: Si une erreur survient lors du traitement
        """
        logger.info("[DEBUG] process_message called")
        logger.info("[DEBUG] message: %s", message)
        logger.info("[DEBUG] session_id: %s", session_id)
        logger.info("[DEBUG] config: %s", config)
        
        # 1. Valider l'entrée
        try:
            logger.info("[DEBUG] Validating message...")
            validated_message = self.validator.validate(message)
            logger.info("[DEBUG] Message validated: %s", validated_message)
        except ValidationError as e:
            logger.warning("Validation failed: %s", e)
            yield f"⚠️ **Question invalide**\n\n{str(e)}"
            return

        # 2. Récupérer ou créer la session
        session = await self.state.get_or_create_session(session_id)

        # 3. Ajouter le message utilisateur à l'historique
        user_message = ChatMessage(role="user", content=validated_message)
        await self.state.add_message(session_id, user_message)

        # 4. RAG retrieval
        try:
            logger.info("RAG retrieval for: '%s...'", validated_message[:50])
            context_str, sources, low_confidence = await self.rag.retrieve(
                query=validated_message, top_k=config.top_k
            )

            if low_confidence or not context_str:
                yield self.llm.get_fallback_response()
                return

        except Exception as e:
            logger.error("RAG retrieval error: %s", e)
            yield f"❌ **Erreur de recherche**\n\n{str(e)}"
            return

        # 5. Récupérer l'historique pour le LLM
        llm_history = session.get_history_for_llm(max_turns=3)

        # 6. Génération LLM avec streaming
        response = ""
        try:
            async for token in self.llm.generate(
                question=validated_message,
                context=context_str,
                model=config.model,
                history=llm_history,
                temperature=config.temperature,
            ):
                response += token
                yield response

        except Exception as e:
            logger.error("LLM generation error: %s", e)
            yield f"❌ **Erreur de génération**\n\n{str(e)}"
            return

        # 7. Ajouter les sources si configuré
        if config.show_sources and sources:
            sources_md = self._format_sources(sources)
            response += sources_md
            yield response

        # 8. Sauvegarder la réponse dans l'historique
        assistant_message = ChatMessage(
            role="assistant", content=response, sources=sources
        )
        await self.state.add_message(session_id, assistant_message)

    def _format_sources(self, sources: list[dict]) -> str:
        """Formate les sources en Markdown.

        Args:
            sources: Liste des sources

        Returns:
            Sources formatées en Markdown
        """
        if not sources:
            return ""

        lines = ["\n\n---\n\n**📚 Sources :**\n"]
        for i, src in enumerate(sources):
            icon = "📝" if src.get("has_code") else "📄"
            title = src.get("title", "Unknown")
            url = src.get("url", "#")
            lines.append(f"{icon} [{i + 1}] [{title}]({url})")

        return "\n".join(lines)

    async def clear_session(self, session_id: str) -> None:
        """Efface l'historique d'une session.

        Args:
            session_id: Identifiant de la session
        """
        await self.state.clear_session(session_id)
        logger.info("Session %s cleared", session_id)
