#!/usr/bin/env python3
"""
04_app_v3.py - Interface Gradio V3 : chatbot HAProxy avec RAG hybride + qwen3-embedding:8b

Lance avec : python 04_app_v3.py

Utilise l'index V3 (qwen3-embedding:8b - MTEB #1 mondial 70.58)
"""
import sys
import io
import threading
import logging
import re
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Use centralized logging configuration
from logging_config import setup_logging
logger = setup_logging(__name__, log_file='gradio_app_v3.log')

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


# ── CSS personnalisé ──────────────────────────────────────────────────────────
CUSTOM_CSS = """
.gradio-container { max-width: 1100px !important; margin: auto; }
.app-title { text-align: center; padding: 10px 0 5px 0; }
.app-title h1 { font-size: 1.8em; color: #2c3e50; margin: 0; }
.app-title p  { color: #7f8c8d; margin: 4px 0 0 0; font-size: 0.9em; }
.sources-box {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.85em;
    margin-top: 8px;
}
.sources-box .source-item { margin: 6px 0; }
.btn-index { background: #27ae60 !important; color: white !important; }
.btn-clear  { background: #e74c3c !important; color: white !important; }
.low-confidence {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 0.85em;
    margin-top: 8px;
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
    """Formate les sources en Markdown."""
    if not sources:
        return ""
    
    lines = ["\n\n---\n\n**📚 Sources :**\n"]
    for i, src in enumerate(sources):
        icon = "📝" if src.get("has_code") else "📄"
        title = src.get("title", "Section inconnue")
        url = src.get("url", "#")
        score = src.get("score", 0)
        lines.append(f"{icon} **[{i+1}]** [{title}]({url}) (score: {score:.2f})")
    
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


def history_to_llm_format(history: list[dict]) -> list[tuple[str, str]]:
    """Convertit l'historique Gradio vers format LLM."""
    llm_history = []
    user_msg = None
    
    for msg in history:
        role = msg.get("role", "")
        raw_content = msg.get("content", "")
        content = extract_message_text(raw_content)
        
        if role == "user":
            user_msg = content
        elif role == "assistant" and user_msg is not None:
            llm_history.append((user_msg, content))
            user_msg = None
    
    return llm_history[-3:]


def submit_message(
    message,
    history: list[dict],
    model_name: str,
    top_k: int,
    show_sources: bool,
):
    """Ajoute le message utilisateur à l'historique avec validation."""
    message_text = extract_message_text(message)
    logger.info("submit_message() - message='%s...'", message_text[:30] if message_text else "")

    if not message_text.strip():
        return history

    # Validate and sanitize user input
    try:
        message_text = validate_query(message_text)
    except ValueError as e:
        logger.warning("Input validation failed: %s", e)
        history.append({"role": "assistant", "content": f"⚠️ Question invalide: {str(e)}"})
        return history

    ok, status = ensure_indexes()
    if not ok:
        history.append({"role": "assistant", "content": status})
        return history

    history.append({"role": "user", "content": message_text})
    return history


def respond(
    history: list[dict],
    model_name: str,
    top_k: int,
    show_sources: bool,
):
    """Génère la réponse de l'assistant avec streaming (V3)."""
    if not history or history[-1].get("role") != "user":
        return history
    
    raw_message = history[-1]["content"]
    message = extract_message_text(raw_message)
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
        history.append({"role": "assistant", "content": f"❌ Erreur retrieval V3 : {e}"})
        yield history
        return
    
    if low_confidence or not context_str:
        response = FALLBACK_RESPONSE
        history.append({"role": "assistant", "content": response})
        yield history
        return
    
    llm_history = history_to_llm_format(history[:-1])
    
    history.append({"role": "assistant", "content": "⏳ Recherche en cours (V3)..."})
    yield history
    
    history[-1]["content"] = ""
    logger.info("Génération avec modèle: %s", model_name)
    
    try:
        for token in generate_response(
            question=message,
            context=context_str,
            model=model_name,
            history=llm_history,
            temperature=0.1,
        ):
            history[-1]["content"] += token
            yield history
        
        logger.info("Génération terminée - %d caractères", len(history[-1]["content"]))
        
    except Exception as e:
        logger.error("❌ Erreur génération: %s", e)
        history[-1]["content"] = f"❌ Erreur génération : {e}"
        yield history
        return
    
    if show_sources and sources:
        history[-1]["content"] += format_sources_markdown(sources)
    
    if low_confidence:
        history[-1]["content"] += '\n\n<div class="low-confidence">⚠️ Confiance faible — vérifiez la documentation officielle</div>'
    
    yield history


def reindex_fn():
    """Lance le pipeline de réindexation V3."""
    import subprocess
    
    logger.info("Début de la réindexation V3")
    
    scripts = ["01_scrape.py", "02_ingest_v2.py", "03_build_index_v3.py"]
    
    for script_name in scripts:
        path = Path(__file__).parent / script_name
        if not path.exists():
            yield f"❌ Script introuvable : {script_name}"
            return
        
        yield f"🔄 {script_name}..."
        logger.info("Exécution de %s...", script_name)
        
        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent),
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            yield f"❌ Timeout pour {script_name}"
            return
        except Exception as e:
            yield f"❌ Erreur pour {script_name}: {e}"
            return
        
        if result.returncode != 0:
            yield f"❌ Erreur dans {script_name}:\n{result.stderr[:500]}"
            return
        
        yield f"✅ {script_name} terminé"
    
    global _indexes_loaded
    _indexes_loaded = False
    
    yield "✅ Réindexation V3 complète ! Rechargez la page pour utiliser les nouveaux index."


