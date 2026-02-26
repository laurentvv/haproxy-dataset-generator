#!/usr/bin/env python3
"""
04_chatbot.py - Interface Gradio V3 moderne : chatbot HAProxy avec RAG hybride

Lance avec : uv run python 04_chatbot.py

Utilise l'index V3 (qwen3-embedding:8b - MTEB #1 mondial 70.58)
"""

import sys
import io
import threading
from pathlib import Path
from datetime import datetime

# Fix encoding Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Use centralized logging configuration
from logging_config import setup_logging

logger = setup_logging(__name__, log_file="gradio_app_v3.log")

try:
    import gradio as gr
except ImportError:
    print("❌ gradio non installé : uv add gradio")
    sys.exit(1)

# Importer nos modules V3
sys.path.insert(0, str(Path(__file__).parent))
logger.info("Importation des modules V3 (qwen3-embedding:8b)...")
try:
    from retriever_v3 import retrieve_context_string, _load_indexes, validate_query

    logger.info("✅ Module retriever_v3 importé avec succès")
except ImportError as e:
    logger.error("❌ Erreur d'importation du module retriever_v3: %s", e)
    raise

try:
    from llm import (
        generate_response,
        list_ollama_models,
        FALLBACK_RESPONSE,
        DEFAULT_MODEL,
    )

    logger.info("✅ Module llm importé avec succès")
    logger.info("Modèle par défaut: %s", DEFAULT_MODEL)
except ImportError as e:
    logger.error("❌ Erreur d'importation du module llm: %s", e)
    raise


# ── CSS personnalisé - Design Dark Moderne ───────────────────────────────────
CUSTOM_CSS = """
/* ── Thème Dark ─────────────────────────────────────────────────────────── */
:root {
    --haproxy-orange: #ff6b35;
    --haproxy-red: #e74c3c;
    --bg-dark: #0f0f0f;
    --bg-card: #1a1a1a;
    --bg-input: #252525;
    --text-primary: #ffffff;
    --text-secondary: #b0b0b0;
    --border-color: #333333;
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
}

/* ── Container ─────────────────────────────────────────────────────────── */
.gradio-container {
    max-width: 1800px !important;
    margin: 0 auto !important;
    background: var(--bg-dark) !important;
}

/* ── Header compact ────────────────────────────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%);
    border-radius: 12px;
    padding: 16px 24px;
    margin: 16px auto;
    text-align: center;
    color: white;
}

.app-header h1 {
    font-size: 1.6em;
    font-weight: 700;
    margin: 0;
}

.app-header .subtitle {
    font-size: 0.9em;
    opacity: 0.9;
    margin: 4px 0 0 0;
}

/* ── Chatbot en pleine largeur ────────────────────────────────────────── */
.chatbot-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
}

.chatbot-container .chatbot {
    height: 70vh !important;
    max-height: 70vh !important;
}

/* ── Messages ──────────────────────────────────────────────────────────── */
.message-user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 12px 16px !important;
}

.message-assistant {
    background: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 12px 16px !important;
    border: 1px solid var(--border-color) !important;
}

/* ── Input area ────────────────────────────────────────────────────────── */
.input-area {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
}

.input-area textarea {
    background: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    font-size: 1em !important;
}

.input-area textarea:focus {
    border-color: var(--haproxy-orange) !important;
    box-shadow: 0 0 0 2px rgba(255,107,53,0.2) !important;
}

/* ── Boutons ───────────────────────────────────────────────────────────── */
.btn-primary {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

.btn-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(255,107,53,0.4) !important;
}

/* ── Exemples - Cartes lisibles ───────────────────────────────────────── */
.examples-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
}

.examples-panel .section-title {
    font-size: 0.95em;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--haproxy-orange);
}

.example-card {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.85em;
    color: var(--text-primary);
    text-align: left;
    white-space: normal;
    height: auto;
    min-height: 50px;
    display: flex;
    align-items: center;
}

.example-card:hover {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%);
    border-color: var(--haproxy-orange);
    color: white;
    transform: translateX(4px);
}

.example-card::before {
    content: "💡";
    margin-right: 8px;
    flex-shrink: 0;
}

/* ── Sources ───────────────────────────────────────────────────────────── */
.sources-box {
    background: var(--bg-input);
    border-left: 4px solid var(--haproxy-orange);
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 12px;
    font-size: 0.85em;
}

.sources-box a {
    color: var(--haproxy-orange);
}

/* ── Welcome message ──────────────────────────────────────────────────── */
.welcome-box {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
}

.welcome-box h2 {
    color: var(--text-primary);
    margin-bottom: 8px;
}

.welcome-box p {
    color: var(--text-secondary);
}

/* ── Footer ───────────────────────────────────────────────────────────── */
.app-footer {
    text-align: center;
    padding: 12px;
    color: var(--text-secondary);
    font-size: 0.8em;
    border-top: 1px solid var(--border-color);
    margin-top: 16px;
}

.app-footer a {
    color: var(--haproxy-orange);
}

/* ── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-dark);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--haproxy-orange);
}
"""


