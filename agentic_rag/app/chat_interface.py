"""Interface de chat Gradio pour le système RAG agentic."""

import gradio as gr

from .rag_system import AgenticRAGSystem


class ChatInterface:
    """Interface de chat Gradio."""

    def __init__(self) -> None:
        """Initialise l'interface de chat."""
        self.rag_system = AgenticRAGSystem()
        self.current_session_id = self.rag_system.create_session()

    def respond(
        self,
        message: str,
        history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """Répond à un message de l'utilisateur.

        Args:
            message: Message de l'utilisateur
            history: Historique de conversation (liste de dict avec 'role' et 'content')

        Returns:
            Tuple (message vide, historique mis à jour)
        """
        if not message.strip():
            return '', history

        # Construire la réponse avec streaming
        response = ''
        for chunk in self.rag_system.query(self.current_session_id, message):
            response += chunk

        # Mettre à jour l'historique avec le format dict
        history.append({'role': 'user', 'content': message})
        history.append({'role': 'assistant', 'content': response})

        return '', history

    def clear_chat(self) -> tuple[str, list[dict[str, str]]]:
        """Efface la conversation.

        Returns:
            Tuple (message vide, historique vide)
        """
        self.current_session_id = self.rag_system.create_session()
        return '', []

    def create_ui(self) -> gr.Blocks:
        """Crée l'interface utilisateur Gradio.

        Returns:
            Interface Gradio
        """
        with gr.Blocks(
            title='HAProxy 3.2 Agentic RAG',
            theme=gr.themes.Soft(),
            css="""
                .chat-container { max-height: 600px; overflow-y: auto; }
                .message { padding: 10px; margin: 5px 0; border-radius: 8px; }
                .user-message { background-color: #e3f2fd; }
                .assistant-message { background-color: #f5f5f5; }
            """,
        ) as demo:
            gr.Markdown(
                """
                # 🤖 HAProxy 3.2 Agentic RAG

                Assistant intelligent basé sur la documentation officielle HAProxy 3.2.

                **Fonctionnalités:**
                - Recherche agentic avec LangGraph
                - Validation de configuration HAProxy
                - Citation des sources
                - Conversation contextuelle
                """
            )

            chatbot = gr.Chatbot(
                label='Conversation',
                height=500,
            )

            with gr.Row():
                msg = gr.Textbox(
                    label='Votre question',
                    placeholder='Posez une question sur HAProxy 3.2...',
                    scale=4,
                    submit_btn=True,
                )
                submit_btn = gr.Button('Envoyer', variant='primary', scale=1)

            with gr.Row():
                clear_btn = gr.Button('Nouvelle conversation', variant='secondary')

            # Event listeners
            msg.submit(
                fn=self.respond,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot],
            )

            submit_btn.click(
                fn=self.respond,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot],
            )

            clear_btn.click(
                fn=self.clear_chat,
                outputs=[msg, chatbot],
            )

            gr.Markdown(
                """
                ---
                **Note:** Ce système utilise un agent RAG agentic avec LangGraph pour fournir
                des réponses contextuelles basées sur la documentation HAProxy 3.2.
                """
            )

        return demo
