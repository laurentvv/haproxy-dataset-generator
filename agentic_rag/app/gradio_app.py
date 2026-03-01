"""Application Gradio pour le système RAG agentic HAProxy 3.2."""

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
    )


if __name__ == '__main__':
    main()
