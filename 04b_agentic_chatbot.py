import sys
import io
import uuid
import gradio as gr
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.agentic_service import AgenticRAGService
from app.utils.logging import setup_logging

logger = setup_logging(__name__, log_file="agentic_chatbot.log")

agentic_service = AgenticRAGService()


async def chat_fn(message, history, thread_id):
    if not thread_id:
        thread_id = str(uuid.uuid4())

    response_text = ""
    # Status indicator
    yield "🔍 Analyse de la question et recherche en cours...", thread_id

    async for chunk in agentic_service.process_message(message, thread_id):
        response_text = chunk  # Overwrite with latest update for simplicity in this UI
        yield response_text, thread_id


def create_demo():
    with gr.Blocks(title="HAProxy Agentic RAG") as demo:
        gr.Markdown("# 🤖 Assistant HAProxy 3.2 - Agentic RAG")
        gr.Markdown(
            "Cette version utilise LangGraph pour un processus de recherche multi-étapes et itératif."
        )

        thread_id_state = gr.State("")

        chatbot = gr.Chatbot(label="Conversation")
        msg = gr.Textbox(label="Votre question sur HAProxy")
        clear = gr.Button("Effacer l'historique")

        async def user_msg(user_message, history):
            return "", history + [{"role": "user", "content": user_message}]

        async def bot_res(history, thread_id):
            if not history:
                yield history, thread_id
                return

            user_message = history[-1]["content"]
            history.append({"role": "assistant", "content": ""})

            async for bot_message, new_thread_id in chat_fn(
                user_message, history[:-1], thread_id
            ):
                history[-1]["content"] = bot_message
                yield history, new_thread_id

        msg.submit(user_msg, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot_res, [chatbot, thread_id_state], [chatbot, thread_id_state]
        )

        clear.click(lambda: ([], ""), None, [chatbot, thread_id_state], queue=False)

    return demo


if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7862)
