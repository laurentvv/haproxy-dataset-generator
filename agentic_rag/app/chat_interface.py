"""Interface de chat Gradio pour le système RAG agentic."""

import json
from datetime import datetime

import gradio as gr

from .rag_system import AgenticRAGSystem


class ChatInterface:
    """Interface de chat Gradio."""

    # Exemples de questions pour aider les utilisateurs à démarrer
    examples = [
        "Comment configurer un backend HTTP dans HAProxy 3.2 ?",
        "Quelles sont les nouvelles fonctionnalités de HAProxy 3.2 ?",
        "Comment utiliser le stick-table pour la persistance ?",
        "Comment configurer le load balancing avec round-robin ?",
        "Qu'est-ce que le multiplexer dans HAProxy 3.2 ?",
    ]

    def __init__(self) -> None:
        """Initialise l'interface de chat."""
        self.rag_system = AgenticRAGSystem()
        self.current_session_id = self.rag_system.create_session()

    def respond(
        self,
        message: str,
        history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]], str, str]:
        """Répond à un message de l'utilisateur avec streaming.

        Args:
            message: Message de l'utilisateur
            history: Historique de conversation (liste de dict avec 'role' et 'content')

        Yields:
            Tuple (message vide, historique mis à jour, texte des sources, statut) pour chaque chunk
        """
        if not message.strip():
            yield '', history, '**Sources utilisées:**\n\nAucune source pour le moment.', 'Prêt'
            return
        
        try:
            # Ajouter le message utilisateur à l'historique
            history.append({'role': 'user', 'content': message})
            
            # Initialiser le texte des sources
            sources_text = '**Sources utilisées:**\n\n'
            
            # Construire la réponse avec streaming
            response = ''
            for chunk in self.rag_system.query(self.current_session_id, message):
                response += chunk
                history[-1] = {'role': 'assistant', 'content': response}
                yield '', history, sources_text + 'Chargement...', f'Génération en cours... ({len(response)} caractères)'
            
            # Récupérer les sources
            try:
                sources = self.rag_system.get_sources(self.current_session_id)
                if sources:
                    for i, source in enumerate(sources, 1):
                        title = source.get('title', 'N/A')
                        content = source.get('content', '')[:100]
                        sources_text += f'### {i}. {title}\n\n{content}...\n\n'
                else:
                    sources_text += '\n\n*Sources récupérées depuis la documentation HAProxy 3.2*'
            except Exception:
                sources_text += '\n\n*Sources récupérées depuis la documentation HAProxy 3.2*'
            
            yield '', history, sources_text, 'Réponse terminée'
        
        except Exception as e:
            error_message = f"**Erreur:** {str(e)}\n\nVeuillez réessayer ou reformuler votre question."
            history.append({'role': 'assistant', 'content': error_message})
            yield '', history, '**Sources utilisées:**\n\nErreur lors de la récupération des sources.', f'Erreur: {str(e)}'

    def clear_chat(self) -> tuple[str, list[dict[str, str]], str, str]:
        """Efface la conversation.

        Returns:
            Tuple (message vide, historique vide, texte des sources par défaut, statut)
        """
        self.current_session_id = self.rag_system.create_session()
        return '', [], '**Sources utilisées:**\n\nAucune source pour le moment.', 'Prêt'

    def save_chat(self, history: list[dict[str, str]]) -> str:
        """Sauvegarde la conversation dans un fichier JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_history_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return f"Conversation sauvegardée dans {filename}"

    def load_chat(self, file_data) -> tuple[list[dict[str, str]], str, str, str]:
        """Charge une conversation depuis un fichier JSON."""
        try:
            history = json.loads(file_data)
            return history, '**Sources utilisées:**\n\nAucune source pour le moment.', 'Prêt', "Conversation chargée avec succès"
        except Exception as e:
            return [], '**Sources utilisées:**\n\nAucune source pour le moment.', 'Prêt', f"Erreur lors du chargement: {str(e)}"

    def create_ui(self) -> gr.Blocks:
        """Crée l'interface utilisateur Gradio.

        Returns:
            Interface Gradio
        """
        with gr.Blocks(
            title='HAProxy 3.2 Agentic RAG',
        ) as demo:
            gr.Markdown(
                """
                # 🤖 HAProxy 3.2 Agentic RAG
                
                Assistant intelligent basé sur la documentation officielle HAProxy 3.2.
                """
            )

            chatbot = gr.Chatbot(
                label='Conversation',
                height=500,
            )

            sources_display = gr.Markdown(
                label='Sources utilisées',
                value='**Sources utilisées:**\n\nAucune source pour le moment.',
            )

            status_text = gr.Textbox(
                label='Statut',
                value='Prêt',
                interactive=False,
                visible=False,
            )

            with gr.Row():
                msg = gr.Textbox(
                    label='Votre question',
                    placeholder='Posez une question sur HAProxy 3.2...',
                    scale=4,
                    submit_btn=True,
                )

            with gr.Row():
                clear_btn = gr.Button('Nouvelle conversation', variant='secondary')
                save_btn = gr.Button('💾 Sauvegarder', variant='secondary')
                load_btn = gr.UploadButton(
                    label='📂 Charger',
                    file_types=['.json'],
                )

            # Ajouter les exemples
            gr.Examples(
                examples=self.examples,
                inputs=msg,
                label='Exemples de questions:',
            )

            # Event listeners
            msg.submit(
                fn=self.respond,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot, sources_display, status_text],
            )

            clear_btn.click(
                fn=self.clear_chat,
                outputs=[msg, chatbot, sources_display, status_text],
            )

            save_btn.click(
                fn=self.save_chat,
                inputs=[chatbot],
                outputs=[gr.Textbox(visible=False)],
            )

            load_btn.upload(
                fn=self.load_chat,
                inputs=[load_btn],
                outputs=[chatbot, sources_display, status_text, gr.Textbox(visible=False)],
            )

            gr.Markdown(
                """
                ---
                **Note:** Ce système utilise un agent RAG agentic avec LangGraph pour fournir
                des réponses contextuelles basées sur la documentation HAProxy 3.2.
                """
            )

        return demo
