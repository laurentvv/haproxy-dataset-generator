"""Layout for HAProxy Chatbot UI."""

import gradio as gr

from app.ui.styles import CUSTOM_CSS
from app.ui.components import (
    build_header,
    build_config_panel,
    build_examples_panel,
    build_chat_area,
)
from app.services.chat_service import ChatService
from app.utils.logging import setup_logging

logger = setup_logging(__name__)


def build_ui(chat_service: ChatService) -> gr.Blocks:
    """Construit l'interface utilisateur complète.

    Args:
        chat_service: Service de chat injecté

    Returns:
        Instance de gr.Blocks
    """
    with gr.Blocks(
        title="HAProxy Docs Chatbot",
        fill_width=True,
        fill_height=True,
    ) as demo:
        # Header
        build_header()

        # Main layout
        with gr.Row(equal_height=False):
            # Sidebar
            with gr.Column(scale=1, min_width=280):
                # Récupérer les modèles disponibles
                available_models = chat_service.llm.list_models()
                (
                    config_panel,
                    model_dropdown,
                    top_k_slider,
                    show_sources,
                ) = build_config_panel(available_models=available_models)
                examples_panel, example_buttons = build_examples_panel()

            # Chat area
            with gr.Column(scale=4):
                (
                    chat_area,
                    msg_input,
                    send_btn,
                    clear_btn,
                    chatbot,
                ) = build_chat_area()

        # Footer
        gr.HTML(
            """
            <div class="app-footer">
                <a href="https://docs.haproxy.org/3.2/" target="_blank">📚 docs.haproxy.org</a> •
                <a href="https://github.com/haproxy/haproxy" target="_blank">💻 GitHub</a>
            </div>
            """
        )

        # Event wiring
        _wire_events(
            demo,
            chat_service,
            msg_input,
            send_btn,
            clear_btn,
            chatbot,
            model_dropdown,
            top_k_slider,
            show_sources,
            example_buttons,
        )

    return demo


