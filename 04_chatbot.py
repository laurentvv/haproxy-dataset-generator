#!/usr/bin/env python3
"""
04_chatbot.py - HAProxy 3.2 Documentation Chatbot
Using Gradio 6.x best practices from official docs
"""

import sys
import io
import threading
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from logging_config import setup_logging

logger = setup_logging(__name__, log_file="gradio_app_v3.log")

try:
    import gradio as gr
except ImportError:
    print("❌ gradio non installé : uv add gradio")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))

try:
    from retriever_v3 import retrieve_context_string, _load_indexes
    from llm import generate_response, FALLBACK_RESPONSE, DEFAULT_MODEL
except ImportError as e:
    logger.error("❌ Import error: %s", e)
    raise


# ── Global state ─────────────────────────────────────────────────────────────
_indexes_loaded = False
_index_lock = threading.Lock()


def ensure_indexes():
    """Load indexes once (thread-safe)."""
    global _indexes_loaded
    with _index_lock:
        if _indexes_loaded:
            return True
        try:
            _load_indexes()
            _indexes_loaded = True
            logger.info("✅ Indexes loaded")
            return True
        except Exception as e:
            logger.error("❌ Index error: %s", e)
            return False


def respond(message, history):
    """
    RAG response generator for HAProxy documentation.

    Args:
        message: User question (string)
        history: List of (user_msg, assistant_msg) tuples

    Yields:
        Streaming response text
    """
    logger.info("Question: %s", message[:50])

    # Retrieval
    try:
        context_str, sources, low_confidence = retrieve_context_string(message, top_k=5)
    except Exception as e:
        logger.error("Retrieval error: %s", e)
        yield f"❌ Retrieval error: {e}"
        return

    if low_confidence or not context_str:
        yield FALLBACK_RESPONSE
        return

    # Build LLM history (last 3 conversations)
    llm_history = []
    for user_msg, assistant_msg in history[-3:]:
        if user_msg and assistant_msg:
            llm_history.append((user_msg, assistant_msg))

    # Generate streaming response
    response = ""
    try:
        for token in generate_response(
            question=message,
            context=context_str,
            model=DEFAULT_MODEL,
            history=llm_history,
            temperature=0.1,
        ):
            response += token
            yield response

        # Append sources
        if sources:
            response += "\n\n---\n\n**📚 Sources :**\n"
            for i, src in enumerate(sources):
                icon = "📝" if src.get("has_code") else "📄"
                title = src.get("title", "Unknown")
                url = src.get("url", "#")
                response += f"{icon} [{i + 1}] [{title}]({url})\n"
            yield response

    except Exception as e:
        logger.error("Generation error: %s", e)
        yield f"❌ Generation error: {e}"


def get_examples():
    """Return example questions."""
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
    """
    Build Gradio Blocks UI following official patterns.

    Reference: https://www.gradio.app/guides/blocks-and-event-listeners
    """
    logger.info("Building UI...")
    ensure_indexes()

    # Custom CSS (passed to launch(), not Blocks())
    custom_css = """
    .gradio-container { max-width: 1400px !important; margin: auto !important; }
    footer { visibility: hidden }
    """

    with gr.Blocks(fill_width=True, title="HAProxy 3.2 Assistant") as demo:
        # Header
        gr.Markdown("""
        # 🔧 HAProxy 3.2 Documentation Assistant
        
        **RAG hybride avec qwen3-embedding:8b (MTEB #1 - 70.58)**
        
        Pose tes questions sur la configuration HAProxy 3.2
        """)

        # Chatbot - Gradio 6.x native format
        chatbot = gr.Chatbot(
            label="Conversation",
            height=600,
            avatar_images=(None, "🔧"),
            buttons=["share", "copy", "copy_all"],
            layout="bubble",
        )

        # Message input
        msg = gr.Textbox(
            placeholder="Pose ta question sur HAProxy 3.2...",
            label="Question",
            lines=2,
            submit_btn=True,
        )

        # Buttons
        with gr.Row():
            submit_btn = gr.Button("🚀 Envoyer", variant="primary")
            clear_btn = gr.Button("🗑️ Effacer", variant="secondary")

        # Examples - using gr.Examples component
        gr.Examples(
            examples=get_examples(),
            inputs=msg,
            label="💡 Exemples",
        )

        # Footer
        gr.Markdown("""
        ---
        📚 [docs.haproxy.org](https://docs.haproxy.org/3.2/) | 
        💻 [GitHub](https://github.com/haproxy/haproxy)
        """)

        # ── Event wiring ────────────────────────────────────────────────────
        # Pattern: user_submit → chatbot update → respond streaming

        def user_submit(message, history):
            """Add user message to history."""
            return "", history + [{"role": "user", "content": message}]

        # Submit on Enter
        msg.submit(
            fn=user_submit,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        ).then(
            fn=respond,
            inputs=[msg, chatbot],
            outputs=[chatbot],
        )

        # Submit on button click
        submit_btn.click(
            fn=user_submit,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
        ).then(
            fn=respond,
            inputs=[msg, chatbot],
            outputs=[chatbot],
        )

        # Clear history
        clear_btn.click(
            fn=lambda: [],
            outputs=[chatbot],
        )

    return demo, custom_css


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
        demo, css = build_ui()
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            css=css,  # CSS passed to launch() in Gradio 6.x
        )
    except Exception as e:
        logger.critical("❌ Critical error: %s", e)
        print(f"\n❌ {e}")
        import traceback

        traceback.print_exc()
