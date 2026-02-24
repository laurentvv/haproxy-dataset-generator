"""
04_app.py - Interface Gradio : chatbot HAProxy avec RAG hybride
Lance avec : python 06_app.py

Compatible Gradio 6.x - Format messages: {"role": "...", "content": "..."}
"""
import sys
import io
import threading
import logging
import traceback
from pathlib import Path

# Configurer l'encodage UTF-8 pour la console Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gradio_app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    import gradio as gr
except ImportError:
    print("❌ gradio non installé : uv add gradio")
    sys.exit(1)

# Importer nos modules
sys.path.insert(0, str(Path(__file__).parent))
logger.info("Importation des modules personnalisés...")
try:
    from retriever import retrieve_context_string, _load_indexes
    logger.info("✅ Module retriever importé avec succès")
except ImportError as e:
    logger.error("❌ Erreur d'importation du module retriever: %s", e)
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


# ── Sécurité ──────────────────────────────────────────────────────────────────
# Scripts autorisés pour la réindexation (sécurité)
ALLOWED_SCRIPTS = frozenset({
    "01_scrape.py",
    "02_ingest_v2.py",
    "03_build_index_v2.py",
})

# Validation des inputs (sécurité)
ALLOWED_MODELS = frozenset({
    "gemma3:latest",
    "gemma3n:latest",
    "qwen3:latest",
    "qwen3:4b",
    "llama3.1:8b",
    "lfm2.5-thinking:1.2b-bf16",
})
MAX_TOP_K = 20
MAX_MESSAGE_LENGTH = 2000


def validate_script_name(script_name: str) -> bool:
    """Valide que le script est autorisé et existe."""
    # Vérifier que le nom est dans la liste blanche
    if script_name not in ALLOWED_SCRIPTS:
        return False
    
    # Vérifier que le fichier existe dans le répertoire de base
    script_path = (Path(__file__).parent / script_name).resolve()
    base_dir = Path(__file__).parent.resolve()
    
    # Empêcher les path traversal (../)
    if not str(script_path).startswith(str(base_dir)):
        return False
    
    return script_path.exists()


def validate_inputs(model_name: str, top_k: int, message: str) -> tuple[bool, str]:
    """Valide les inputs utilisateur."""
    if model_name not in ALLOWED_MODELS:
        return False, f"Modèle non autorisé. Modèles disponibles: {', '.join(ALLOWED_MODELS)}"
    
    if not isinstance(top_k, int) or not (1 <= top_k <= MAX_TOP_K):
        return False, f"top_k doit être entre 1 et {MAX_TOP_K}"
    
    if not message or not isinstance(message, str):
        return False, "Message vide ou invalide"
    
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message trop long (max {MAX_MESSAGE_LENGTH} caractères)"
    
    return True, ""


# ── CSS personnalisé ──────────────────────────────────────────────────────────
CUSTOM_CSS = """
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
_index_error = None  # Stocke l'erreur de chargement si échec
_index_lock     = threading.Lock()


def ensure_indexes() -> tuple[bool, str]:
    """Charge les index une seule fois de manière thread-safe."""
    global _indexes_loaded, _index_error
    
    with _index_lock:
        # Déjà chargé avec succès
        if _indexes_loaded:
            return True, "✅ Index chargés"
        
        # Erreur précédente - ne pas réessayer indéfiniment
        if _index_error:
            return False, f"❌ Erreur précédente: {_index_error}"
        
        try:
            logger.info("Tentative de chargement des index...")
            _load_indexes()
            _indexes_loaded = True
            _index_error = None
            logger.info("✅ Index chargés avec succès")
            return True, "✅ Index chargés"
        except FileNotFoundError as e:
            _index_error = f"Index introuvables: {e}"
            logger.error("❌ Index introuvables: %s", e)
            return False, f"❌ {_index_error}"
        except Exception as e:
            _index_error = str(e)
            logger.error("❌ Erreur chargement index: %s", e)
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


def history_to_llm_format(history: list[dict]) -> list[tuple[str, str]]:
    """Convertit l'historique Gradio (format messages) vers format LLM (tuples)."""
    llm_history = []
    user_msg = None

    for msg in history:
        role = msg.get("role", "")
        raw_content = msg.get("content", "")
        
        # Extraire le texte (Gradio 6.x peut avoir content=liste)
        content = extract_message_text(raw_content)

        if role == "user":
            user_msg = content
        elif role == "assistant" and user_msg is not None:
            llm_history.append((user_msg, content))
            user_msg = None

    return llm_history[-3:]  # Garder les 3 derniers tours


