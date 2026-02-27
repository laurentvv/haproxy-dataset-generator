"""UI components for HAProxy Chatbot."""

import gradio as gr

from app.utils.logging import setup_logging

logger = setup_logging(__name__)


def build_header() -> gr.Markdown:
    """Construit le header de l'application.

    Returns:
        Composant Gradio Markdown avec le header
    """
    return gr.Markdown(
        """
    # 🔧 HAProxy 3.2 Documentation Assistant

    **RAG hybride avec qwen3-embedding:8b (MTEB #1 - 70.58)**

    Pose tes questions sur la configuration HAProxy 3.2
    """,
        elem_classes="app-header",
    )


def build_config_panel(
    available_models: list[str] | None = None,
) -> tuple[gr.Group, gr.Dropdown, gr.Slider, gr.Checkbox]:
    """Construit le panneau de configuration.

    Args:
        available_models: Liste des modèles disponibles (optionnel)

    Returns:
        Tuple (panel, model_dropdown, top_k_slider, show_sources)
    """
    from llm import DEFAULT_MODEL

    # Utiliser les modèles fournis ou une liste par défaut
    if available_models is None:
        available_models = [DEFAULT_MODEL, "qwen2.5:7b", "llama3.1:8b"]

    # Sélectionner le modèle par défaut
    default_model = (
        DEFAULT_MODEL if DEFAULT_MODEL in available_models else available_models[0]
    )

    with gr.Group() as panel:
        gr.Markdown("### ⚙️ Configuration")

        model_dropdown = gr.Dropdown(
            choices=available_models,
            value=default_model,
            label="Modèle LLM",
        )

        top_k_slider = gr.Slider(
            minimum=1, maximum=15, value=5, step=1, label="Profondeur (top-k)"
        )

        show_sources = gr.Checkbox(value=True, label="📚 Afficher les sources")

    return panel, model_dropdown, top_k_slider, show_sources


def build_examples_panel() -> tuple[gr.Group, list[gr.Button]]:
    """Construit le panneau d'exemples.

    Returns:
        Tuple (panel, example_buttons)
    """
    examples = [
        "Comment configurer un health check HTTP ?",
        "Syntaxe de la directive bind avec SSL ?",
        "Limiter les connexions par IP avec stick-table ?",
        "Utiliser les ACLs pour le routage HTTP ?",
        "Configurer les timeouts client/server ?",
        "Activer les statistiques avec stats enable ?",
    ]

    with gr.Group(elem_classes="examples-panel") as panel:
        gr.Markdown("### 💡 Exemples")

        example_buttons = [
            gr.Button(
                example,
                size="sm",
                variant="secondary",
                elem_classes="example-card",
            )
            for example in examples
        ]

    return panel, example_buttons


def build_chat_area() -> tuple:
    """Construit la zone de chat principale.

    Returns:
        Tuple (chat_area, msg_input, send_btn, clear_btn, chatbot)
    """
    with gr.Column() as chat_area:
        # Input zone
        with gr.Group(elem_classes="input-area"):
            msg_input = gr.Textbox(
                placeholder="Pose ta question sur HAProxy 3.2...",
                show_label=False,
                lines=2,
            )

            with gr.Row():
                send_btn = gr.Button(
                    "🚀 Envoyer", variant="primary", elem_classes="btn-primary"
                )
                clear_btn = gr.Button("🗑️ Effacer", variant="secondary")

        # Chatbot display
        chatbot = gr.Chatbot(
            label="Conversation",
            height="70vh",
            render_markdown=True,
            avatar_images=(None, "🔧"),
            elem_classes="chatbot-container",
            buttons=["share", "copy", "copy_all"],
            layout="bubble",
            value=[
                gr.ChatMessage(
                    role="assistant",
                    content=[{"type": "text", "text": get_welcome_message()}],
                )
            ],
        )

    return chat_area, msg_input, send_btn, clear_btn, chatbot


def get_welcome_message() -> str:
    """Retourne le message de bienvenue HTML.

    Returns:
        Message de bienvenue formaté en HTML
    """
    return """
    👋 Bonjour ! Je suis l'assistant HAProxy 3.2.

    Je peux t'aider avec :
    - Configuration des backends et frontends
    - Health checks et monitoring
    - ACLs et routage HTTP
    - SSL/TLS et terminaison TLS
    - Performance et optimisation
    - Et bien plus encore !

    Pose-moi une question sur HAProxy 3.2 🚀
    """