# ── State global ──────────────────────────────────────────────────────────────
_indexes_loaded = False
_index_error = None
_index_lock = threading.Lock()


def ensure_indexes() -> tuple[bool, str]:
    """Charge les index V3 une seule fois de manière thread-safe."""
    global _indexes_loaded, _index_error

    with _index_lock:
        if _indexes_loaded:
            return True, "✅ Index V3 chargés"

        if _index_error:
            return False, f"❌ Erreur précédente: {_index_error}"

        try:
            logger.info("Tentative de chargement des index V3...")
            _load_indexes()
            _indexes_loaded = True
            _index_error = None
            logger.info("✅ Index V3 chargés avec succès (qwen3-embedding:8b)")
            return True, "✅ Index V3 chargés"
        except FileNotFoundError as e:
            _index_error = f"Index V3 introuvables: {e}"
            logger.error("❌ Index V3 introuvables: %s", e)
            return False, f"❌ {_index_error}"
        except Exception as e:
            _index_error = str(e)
            logger.error("❌ Erreur chargement index V3: %s", e)
            return False, f"❌ Erreur: {_index_error}"


def format_sources_markdown(sources: list[dict]) -> str:
    """Formate les sources en Markdown avec style amélioré."""
    if not sources:
        return ""

    lines = ["\n\n<div class='sources-box'>\n\n**📚 Sources :**\n"]
    for i, src in enumerate(sources):
        icon = "📝" if src.get("has_code") else "📄"
        title = src.get("title", "Section inconnue")
        url = src.get("url", "#")
        score = src.get("score", 0)
        lines.append(f"{icon} **[{i+1}]** [{title}]({url}) (score: {score:.2f})")

    lines.append("</div>")
    return "\n".join(lines)


def extract_message_text(message) -> str:
    """Extrait le texte d'un message Gradio 6.x."""
    if isinstance(message, str):
        return message
    elif isinstance(message, dict):
        return message.get("text", "") or message.get("content", "")
    elif isinstance(message, list):
        parts = []
        for item in message:
            if isinstance(item, dict):
                parts.append(item.get("text", "") or item.get("content", ""))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(parts)
    return str(message)


def history_to_llm_format(history: list) -> list[tuple[str, str]]:
    """Convertit l'historique Gradio ChatMessage vers format LLM."""
    llm_history = []
    user_msg = None

    for msg in history:
        role = msg.role if hasattr(msg, 'role') else msg.get("role", "")
        content = msg.content if hasattr(msg, 'content') else msg.get("content", "")

        if role == "user":
            user_msg = content
        elif role == "assistant" and user_msg is not None:
            llm_history.append((user_msg, content))
            user_msg = None

    return llm_history[-3:]


def submit_message(
    message,
    history: list,
    model_name: str,
    top_k: int,
    show_sources: bool,
):
    """Ajoute le message utilisateur à l'historique avec validation."""
    # Extract text from Gradio 6.x ChatMessage format
    if hasattr(message, 'content'):
        message_text = message.content
    elif isinstance(message, dict):
        message_text = message.get("content", "")
    elif isinstance(message, str):
        message_text = message
    else:
        message_text = str(message)
    
    logger.info("submit_message() - message='%s...'", message_text[:30] if message_text else "")

    if not message_text.strip():
        return history

    # Validate and sanitize user input
    try:
        message_text = validate_query(message_text)
    except ValueError as e:
        logger.warning("Input validation failed: %s", e)
        history.append(gr.ChatMessage(role="assistant", content=f"⚠️ **Question invalide**\n\n{str(e)}"))
        return history

    ok, status = ensure_indexes()
    if not ok:
        history.append(gr.ChatMessage(role="assistant", content=f"❌ **Erreur d'index**\n\n{status}"))
        return history

    history.append(gr.ChatMessage(role="user", content=message_text))
    return history


