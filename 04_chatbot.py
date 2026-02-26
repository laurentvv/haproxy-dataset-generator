#!/usr/bin/env python3
"""
04_chatbot.py - Interface Gradio V3 simple et robuste

Lance avec : uv run python 04_chatbot.py
"""

import sys
import io
import threading
from pathlib import Path

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
logger.info("Importation des modules V3...")
try:
    from retriever_v3 import retrieve_context_string, _load_indexes

    logger.info("✅ retriever_v3 OK")
except ImportError as e:
    logger.error("❌ Erreur retriever_v3: %s", e)
    raise

try:
    from llm import (
        generate_response,
        list_ollama_models,
        FALLBACK_RESPONSE,
        DEFAULT_MODEL,
    )

    logger.info("✅ llm OK - Modèle: %s", DEFAULT_MODEL)
except ImportError as e:
    logger.error("❌ Erreur llm: %s", e)
    raise


# Custom CSS
CUSTOM_CSS = """
.gradio-container { max-width: 1400px !important; margin: auto !important; }
footer { visibility: hidden }
"""


# ── State global ──────────────────────────────────────────────────────────────
_indexes_loaded = False
_index_lock = threading.Lock()


def ensure_indexes():
    """Charge les index une fois."""
    global _indexes_loaded

    with _index_lock:
        if _indexes_loaded:
            return True
        try:
            _load_indexes()
            _indexes_loaded = True
            logger.info("✅ Index chargés")
            return True
        except Exception as e:
            logger.error("❌ Index: %s", e)
            return False


def chat_respond(message, history):
    """Répond à une question avec RAG."""
    logger.info("Question: %s", message[:50])

    # Retrieval
    try:
        context_str, sources, low_confidence = retrieve_context_string(message, top_k=5)
    except Exception as e:
        logger.error("Erreur retrieval: %s", e)
        return f"❌ Erreur retrieval: {e}"

    if low_confidence or not context_str:
        return FALLBACK_RESPONSE

    # Format context for LLM (system prompt used in llm.py)
    _ = f"""Tu es un assistant expert HAProxy 3.2.
RÉPONDS UNIQUEMENT à partir du contexte ci-dessous.
Cite TOUJOURS la source entre parenthèses.

<context>
{context_str}
</context>
"""

    # Build history for LLM
    llm_history = []
    for i, msg in enumerate(history):
        if isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
        else:
            role = msg[0] if len(msg) > 0 else ""
            content = msg[1] if len(msg) > 1 else ""

        if role == "user" and i < len(history) - 1:
            llm_history.append((content, ""))
        elif role == "assistant":
            if llm_history:
                llm_history[-1] = (llm_history[-1][0], content)

    # Generate response
    response = ""
    try:
        for token in generate_response(
            question=message,
            context=context_str,
            model=DEFAULT_MODEL,
            history=llm_history[-3:],
            temperature=0.1,
        ):
            response += token
            yield response

        # Add sources
        if sources:
            response += "\n\n---\n\n**Sources :**\n"
            for i, src in enumerate(sources):
                icon = "📝" if src.get("has_code") else "📄"
                title = src.get("title", "?")
                url = src.get("url", "#")
                response += f"{icon} [{i + 1}] [{title}]({url})\n"

        yield response

    except Exception as e:
        logger.error("Erreur génération: %s", e)
        yield f"❌ Erreur: {e}"


def get_examples():
    """Retourne des exemples de questions."""
    return [
        ["Comment configurer un health check HTTP ?"],
        ["Syntaxe de la directive bind avec SSL ?"],
        ["Limiter les connexions par IP avec stick-table ?"],
        ["Utiliser les ACLs pour le routage HTTP ?"],
        ["Configurer les timeouts client/server ?"],
        ["Activer les statistiques avec stats enable ?"],
    ]


# ── Build UI ──────────────────────────────────────────────────────────────────
def build_ui():
    """Construit l'interface avec ChatInterface."""
    logger.info("Construction UI...")

    # Check indexes
    ensure_indexes()

    # Get available models
    try:
        _ = list_ollama_models()
    except Exception:
        pass  # Use default model if list fails

    # Create ChatInterface
    with gr.Blocks(fill_width=True) as demo:
        gr.Markdown("""
        # 🔧 HAProxy 3.2 Documentation Assistant
        
        **RAG hybride avec qwen3-embedding:8b (MTEB #1 - 70.58)**
        
        Pose tes questions sur la configuration HAProxy 3.2
        """)

        chatbot = gr.Chatbot(
            label="Conversation",
            height=600,
            avatar_images=(None, "🔧"),
        )

        msg = gr.Textbox(
            placeholder="Pose ta question sur HAProxy 3.2...",
            label="Question",
            lines=2,
        )

        with gr.Row():
            submit_btn = gr.Button("🚀 Envoyer", variant="primary")
            clear_btn = gr.Button("🗑️ Effacer", variant="secondary")

        # Examples
        gr.Examples(
            examples=get_examples(),
            inputs=msg,
            label="💡 Exemples",
        )

        gr.Markdown("""
        ---
        📚 [docs.haproxy.org](https://docs.haproxy.org/3.2/) | 
        💻 [GitHub](https://github.com/haproxy/haproxy)
        """)

        # Events
        def user_submit(message, history):
            return "", history + [{"role": "user", "content": message}]

        msg.submit(
            fn=user_submit,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        ).then(
            fn=chat_respond,
            inputs=[msg, chatbot],
            outputs=[chatbot],
        )

        submit_btn.click(
            fn=user_submit,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        ).then(
            fn=chat_respond,
            inputs=[msg, chatbot],
            outputs=[chatbot],
        )

        clear_btn.click(
            fn=lambda: [],
            outputs=[chatbot],
        )

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HAProxy RAG Chatbot V3")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", default=7861, type=int, help="Port")
    parser.add_argument("--share", action="store_true", help="Share")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  🔧 HAProxy 3.2 Documentation Assistant V3")
    print("=" * 60)
    print(f"  URL: http://{args.host}:{args.port}")
    print("  Embedding: qwen3-embedding:8b")
    print(f"  LLM: {DEFAULT_MODEL}")
    print(f"  Gradio: {gr.__version__}")
    print("=" * 60 + "\n")

    try:
        demo = build_ui()
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            css=CUSTOM_CSS,
        )
    except Exception as e:
        logger.critical("❌ Erreur: %s", e)
        print(f"\n❌ {e}")
