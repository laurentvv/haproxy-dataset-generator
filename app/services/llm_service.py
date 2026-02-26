"""LLM service for HAProxy Chatbot."""

import asyncio
from typing import AsyncGenerator

from app.utils.logging import setup_logging

logger = setup_logging(__name__)


class LLMService:
    """Service LLM encapsulant la génération via Ollama.

    Responsabilités:
    - Génération de réponses
    - Streaming
    - Gestion des erreurs
    """

    FALLBACK_RESPONSE = """⚠️ Je n'ai pas trouvé d'information suffisamment précise dans la documentation HAProxy pour répondre à cette question.

Suggestions :
- Reformule ta question en utilisant des termes techniques HAProxy précis (ex: "option httpchk", "backend", "ACL")
- Consulte directement la documentation : https://docs.haproxy.org/3.2/
- Vérifie que le terme recherché existe dans HAProxy 3.2"""

    async def generate(
        self,
        question: str,
        context: str,
        model: str = "gemma3:latest",
        history: list[tuple[str, str]] | None = None,
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        """Génère une réponse avec streaming.

        Args:
            question: Question utilisateur
            context: Contexte RAG
            model: Modèle LLM
            history: Historique de conversation
            temperature: Température de génération

        Yields:
            Tokens de la réponse
        """
        from llm import generate_response

        # Exécuter la génération dans un thread séparé
        loop = asyncio.get_event_loop()

        for token in await loop.run_in_executor(
            None,
            lambda: generate_response(
                question=question,
                context=context,
                model=model,
                history=history,
                temperature=temperature,
            ),
        ):
            yield token

    def get_fallback_response(self) -> str:
        """Retourne la réponse par défaut.

        Returns:
            Message de fallback
        """
        return self.FALLBACK_RESPONSE

    def list_models(self) -> list[str]:
        """Retourne la liste des modèles LLM disponibles.

        Returns:
            Liste des noms de modèles disponibles
        """
        from llm import list_ollama_models

        return list_ollama_models()
