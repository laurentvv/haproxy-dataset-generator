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


# ── CSS personnalisé - Design moderne professionnel ───────────────────────────
CUSTOM_CSS = """
/* ── Variables de couleurs ───────────────────────────────────────────────── */
:root {
    --haproxy-orange: #e84e2c;
    --haproxy-red: #d63031;
    --haproxy-dark: #2d3436;
    --haproxy-gray: #636e72;
    --bg-light: #f8f9fa;
    --bg-white: #ffffff;
    --border-color: #e9ecef;
    --shadow-sm: 0 2px 4px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
}

/* ── Container principal ─────────────────────────────────────────────────── */
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    min-height: 100vh;
}

/* ── Header avec gradient ───────────────────────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%);
    border-radius: var(--radius-lg);
    padding: 32px 40px;
    margin: 20px auto;
    max-width: 1200px;
    box-shadow: var(--shadow-lg);
    text-align: center;
    color: white;
}

.app-header h1 {
    font-size: 2.2em;
    font-weight: 700;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.app-header .subtitle {
    font-size: 1.1em;
    opacity: 0.95;
    margin: 0;
    font-weight: 400;
}

.app-header .badge {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 0.85em;
    margin-top: 12px;
    backdrop-filter: blur(10px);
}

/* ── Sidebar de configuration ──────────────────────────────────────────── */
.config-panel {
    background: var(--bg-white);
    border-radius: var(--radius-md);
    padding: 24px;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-color);
}

.config-panel .section-title {
    font-size: 1.1em;
    font-weight: 600;
    color: var(--haproxy-dark);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--haproxy-orange);
}

/* ── Chatbot area ──────────────────────────────────────────────────────── */
.chatbot-container {
    background: var(--bg-white);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--border-color);
    overflow: hidden;
}

.chatbot-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 16px 24px;
    font-weight: 600;
    font-size: 1.1em;
}

/* ── Message bubbles ───────────────────────────────────────────────────── */
.message-user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 14px 18px !important;
    box-shadow: var(--shadow-sm);
}

.message-assistant {
    background: var(--bg-light) !important;
    color: var(--haproxy-dark) !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 14px 18px !important;
    border: 1px solid var(--border-color) !important;
}

/* ── Input area ────────────────────────────────────────────────────────── */
.input-area {
    background: var(--bg-white);
    border-radius: var(--radius-md);
    padding: 20px;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-color);
}

.input-area textarea {
    border-radius: var(--radius-sm) !important;
    border: 2px solid var(--border-color) !important;
    font-size: 1em !important;
    transition: all 0.3s ease;
}

.input-area textarea:focus {
    border-color: var(--haproxy-orange) !important;
    box-shadow: 0 0 0 3px rgba(232, 78, 44, 0.1) !important;
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
.btn-primary {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: var(--shadow-sm) !important;
}

.btn-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-md) !important;
}

.btn-secondary {
    background: var(--bg-light) !important;
    color: var(--haproxy-dark) !important;
    border: 2px solid var(--border-color) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
}

.btn-danger {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%) !important;
    color: white !important;
    border: none !important;
}

/* ── Examples cards ───────────────────────────────────────────────────── */
.examples-panel {
    background: var(--bg-white);
    border-radius: var(--radius-md);
    padding: 24px;
    box-shadow: var(--shadow-md);
    border: 1px solid var(--border-color);
}

.example-card {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    padding: 14px 18px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9em;
    line-height: 1.5;
}

.example-card:hover {
    background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
    border-color: var(--haproxy-orange);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.example-card::before {
    content: "💡";
    margin-right: 8px;
}

/* ── Sources box ───────────────────────────────────────────────────────── */
.sources-box {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-left: 4px solid var(--haproxy-orange);
    border-radius: var(--radius-sm);
    padding: 16px 20px;
    margin-top: 16px;
    font-size: 0.9em;
}

.sources-box .source-item {
    margin: 8px 0;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);
}

.sources-box .source-item:last-child {
    border-bottom: none;
}

/* ── Low confidence warning ───────────────────────────────────────────── */
.low-confidence {
    background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
    border-left: 4px solid #ffc107;
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    margin-top: 12px;
    font-size: 0.9em;
    color: #856404;
}

/* ── Status indicators ────────────────────────────────────────────────── */
.status-indicator {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 500;
}

.status-ok {
    background: #d4edda;
    color: #155724;
}

.status-error {
    background: #f8d7da;
    color: #721c24;
}

/* ── Footer ───────────────────────────────────────────────────────────── */
.app-footer {
    text-align: center;
    padding: 24px;
    color: var(--haproxy-gray);
    font-size: 0.9em;
    border-top: 1px solid var(--border-color);
    margin-top: 40px;
    background: var(--bg-white);
    border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.app-footer a {
    color: var(--haproxy-orange);
    text-decoration: none;
    font-weight: 500;
}

.app-footer a:hover {
    text-decoration: underline;
}

/* ── Scrollbar custom ─────────────────────────────────────────────────── */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-light);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: var(--haproxy-gray);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--haproxy-dark);
}

/* ── Animations ──────────────────────────────────────────────────────── */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.loading-pulse {
    animation: pulse 1.5s ease-in-out infinite;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.message-animate {
    animation: slideIn 0.3s ease-out;
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

    lines = ["\n\n<div class='sources-box'>\n\n**📚 Sources de la documentation :**\n"]
    for i, src in enumerate(sources):
        icon = "📝" if src.get("has_code") else "📄"
        title = src.get("title", "Section inconnue")
        url = src.get("url", "#")
        score = src.get("score", 0)
        category = src.get("ia_category", "general")
        lines.append(
            f"<div class='source-item'>{icon} **[{i + 1}]** [{title}]({url})</div>"
        )
        lines.append(f"   *Catégorie: {category} | Score: {score:.2f}*")

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
    logger.info(
        "submit_message() - message='%s...'", message_text[:30] if message_text else ""
    )

    if not message_text.strip():
        return history

    # Validate and sanitize user input
    try:
        message_text = validate_query(message_text)
    except ValueError as e:
        logger.warning("Input validation failed: %s", e)
        history.append(
            {"role": "assistant", "content": f"⚠️ **Question invalide**\n\n{str(e)}"}
        )
        return history

    ok, status = ensure_indexes()
    if not ok:
        history.append(
            {"role": "assistant", "content": f"❌ **Erreur d'index**\n\n{status}"}
        )
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
    logger.info(
        "respond() V3 - message='%s...', model='%s', top_k=%d",
        message[:30] if message else "",
        model_name,
        top_k,
    )

    try:
        logger.info("Retrieval V3 (qwen3-embedding:8b) pour: '%s'", message[:80])
        context_str, sources, low_confidence = retrieve_context_string(
            message, top_k=top_k
        )
        logger.info(
            "Retrieval V3 terminé - %d sources, low_confidence=%s",
            len(sources),
            low_confidence,
        )
    except Exception as e:
        logger.error("❌ Erreur retrieval V3: %s", e)
        history.append(
            {"role": "assistant", "content": f"❌ **Erreur retrieval**\n\n{str(e)}"}
        )
        yield history
        return

    if low_confidence or not context_str:
        response = FALLBACK_RESPONSE
        history.append({"role": "assistant", "content": response})
        yield history
        return

    llm_history = history_to_llm_format(history[:-1])

    history.append(
        {
            "role": "assistant",
            "content": "<div class='loading-pulse'>⏳ **Recherche en cours...**\n\nAnalyse de la documentation HAProxy 3.2 avec qwen3-embedding:8b</div>",
        }
    )
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
        history[-1]["content"] = f"❌ **Erreur génération**\n\n{str(e)}"
        yield history
        return

    # Add sources if enabled
    if show_sources and sources:
        history[-1]["content"] += format_sources_markdown(sources)

    # Add low confidence warning if needed
    if low_confidence:
        history[-1]["content"] += (
            '\n\n<div class="low-confidence">⚠️ **Confiance faible** — Vérifiez la documentation officielle pour confirmation.</div>'
        )

    yield history


def reindex_fn():
    """Lance le pipeline de réindexation V3."""
    import subprocess

    logger.info("Début de la réindexation V3")

    scripts = ["01_scrape.py", "02_chunking.py", "03_indexing.py"]

    for script_name in scripts:
        path = Path(__file__).parent / script_name
        if not path.exists():
            yield f"❌ Script introuvable : {script_name}"
            return

        yield f"🔄 **{script_name}**...\n\nExécution en cours..."
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
            yield f"❌ **Timeout** pour {script_name}"
            return
        except Exception as e:
            yield f"❌ **Erreur** pour {script_name}: {e}"
            return

        if result.returncode != 0:
            yield f"❌ **Erreur dans {script_name}**:\n\n```{result.stderr[:500]}```"
            return

        yield f"✅ **{script_name}** terminé avec succès"

    global _indexes_loaded
    _indexes_loaded = False

    yield "✅ **Réindexation V3 complète !**\n\nRechargez la page pour utiliser les nouveaux index."


def get_welcome_message() -> str:
    """Génère un message de bienvenue avec statistiques."""
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    return f"""
<div style="text-align: center; padding: 40px 20px;">