# ── Construction de l'UI ──────────────────────────────────────────────────────
def build_ui():
    """Construit l'interface Gradio V3."""
    logger.info("Construction de l'UI V3...")
    
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
    
    with gr.Blocks(title="HAProxy Docs Chatbot V3", css=CUSTOM_CSS) as app:
        
        gr.HTML("""
            <div class="app-title">
                <h1>🔧 HAProxy 3.2 Documentation Assistant V3</h1>
                <p>Embedding: qwen3-embedding:8b (MTEB #1 mondial - 70.58)</p>
            </div>
        """)
        
        with gr.Row():
            with gr.Column(scale=1, min_width=240):
                gr.Markdown("### ⚙️ Paramètres")
                
                model_dd = gr.Dropdown(
                    choices=available_models,
                    value=default_model,
                    label="Modèle Ollama",
                )
                top_k = gr.Slider(
                    minimum=1, maximum=10, value=5, step=1,
                    label="Chunks de contexte (top-k)"
                )
                sources_chk = gr.Checkbox(
                    value=True, label="Afficher les sources"
                )
                
                gr.Markdown("---\n### 🔄 Réindexation")
                ridx_btn = gr.Button("🔄 Réindexer V3", variant="secondary")
                ridx_status = gr.Markdown("")
                
                gr.Markdown("---\n### 💡 Exemples")
                examples = [
                    "Comment configurer un health check HTTP ?",
                    "Syntaxe de la directive bind ?",
                    "Limiter les connexions par IP ?",
                    "Comment utiliser les ACLs ?",
                    "Options de timeout disponibles ?",
                    "Configurer SSL/TLS sur un frontend ?",
                ]
                example_btns = [
                    gr.Button(q, size="sm", variant="secondary") for q in examples
                ]
            
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation V3",
                    height=560,
                    render_markdown=True,
                    avatar_images=(None, "🔧"),
                )
                
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="Ex: Comment configurer un health check TCP ?",
                        show_label=False,
                        scale=5,
                        lines=2,
                        container=False,
                    )
                    send_btn = gr.Button("🚀 Envoyer", variant="primary", scale=1)
                
                clear_btn = gr.Button("🗑️ Effacer l'historique", size="sm")
        
        msg_box.submit(
            fn=submit_message,
            inputs=[msg_box, chatbot, model_dd, top_k, sources_chk],
            outputs=[chatbot],
        ).then(
            fn=respond,
            inputs=[chatbot, model_dd, top_k, sources_chk],
            outputs=[chatbot],
        )
        
        send_btn.click(
            fn=submit_message,
            inputs=[msg_box, chatbot, model_dd, top_k, sources_chk],
            outputs=[chatbot],
        ).then(
            fn=respond,
            inputs=[chatbot, model_dd, top_k, sources_chk],
            outputs=[chatbot],
        )
        
        clear_btn.click(fn=lambda: [], outputs=[chatbot])
        ridx_btn.click(fn=reindex_fn, outputs=ridx_status)
        
        for btn, q in zip(example_btns, examples):
            btn.click(fn=lambda x=q: x, outputs=msg_box)
        
        gr.Markdown(
            "---\n💬 Documentation HAProxy 3.2 | "
            "🏠 [docs.haproxy.org](https://docs.haproxy.org/3.2/) | "
            "📊 Embedding: qwen3-embedding:8b (MTEB 70.58)"
        )
    
    return app


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="HAProxy RAG Chatbot V3 (qwen3-embedding:8b)")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'écoute")
    parser.add_argument("--port", default=7861, type=int, help="Port (défaut: 7861)")
    parser.add_argument("--share", action="store_true", help="Partager via Gradio")
    args = parser.parse_args()
    
    print("\n" + "=" * 55)
    print("  🔧 HAProxy 3.2 Documentation Assistant V3")
    print("=" * 55)
    print(f"  URL       : http://{args.host}:{args.port}")
    print(f"  Ollama    : http://localhost:11434")
    print(f"  Embedding : qwen3-embedding:8b (MTEB #1 - 70.58)")
    print(f"  Modèle    : {DEFAULT_MODEL}")
    print(f"  Gradio    : {gr.__version__}")
    print("=" * 55 + "\n")
    
    print("📂 Préchargement des index V3...")
    ok, status = ensure_indexes()
    print(f"   {status}")
    
    try:
        models = list_ollama_models()
        print(f"   Modèles  : {models}")
    except Exception:
        print(f"   ❌ Erreur modèles")
        models = []
    
    print()
    
    try:
        app = build_ui()
        print("🚀 Lancement de l'application Gradio V3...\n")
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=True,
        )
    except Exception as e:
        logger.critical("❌ Erreur critique: %s", e)
        print(f"\n❌ ERREUR: {e}")
        print("Consultez 'gradio_app_v3.log' pour plus de détails.")