def respond(
    history: list,
    model_name: str,
    top_k: int,
    show_sources: bool,
):
    """Génère la réponse de l'assistant avec streaming (V3)."""
    if not history or not hasattr(history[-1], 'role') or history[-1].role != "user":
        return history

    message = history[-1].content
    logger.info("respond() V3 - message='%s...', model='%s', top_k=%d",
                message[:30] if message else "", model_name, top_k)

    try:
        logger.info("Retrieval V3 (qwen3-embedding:8b) pour: '%s'", message[:80])
        context_str, sources, low_confidence = retrieve_context_string(
            message, top_k=top_k
        )
        logger.info("Retrieval V3 terminé - %d sources, low_confidence=%s",
                   len(sources), low_confidence)
    except Exception as e:
        logger.error("❌ Erreur retrieval V3: %s", e)
        history.append(gr.ChatMessage(role="assistant", content=f"❌ **Erreur retrieval**\n\n{str(e)}"))
        yield history
        return

    if low_confidence or not context_str:
        response = FALLBACK_RESPONSE
        history.append(gr.ChatMessage(role="assistant", content=response))
        yield history
        return

    llm_history = history_to_llm_format(history[:-1])

    history.append(gr.ChatMessage(role="assistant", content="<div style='opacity: 0.7'>⏳ **Recherche en cours...**</div>"))
    yield history

    history[-1].content = ""
    logger.info("Génération avec modèle: %s", model_name)

    try:
        for token in generate_response(
            question=message,
            context=context_str,
            model=model_name,
            history=llm_history,
            temperature=0.1,
        ):
            history[-1].content += token
            yield history

        logger.info("Génération terminée - %d caractères", len(history[-1].content))

    except Exception as e:
        logger.error("❌ Erreur génération: %s", e)
        history[-1].content = f"❌ **Erreur génération**\n\n{str(e)}"
        yield history
        return

    # Add sources if enabled
    if show_sources and sources:
        history[-1].content += format_sources_markdown(sources)

    yield history


def get_welcome_message() -> str:
    """Génère un message de bienvenue."""
    return """
<div class="welcome-box">

# 👋 Assistant HAProxy 3.2

**RAG hybride avec qwen3-embedding:8b (MTEB #1 - 70.58)**

---

### 💬 Posez votre question

- "Comment configurer un health check HTTP ?"
- "Syntaxe de la directive bind avec SSL ?"
- "Limiter les connexions par IP avec stick-table ?"

</div>
"""


