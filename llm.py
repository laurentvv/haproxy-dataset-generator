"""
llm.py - Génération de réponses via Ollama avec streaming
Utilise le contexte récupéré par le retriever pour répondre avec précision.
"""
import os
import json
import requests
from typing import Generator


# ── Config ───────────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:latest"  # Changé de qwen3:latest à gemma3:latest (plus stable)
MAX_CONTEXT_CHARS = 4000  # Limite de contexte envoyé au LLM
LLM_TIMEOUT   = int(os.getenv("LLM_TIMEOUT", "300"))  # Timeout configurable (défaut: 300s)


# ── Prompt système ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant expert en HAProxy 3.2, spécialisé dans la configuration et l'administration.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT à partir du contexte de documentation fourni entre <context> et </context>.
2. Si une directive, option ou comportement n'est PAS dans le contexte, dis-le explicitement : "Cette information n'est pas dans la documentation fournie."
3. Ne jamais inventer de valeurs par défaut, de comportements ou d'options non documentés.
4. Cite toujours la section source entre parenthèses : (Source: nom_de_la_section).
5. Pour les exemples de configuration HAProxy, utilise des blocs de code avec la syntaxe haproxy.
6. Si le contexte contient un exemple de code pertinent, inclus-le dans ta réponse.
7. Réponds en français si la question est en français, en anglais si en anglais.

FORMAT DE RÉPONSE :
- Commence par une réponse directe à la question
- Détaille ensuite avec les paramètres/options importants
- Inclus un exemple de configuration si pertinent
- Termine par les sources utilisées"""


PROMPT_TEMPLATE = """<context>
{context}
</context>

Question : {question}"""


FALLBACK_RESPONSE = """⚠️ Je n'ai pas trouvé d'information suffisamment précise dans la documentation HAProxy pour répondre à cette question.

Suggestions :
- Reformule ta question en utilisant des termes techniques HAProxy précis (ex: "option httpchk", "backend", "ACL")
- Consulte directement la documentation : https://docs.haproxy.org/3.2/
- Vérifie que le terme recherché existe dans HAProxy 3.2"""


def list_ollama_models() -> list[str]:
    """Retourne la liste des modèles Ollama disponibles."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
    except Exception:
        return []


def truncate_context(context: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Tronque le contexte si trop long en respectant les séparateurs --- (limites de chunks).
    """
    if len(context) <= max_chars:
        return context

    # Couper aux séparateurs de chunks
    parts = context.split("\n\n---\n\n")
    result = []
    total = 0

    for part in parts:
        if total + len(part) > max_chars:
            # Inclure au moins le premier chunk même s'il dépasse
            if not result:
                result.append(part[:max_chars])
            break
        result.append(part)
        total += len(part)

    truncated = "\n\n---\n\n".join(result)
    if len(truncated) < len(context):
        truncated += f"\n\n[... contexte tronqué à {max_chars} caractères ...]"

    return truncated


def build_messages(
    question: str,
    context: str,
    history: list[tuple[str, str]] | None = None
) -> list[dict]:
    """
    Construit la liste de messages pour l'API Ollama.

    Args:
        question : Question actuelle
        context  : Contexte récupéré par le retriever
        history  : Historique [(question, réponse), ...] des 3 derniers tours max
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Ajouter l'historique de conversation (max 3 tours)
    if history:
        for user_msg, assistant_msg in history[-3:]:
            messages.append({"role": "user",      "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})

    # Message utilisateur avec contexte
    user_content = PROMPT_TEMPLATE.format(
        context  = truncate_context(context),
        question = question
    )
    messages.append({"role": "user", "content": user_content})

    return messages


def generate_response(
    question: str,
    context: str,
    model: str = DEFAULT_MODEL,
    history: list[tuple[str, str]] | None = None,
    temperature: float = 0.1,  # Faible pour rester factuel
) -> Generator[str, None, None]:
    """
    Génère une réponse en streaming.

    Yields:
        Tokens de la réponse au fur et à mesure
    """
    messages = build_messages(question, context, history)

    # DEBUG: Afficher les messages
    import json
    print(f"\n[DEBUG] Messages envoyés à Ollama:")
    for msg in messages:
        content_preview = msg["content"][:100].replace("\n", " ")
        print(f"  - {msg['role']}: {content_preview}...")
    print(f"[DEBUG] Modèle: {model}, Temperature: {temperature}")

    # Détecter si c'est un modèle GGUF (qui nécessite un format différent)
    is_gguf = "GGUF" in model or "gguf" in model.lower()

    # Pour les modèles GGUF, construire un prompt simple au lieu de messages
    if is_gguf:
        # Construire un prompt simple pour les modèles GGUF
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        prompt_parts.append("Assistant:")  # Ajouter le début de la réponse
        prompt = "".join(prompt_parts)

        payload = {
            "model"  : model,
            "prompt" : prompt,
            "stream" : True,
            "options": {
                "temperature"   : temperature,
                "top_p"         : 0.9,
                "repeat_penalty": 1.1,
                "num_predict"   : 1024,
            }
        }
        endpoint = f"{OLLAMA_URL}/api/generate"
    else:
        # Format standard pour les modèles natifs Ollama
        payload = {
            "model"   : model,
            "messages": messages,
            "stream"  : True,
            "options" : {
                "temperature"   : temperature,
                "top_p"         : 0.9,
                "repeat_penalty": 1.1,
                "num_predict"   : 1024,
            }
        }
        endpoint = f"{OLLAMA_URL}/api/chat"

    try:
        with requests.post(
            endpoint,
            json=payload,
            stream=True,
            timeout=LLM_TIMEOUT
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        # Les deux endpoints retournent des formats légèrement différents
                        if is_gguf:
                            token = data.get("response", "")
                        else:
                            token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    except requests.exceptions.ConnectionError:
        yield f"❌ Impossible de se connecter à Ollama sur {OLLAMA_URL}.\nVérifie qu'Ollama tourne : `ollama serve`"
    except requests.exceptions.Timeout:
        yield "⏱️ Timeout — le modèle met trop de temps à répondre. Essaie un modèle plus léger."
    except requests.exceptions.HTTPError as e:
        if "404" in str(e):
            yield f"❌ Modèle '{model}' non trouvé.\nInstalle-le : `ollama pull {model}`"
        else:
            yield f"❌ Erreur Ollama : {e}"
    except Exception as e:
        yield f"❌ Erreur inattendue : {e}"


def generate_response_sync(
    question: str,
    context: str,
    model: str = DEFAULT_MODEL,
    history: list[tuple[str, str]] | None = None,
) -> str:
    """Version synchrone (non-streaming) — utile pour les tests."""
    return "".join(generate_response(question, context, model, history))


# ── Test CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    import sys

    # Test simple sans RAG
    question = sys.argv[1] if len(sys.argv) > 1 else "Comment configurer un backend avec health check HTTP ?"
    context  = """[Source 1: option httpchk — https://docs.haproxy.org/3.2/configuration.html]

option httpchk
    Use HTTP protocol to check server health

    Syntax: option httpchk [<method> <uri> [<version>]]
    
    Example:
    ```haproxy
    backend web_servers
        option httpchk GET /health HTTP/1.1\\r\\nHost:\\ example.com
        server web1 192.168.1.1:80 check
    ```
    """

    print(f"🤖 Question : {question}\n")
    print("📝 Réponse :\n")

    models = list_ollama_models()
    model  = DEFAULT_MODEL if DEFAULT_MODEL in models else (models[0] if models else DEFAULT_MODEL)

    for token in generate_response(question, context, model=model):
        print(token, end='', flush=True)
    print("\n")