def extract_message_text(message) -> str:
    """
    Extrait le texte d'un message Gradio 6.x.
    Gradio 6.x peut passer soit une chaîne, soit un dict {'text': '...', 'type': 'text'}
    """
    if isinstance(message, str):
        return message
    elif isinstance(message, dict):
        return message.get("text", "") or message.get("content", "")
    elif isinstance(message, list):
        # Peut être une liste de contenus
        parts = []
        for item in message:
            if isinstance(item, dict):
                parts.append(item.get("text", "") or item.get("content", ""))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(parts)
    return str(message)


def submit_message(
    message,
    history: list[dict],
    model_name: str,
    top_k: int,
    show_sources: bool,
):
    """
    Ajoute le message utilisateur à l'historique.
    Retourne: history mis à jour
    """
    # Extraire le texte du message (Gradio 6.x format)
    message_text = extract_message_text(message)
    logger.info("submit_message() - message='%s...'", message_text[:30] if message_text else "")
    
    # VALIDATION DES INPUTS
    is_valid, error_msg = validate_inputs(model_name, top_k, message_text)
    if not is_valid:
        logger.warning("Validation échouée: %s", error_msg)
        history.append({"role": "assistant", "content": f"❌ {error_msg}"})
        return history

    if not message_text.strip():
        return history

    # Vérifier les index
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
    """
    Génère la réponse de l'assistant avec streaming.
    Format Gradio 6.x : history = [{'role': 'user'|'assistant', 'content': '...'}]
    """
    if not history or history[-1].get("role") != "user":
        return history

    # Extraire le texte du dernier message
    raw_message = history[-1]["content"]
    message = extract_message_text(raw_message)
    logger.info("respond() - message='%s...', model='%s', top_k=%d",
                message[:30] if message else "", model_name, top_k)

    # ── Retrieval ──────────────────────────────────────────────────────────────
    try:
        logger.info("Retrieval pour: '%s'", message[:80])
        context_str, sources, low_confidence = retrieve_context_string(
            message, top_k=top_k
        )
        logger.info("Retrieval terminé - %d sources, low_confidence=%s",
                   len(sources), low_confidence)
    except Exception as e:
        logger.error("❌ Erreur retrieval: %s", e)
        history.append({"role": "assistant", "content": f"❌ Erreur retrieval : {e}"})
        yield history
        return

    # ── Cas confiance faible ───────────────────────────────────────────────────
    if low_confidence or not context_str:
        response = FALLBACK_RESPONSE
        history.append({"role": "assistant", "content": response})
        yield history
        return

    # ── Historique pour LLM ────────────────────────────────────────────────────
    llm_history = history_to_llm_format(history[:-1])  # Exclure le dernier message user

    # ── Streaming ──────────────────────────────────────────────────────────────
    history.append({"role": "assistant", "content": "⏳ Recherche en cours..."})
    yield history

    # Streamer la réponse
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

    # Ajouter les sources
    if show_sources and sources:
        history[-1]["content"] += format_sources_markdown(sources)

    # Warning confiance faible
    if low_confidence:
        history[-1]["content"] += '\n\n<div class="low-confidence">⚠️ Confiance faible — vérifiez la documentation officielle</div>'

    yield history


