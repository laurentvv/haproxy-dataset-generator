"""Main application for HAProxy Chatbot."""

import gradio as gr

from app.ui.layout import build_ui
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.state.manager import StateManager
from app.utils.logging import setup_logging

logger = setup_logging(__name__)


def create_app() -> gr.Blocks:
    """Crée l'application Gradio avec tous les services injectés.

    Returns:
        Instance de gr.Blocks prête à être lancée
    """
    # Initialiser les services
    state_manager = StateManager()
    rag_service = RAGService()
    llm_service = LLMService()
    chat_service = ChatService(
        rag_service=rag_service,
        llm_service=llm_service,
        state_manager=state_manager,
    )

    # Construire l'UI
    demo = build_ui(chat_service)

    logger.info("Application Gradio créée avec succès")
    return demo