def _wire_events(
    demo: gr.Blocks,
    chat_service: ChatService,
    msg_input: gr.Textbox,
    send_btn: gr.Button,
    clear_btn: gr.Button,
    chatbot: gr.Chatbot,
    model_dropdown: gr.Dropdown,
    top_k_slider: gr.Slider,
    show_sources: gr.Checkbox,
    example_buttons: list[gr.Button],
) -> None:
    """Connecte les événements de l'interface.

    Args:
        demo: Instance Gradio
        chat_service: Service de chat
        msg_input: Zone de saisie
        send_btn: Bouton d'envoi
        clear_btn: Bouton d'effacement
        chatbot: Composant chatbot
        model_dropdown: Dropdown de sélection de modèle
        top_k_slider: Slider de profondeur RAG
        show_sources: Checkbox d'affichage des sources
        example_buttons: Liste des boutons d'exemple
    """
    from app.ui.components import get_welcome_message
    from app.state.models import ChatConfig

    # Session ID par défaut (à améliorer avec uuid.uuid4() si nécessaire)
    session_id = "default"

    def handle_submit(
        message: str,
        history: list[gr.ChatMessage],
        model_name: str,
        top_k: int,
        show_sources_flag: bool,
    ) -> list[gr.ChatMessage]:
        """Ajoute le message utilisateur à l'historique.

        Args:
            message: Message utilisateur
            history: Historique de conversation
            model_name: Nom du modèle LLM
            top_k: Profondeur RAG
            show_sources_flag: Afficher les sources

        Returns:
            Historique mis à jour
        """
        logger.info("[DEBUG] handle_submit called with message: %s", message)
        logger.info("[DEBUG] message type: %s", type(message))
        logger.info("[DEBUG] history length: %d", len(history) if history else 0)
        
        # Extraire le texte du message
        if hasattr(message, "content"):
            message_text = message.content
        elif isinstance(message, dict):
            message_text = message.get("content", "")
        elif isinstance(message, str):
            message_text = message
        else:
            message_text = str(message)

        logger.info("[DEBUG] message_text extracted: %s", message_text)

        if not message_text.strip():
            logger.warning("[DEBUG] message_text is empty, returning history unchanged")
            return history

        # Ajouter le message utilisateur à l'historique
        # Dans Gradio 6.x, le content doit être une liste de blocs
        history.append(gr.ChatMessage(role="user", content=[{"type": "text", "text": message_text}]))
        logger.info("[DEBUG] message added to history, new length: %d", len(history))
        return history

    async def handle_respond(
        history: list[gr.ChatMessage],
        model_name: str,
        top_k: int,
        show_sources_flag: bool,
    ) -> list[gr.ChatMessage]:
        """Génère la réponse de l'assistant avec streaming.

        Args:
            history: Historique de conversation
            model_name: Nom du modèle LLM
            top_k: Profondeur RAG
            show_sources_flag: Afficher les sources

        Yields:
            Historique mis à jour à chaque token
        """
        logger.info("[DEBUG] handle_respond called")
        logger.info("[DEBUG] history length: %d", len(history) if history else 0)
        logger.info("[DEBUG] model_name: %s", model_name)
        logger.info("[DEBUG] top_k: %d", top_k)
        logger.info("[DEBUG] show_sources_flag: %s", show_sources_flag)
        
        # Vérifier qu'il y a un message utilisateur valide
        # Dans Gradio 6.x, le rôle peut être None ou "user"
        if not history or not history[-1]:
            logger.warning("[DEBUG] No history or last message, returning history unchanged")
            yield history
            return
        
        # Extraire le message utilisateur
        user_message = history[-1]
        
        # Vérifier le contenu du message
        # Dans Gradio 6.x, le content peut être une liste d'objets ou une chaîne
        if hasattr(user_message, "content"):
            content = user_message.content
        elif isinstance(user_message, dict):
            content = user_message.get("content", "")
        else:
            content = str(user_message)
        
        # Si content est une liste, extraire le texte
        if isinstance(content, list):
            # Gradio 6.x: content est une liste d'objets avec 'text' et 'type'
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", ""))
                else:
                    text_parts.append(str(item))
            content = " ".join(text_parts)
        
        if not content or not content.strip():
            logger.warning("[DEBUG] No valid content in last message, returning history unchanged")
            yield history
            return
        
        logger.info("[DEBUG] Valid user message found: %s", content[:50])
        
        # Le message utilisateur a déjà été extrait dans la variable 'content'
        # Utiliser 'content' directement pour le traitement
        message = content
        
        logger.info("[DEBUG] User message: %s", message)

        # Créer la configuration
        config = ChatConfig(
            model=model_name,
            top_k=top_k,
            show_sources=show_sources_flag,
            temperature=0.1,
        )
        logger.info("[DEBUG] Config created: %s", config)

        # Ajouter un message assistant vide pour le streaming
        # Dans Gradio 6.x, le content doit être une liste de blocs
        history.append(
            gr.ChatMessage(
                role="assistant",
                content=[{"type": "text", "text": '<div style="opacity: 0.7">⏳ **Recherche en cours...**</div>'}],
            )
        )
        logger.info("[DEBUG] Assistant message added for streaming")
        yield history

        # Vider le message et commencer le streaming
        # Dans Gradio 6.x, le content doit être une liste de blocs
        history[-1].content = [{"type": "text", "text": ""}]
        logger.info("[DEBUG] Starting streaming...")

        try:
            logger.info("[DEBUG] Calling chat_service.process_message")
            async for response in chat_service.process_message(
                message=message,
                session_id=session_id,
                config=config,
            ):
                logger.info("[DEBUG] Received response chunk: %s", response[:50] if response else "empty")
                # Dans Gradio 6.x, le content doit être une liste de blocs
                history[-1].content = [{"type": "text", "text": response}]
                yield history
            logger.info("[DEBUG] Streaming completed")
        except Exception as e:
            logger.error("Error in handle_respond: %s", e)
            import traceback
            traceback.print_exc()
            # Dans Gradio 6.x, le content doit être une liste de blocs
            history[-1].content = [{"type": "text", "text": f"❌ **Erreur de génération**\n\n{str(e)}"}]
            yield history

    def handle_clear() -> list[gr.ChatMessage]:
        """Efface l'historique de la session.

        Returns:
            Historique réinitialisé avec le message de bienvenue
        """
        import asyncio

        # Créer une nouvelle boucle d'événements si nécessaire
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Exécuter la fonction async
        loop.run_until_complete(chat_service.clear_session(session_id))

        # Dans Gradio 6.x, le content doit être une liste de blocs
        return [gr.ChatMessage(role="assistant", content=[{"type": "text", "text": get_welcome_message()}])]

    # Submit sur msg_input
    msg_input.submit(
        fn=handle_submit,
        inputs=[msg_input, chatbot, model_dropdown, top_k_slider, show_sources],
        outputs=[chatbot],
    ).then(
        fn=handle_respond,
        inputs=[chatbot, model_dropdown, top_k_slider, show_sources],
        outputs=[chatbot],
    )

    # Click sur send_btn
    send_btn.click(
        fn=handle_submit,
        inputs=[msg_input, chatbot, model_dropdown, top_k_slider, show_sources],
        outputs=[chatbot],
    ).then(
        fn=handle_respond,
        inputs=[chatbot, model_dropdown, top_k_slider, show_sources],
        outputs=[chatbot],
    )

    # Click sur clear_btn
    clear_btn.click(fn=handle_clear, outputs=[chatbot])

    # Click sur les boutons d'exemple
    examples = [
        "Comment configurer un health check HTTP ?",
        "Syntaxe de la directive bind avec SSL ?",
        "Limiter les connexions par IP avec stick-table ?",
        "Utiliser les ACLs pour le routage HTTP ?",
        "Configurer les timeouts client/server ?",
        "Activer les statistiques avec stats enable ?",
    ]

    for btn, example_text in zip(example_buttons, examples):
        btn.click(fn=lambda text=example_text: text, inputs=None, outputs=msg_input)