def reindex_fn():
    """Lance le pipeline de réindexation complet."""
    import subprocess

    logger.info("Début de la réindexation")

    # Liste ordonnée des scripts à exécuter
    scripts = ["01_scrape.py", "02_ingest_v2.py", "03_build_index_v2.py"]

    for script_name in scripts:
        # VALIDATION DE SÉCURITÉ
        if not validate_script_name(script_name):
            yield f"❌ Script non autorisé ou introuvable : {script_name}"
            logger.error("Tentative d'accès à un script non autorisé: %s", script_name)
            return

        path = Path(__file__).parent / script_name
        yield f"🔄 {script_name}..."
        logger.info("Exécution de %s...", script_name)

        try:
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent),
                timeout=300,
                check=False,  # Ne lève pas d'exception automatiquement
            )
        except subprocess.TimeoutExpired:
            yield f"❌ Timeout pour {script_name}"
            logger.error("Timeout pendant l'exécution de %s", script_name)
            return
        except Exception as e:
            yield f"❌ Erreur pour {script_name}: {e}"
            logger.error("Erreur pendant l'exécution de %s: %s", script_name, e)
            return

        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else "Erreur inconnue"
            yield f"❌ Erreur dans {script_name}:\n{error_msg}"
            logger.error("Échec de %s: %s", script_name, error_msg)
            return

        yield f"✅ {script_name} terminé"

    global _indexes_loaded
    _indexes_loaded = False

    yield "✅ Réindexation complète ! Rechargez la page pour utiliser les nouveaux index."


# ── Construction de l'UI ──────────────────────────────────────────────────────
def build_ui():
    """Construit l'interface Gradio."""
    logger.info("Construction de l'UI...")

    # Modèles disponibles
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

    with gr.Blocks(title="HAProxy Docs Chatbot", css=CUSTOM_CSS) as app:

        # Header
        gr.HTML("""
            <div class="app-title">
                <h1>🔧 HAProxy 3.2 Documentation Assistant</h1>
                <p>Posez vos questions sur la configuration, le management et les directives HAProxy</p>
            </div>
        """)

        with gr.Row():
            # Sidebar
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
                ridx_btn = gr.Button("🔄 Réindexer", variant="secondary")
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

            # Chat zone
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation",
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

        # Bindings - Gradio 6.x avec format messages
        chatbot_events = (
            msg_box.submit(
                fn=submit_message,
                inputs=[msg_box, chatbot, model_dd, top_k, sources_chk],
                outputs=[chatbot],
            )
            .then(
                fn=respond,
                inputs=[chatbot, model_dd, top_k, sources_chk],
                outputs=[chatbot],
            )
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

        msg_box.submit(
            fn=submit_message,
            inputs=[msg_box, chatbot, model_dd, top_k, sources_chk],
            outputs=[chatbot],
        ).then(
            fn=respond,
            inputs=[chatbot, model_dd, top_k, sources_chk],
            outputs=[chatbot],
        )

        clear_btn.click(
            fn=lambda: [],
            outputs=[chatbot],
        )

        ridx_btn.click(fn=reindex_fn, outputs=ridx_status)

        # Exemples
        for btn, q in zip(example_btns, examples):
            btn.click(fn=lambda x=q: x, outputs=msg_box)

        gr.Markdown(
            "---\n💬 Documentation HAProxy 3.2 | "
            "🏠 [docs.haproxy.org](https://docs.haproxy.org/3.2/)"
        )

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HAProxy RAG Chatbot")
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'écoute")
    parser.add_argument("--port", default=7860, type=int, help="Port")
    parser.add_argument("--share", action="store_true", help="Partager via Gradio")
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  🔧 HAProxy 3.2 Documentation Assistant")
    print("=" * 55)
    print(f"  URL       : http://{args.host}:{args.port}")
    print(f"  Ollama    : http://localhost:11434")
    print(f"  Modèle    : {DEFAULT_MODEL}")
    print(f"  Gradio    : {gr.__version__}")
    print("=" * 55 + "\n")

    # Préchargement des index
    print("📂 Préchargement des index...")
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
        print("🚀 Lancement de l'application Gradio...\n")
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=True,
        )
    except Exception as e:
        logger.critical("❌ Erreur critique: %s", e)
        print(f"\n❌ ERREUR: {e}")
        print("Consultez 'gradio_app.log' pour plus de détails.")