# 👋 Bienvenue sur l'Assistant HAProxy 3.2

**Système RAG hybride de nouvelle génération**

---

### 🎯 Fonctionnalités

| Technologie | Détails |
|-------------|---------|
| **Embedding** | qwen3-embedding:8b (MTEB #1 mondial - 70.58) |
| **Retrieval** | Hybride Vectoriel + Lexical (BM25) + RRF |
| **Reranking** | FlashRank avec IA metadata boosting |
| **LLM** | Modèles Ollama locaux |

### 📊 Performance

- ✅ **80%+** de questions résolues
- ⚡ **<25s** temps de réponse moyen
- 📚 **3600+** chunks indexés

---

### 💬 Comment ça marche ?

1. **Posez votre question** en français ou en anglais
2. **Le système recherche** dans la documentation HAProxy 3.2
3. **L'IA génère** une réponse précise avec sources

### 🚀 Exemples de questions

- "Comment configurer un health check HTTP ?"
- "Syntaxe de la directive bind avec SSL ?"
- "Limiter les connexions par IP avec stick-table ?"
- "Utiliser les ACLs pour le routage ?"

---

<p style="color: #636e72; font-size: 0.9em;">
    Dernière mise à jour : {now} | Documentation HAProxy 3.2
</p>

</div>
"""


# ── Construction de l'UI ──────────────────────────────────────────────────────
def build_ui():
    """Construit l'interface Gradio V3 avec design moderne."""
    logger.info("Construction de l'UI V3 avec design moderne...")

    try:
        available_models = list_ollama_models()
    except Exception:
        available_models = []

    if not available_models:
        available_models = [DEFAULT_MODEL, "llama3.1:8b", "qwen2.5:7b"]

    default_model = (
        DEFAULT_MODEL
        if DEFAULT_MODEL in available_models
        else (available_models[0] if available_models else DEFAULT_MODEL)
    )

    logger.info("Modèles disponibles: %s", available_models)
    logger.info("Modèle par défaut: %s", default_model)

    with gr.Blocks(
        title="HAProxy Docs Chatbot V3",
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue="orange",
            secondary_hue="purple",
            neutral_hue="slate",
        ),
        fill_width=True,
    ) as app:
        # ── Header avec gradient ────────────────────────────────────────────
        gr.HTML("""
            <div class="app-header">
                <h1>🔧 HAProxy 3.2 Documentation Assistant</h1>
                <p class="subtitle">Système RAG hybride avec IA de nouvelle génération</p>
                <div class="badge">
                    ✨ qwen3-embedding:8b (MTEB #1 mondial - 70.58)
                </div>
            </div>
        """)

        # ── Main content area ───────────────────────────────────────────────
        with gr.Row(equal_height=False):
            # ── Left Sidebar ───────────────────────────────────────────────
            with gr.Column(scale=1, min_width=320):
                # Configuration Panel
                with gr.Group(elem_classes="config-panel"):
                    gr.HTML("<div class='section-title'>⚙️ Configuration</div>")

                    model_dd = gr.Dropdown(
                        choices=available_models,
                        value=default_model,
                        label="Modèle LLM",
                        info="Modèle Ollama pour la génération",
                        interactive=True,
                    )

                    top_k = gr.Slider(
                        minimum=1,
                        maximum=15,
                        value=5,
                        step=1,
                        label="Profondeur de recherche (top-k)",
                        info="Nombre de chunks à récupérer",
                        interactive=True,
                    )

                    show_sources_chk = gr.Checkbox(
                        value=True,
                        label="📚 Afficher les sources",
                        info="Afficher les références après la réponse",
                    )

                # Reindex Panel
                with gr.Group(elem_classes="config-panel", visible=True):
                    gr.HTML("<div class='section-title'>🔄 Maintenance</div>")

                    ridx_btn = gr.Button(
                        "🔄 Réindexer la documentation",
                        variant="secondary",
                        size="lg",
                    )
                    ridx_status = gr.Markdown("")

                # Examples Panel
                with gr.Group(elem_classes="examples-panel"):
                    gr.HTML("<div class='section-title'>💡 Exemples de questions</div>")

                    examples = [
                        "Comment configurer un health check HTTP ?",
                        "Syntaxe de la directive bind avec SSL ?",
                        "Limiter les connexions par IP avec stick-table ?",
                        "Utiliser les ACLs pour le routage HTTP ?",
                        "Configurer les timeouts client/server ?",
                        "Activer les statistiques avec stats enable ?",
                    ]

                    for q in examples:
                        gr.Button(
                            q,
                            variant="secondary",
                            size="sm",
                            elem_classes="example-card",
                        ).click(fn=lambda x=q: x, outputs=None)

            # ── Right Main Area ────────────────────────────────────────────
            with gr.Column(scale=3, min_width=600):
                # Status indicator
                ok, status = ensure_indexes()
                status_class = "status-ok" if ok else "status-error"
                status_icon = "✅" if ok else "❌"
                gr.HTML(f"""
                    <div style="text-align: right; padding: 10px 20px;">
                        <span class="status-indicator {status_class}">
                            {status_icon} Index: {status}
                        </span>
                    </div>
                """)

                # Chatbot
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=600,
                    render_markdown=True,
                    avatar_images=(None, "🔧"),
                    elem_classes="chatbot-container",
                    show_copy_button=True,
                    bubble_full_width=False,
                )

                # Welcome message (initial state)
                if not chatbot.value:
                    chatbot.value = [[None, get_welcome_message()]]

                # Input area
                with gr.Group(elem_classes="input-area"):
                    msg_box = gr.Textbox(
                        placeholder="Posez votre question sur HAProxy 3.2...",
                        show_label=False,
                        lines=3,
                        container=False,
                        elem_classes="msg-input",
                    )

                    with gr.Row(equal_height=True):
                        send_btn = gr.Button(
                            "🚀 Envoyer",
                            variant="primary",
                            size="lg",
                            elem_classes="btn-primary",
                        )
                        clear_btn = gr.Button(
                            "🗑️ Effacer",
                            variant="secondary",
                            size="lg",
                            elem_classes="btn-danger",
                        )

        # ── Footer ─────────────────────────────────────────────────────────
        gr.HTML("""
            <div class="app-footer">
                <p>
                    🔧 <strong>HAProxy 3.2 Documentation Assistant</strong> | 
                    🏠 <a href="https://docs.haproxy.org/3.2/" target="_blank">docs.haproxy.org</a> |
                    💻 <a href="https://github.com/haproxy/haproxy" target="_blank">GitHub</a>
                </p>
                <p style="margin-top: 8px; font-size: 0.85em;">
                    Propulsé par qwen3-embedding:8b (MTEB 70.58) + RAG hybride + Ollama LLM
                </p>
            </div>
        """)

        # ── Event handlers ─────────────────────────────────────────────────
        # Handle message submission
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
            fn=lambda: [[None, get_welcome_message()]],
            outputs=[chatbot],
        )

        ridx_btn.click(fn=reindex_fn, outputs=ridx_status)

        # Handle example clicks (already handled via click handlers above)
        pass

    return app


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HAProxy RAG Chatbot V3 - Design moderne"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Adresse d'écoute")
    parser.add_argument("--port", default=7861, type=int, help="Port (défaut: 7861)")
    parser.add_argument("--share", action="store_true", help="Partager via Gradio")
    parser.add_argument(
        "--dark", action="store_true", help="Mode sombre (expérimental)"
    )
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  🔧 HAProxy 3.2 Documentation Assistant V3")
    print("  ✨ Nouveau design moderne professionnel")
    print("=" * 65)
    print(f"  🌐 URL        : http://{args.host}:{args.port}")
    print("  🤖 Ollama     : http://localhost:11434")
    print("  📊 Embedding  : qwen3-embedding:8b (MTEB #1 - 70.58)")
    print(f"  💬 Modèle     : {DEFAULT_MODEL}")
    print(f"  🎨 Gradio     : {gr.__version__}")
    print("=" * 65 + "\n")

    print("📂 Préchargement des index V3...")
    ok, status = ensure_indexes()
    print(f"   {status}")

    try:
        models = list_ollama_models()
        print(
            f"   🤖 Modèles  : {', '.join(models[:5])}{'...' if len(models) > 5 else ''}"
        )
    except Exception:
        print("   ❌ Erreur modèles")
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
        )
    except Exception as e:
        logger.critical("❌ Erreur critique: %s", e)
        print(f"\n❌ ERREUR: {e}")
        print("Consultez 'gradio_app_v3.log' pour plus de détails.")