# ── Construction de l'UI ──────────────────────────────────────────────────────
def build_ui():
    """Construit l'interface Gradio V3 avec design dark moderne."""
    logger.info("Construction de l'UI V3 avec design dark...")

    try:
        available_models = list_ollama_models()
    except Exception:
        available_models = []

    if not available_models:
        available_models = [DEFAULT_MODEL, "llama3.1:8b", "qwen2.5:7b"]

    default_model = DEFAULT_MODEL if DEFAULT_MODEL in available_models else (
        available_models[0] if available_models else DEFAULT_MODEL
    )

    logger.info("Modèles disponibles: %s", available_models)
    logger.info("Modèle par défaut: %s", default_model)

    with gr.Blocks(
        title="HAProxy Docs Chatbot V3",
        fill_width=True,
        fill_height=True,
    ) as app:

        # ── Header ───────────────────────────────────────────────────────
        gr.HTML("""
            <div class="app-header">
                <h1>🔧 HAProxy 3.2 Documentation Assistant</h1>
                <p class="subtitle">qwen3-embedding:8b (MTEB #1 - 70.58)</p>
            </div>
        """)

        # ── Main layout ──────────────────────────────────────────────────
        with gr.Row(equal_height=False):
            # ── Left Sidebar ───────────────────────────────────────────
            with gr.Column(scale=1, min_width=280):
                # Configuration
                with gr.Group():
                    gr.Markdown("### ⚙️ Configuration")
                    
                    model_dd = gr.Dropdown(
                        choices=available_models,
                        value=default_model,
                        label="Modèle LLM",
                    )
                    
                    top_k = gr.Slider(
                        minimum=1,
                        maximum=15,
                        value=5,
                        step=1,
                        label="Profondeur (top-k)",
                    )
                    
                    show_sources_chk = gr.Checkbox(
                        value=True,
                        label="📚 Afficher les sources",
                    )

                # Exemples
                with gr.Group(elem_classes="examples-panel"):
                    gr.Markdown("### 💡 Exemples")

                    examples_list = [
                        "Comment configurer un health check HTTP ?",
                        "Syntaxe de bind avec SSL ?",
                        "Limiter connexions par IP ?",
                        "Utiliser ACLs pour routage ?",
                        "Configurer timeouts ?",
                        "Activer stats enable ?",
                    ]

                    example_buttons = []
                    for q in examples_list:
                        btn = gr.Button(
                            q,
                            variant="secondary",
                            elem_classes="example-card",
                        )
                        example_buttons.append(btn)

            # ── Right Main Area ────────────────────────────────────────
            with gr.Column(scale=4):
                # Input (moved up for example clicks)
                with gr.Group(elem_classes="input-area"):
                    msg_box = gr.Textbox(
                        placeholder="Posez votre question sur HAProxy 3.2...",
                        show_label=False,
                        lines=2,
                    )
                    
                    with gr.Row():
                        send_btn = gr.Button(
                            "🚀 Envoyer",
                            variant="primary",
                            elem_classes="btn-primary",
                        )
                        clear_btn = gr.Button("🗑️ Effacer", variant="secondary")

                # Chatbot
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height="70vh",
                    render_markdown=True,
                    avatar_images=(None, "🔧"),
                    elem_classes="chatbot-container",
                    buttons=["share", "copy", "copy_all"],
                    layout="bubble",
                    value=[gr.ChatMessage(role="assistant", content=get_welcome_message())],
                )

        # ── Footer ─────────────────────────────────────────────────────
        gr.HTML("""
            <div class="app-footer">
                <a href="https://docs.haproxy.org/3.2/" target="_blank">📚 docs.haproxy.org</a> •
                <a href="https://github.com/haproxy/haproxy" target="_blank">💻 GitHub</a>
            </div>
        """)

        # ── Events ─────────────────────────────────────────────────────
        def handle_submit(message, history, model_name, top_k, show_sources):
            history = submit_message(message, history, model_name, top_k, show_sources)
            return history
        
        def handle_respond(history, model_name, top_k, show_sources):
            for response in respond(history, model_name, top_k, show_sources):
                yield response

        msg_box.submit(
            fn=handle_submit,
            inputs=[msg_box, chatbot, model_dd, top_k, show_sources_chk],
            outputs=[chatbot],
        ).then(
            fn=handle_respond,
            inputs=[chatbot, model_dd, top_k, show_sources_chk],
            outputs=[chatbot],
        )

        send_btn.click(
            fn=handle_submit,
            inputs=[msg_box, chatbot, model_dd, top_k, show_sources_chk],
            outputs=[chatbot],
        ).then(
            fn=handle_respond,
            inputs=[chatbot, model_dd, top_k, show_sources_chk],
            outputs=[chatbot],
        )

        clear_btn.click(
            fn=lambda: [gr.ChatMessage(role="assistant", content=get_welcome_message())],
            outputs=[chatbot],
        )

        # Example clicks - fill msg_box with example text
        def make_fill_fn(text):
            return lambda: text
        
        for btn, example_text in zip(example_buttons, examples_list):
            btn.click(fn=make_fill_fn(example_text), inputs=None, outputs=msg_box)

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HAProxy RAG Chatbot V3 - Dark Mode")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'écoute")
    parser.add_argument("--port", default=7861, type=int, help="Port (défaut: 7861)")
    parser.add_argument("--share", action="store_true", help="Partager via Gradio")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  🔧 HAProxy 3.2 Documentation Assistant V3")
    print("  🌙 Dark Mode - Design optimisé")
    print("=" * 65)
    print(f"  🌐 URL        : http://{args.host}:{args.port}")
    print(f"  🤖 Ollama     : http://localhost:11434")
    print(f"  📊 Embedding  : qwen3-embedding:8b (MTEB #1 - 70.58)")
    print(f"  💬 Modèle     : {DEFAULT_MODEL}")
    print(f"  🎨 Gradio     : {gr.__version__}")
    print("=" * 65 + "\n")

    print("📂 Préchargement des index V3...")
    ok, status = ensure_indexes()
    print(f"   {status}")

    try:
        models = list_ollama_models()
        print(f"   🤖 Modèles  : {', '.join(models[:5])}{'...' if len(models) > 5 else ''}")
    except Exception:
        print(f"   ❌ Erreur modèles")
        models = []

    print()

    try:
        app = build_ui()
        print("🚀 Lancement de l'application Gradio V3...\n")
        print("   Appuyez sur CTRL+C pour arrêter\n")
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=True,
            favicon_path=None,
            theme=gr.themes.Default(),
            css=CUSTOM_CSS,
        )
    except Exception as e:
        logger.critical("❌ Erreur critique: %s", e)
        print(f"\n❌ ERREUR: {e}")
        print("Consultez 'gradio_app_v3.log' pour plus de détails.")
