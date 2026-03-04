"""Application Gradio pour le système RAG agentic HAProxy 3.2."""

import gradio as gr

from .chat_interface import ChatInterface
from ..config_agentic import GRADIO_CONFIG


def main() -> None:
    """Point d'entrée principal."""
    print('=== HAProxy 3.2 Agentic RAG Chatbot ===')
    print(f'Port: {GRADIO_CONFIG["port"]}')
    print("Démarrage de l'interface Gradio...\n")

    # Créer l'interface
    chat_interface = ChatInterface()
    demo = chat_interface.create_ui()

    # Lancer l'application
    demo.launch(
        server_name='0.0.0.0',
        server_port=GRADIO_CONFIG['port'],
        share=GRADIO_CONFIG['share'],
        show_error=True,
        quiet=False,
        theme=gr.themes.Soft(),
        css="""
            .chat-container { max-height: 600px; overflow-y: auto; }
            .message { padding: 10px; margin: 5px 0; border-radius: 8px; }
            .user-message { background-color: #e3f2fd; }
            .assistant-message { background-color: #f5f5f5; }
        """,
    )


if __name__ == '__main__':
    main()
