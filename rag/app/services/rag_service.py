"""RAG service for HAProxy Chatbot."""

import asyncio

from app.utils.logging import setup_logging

logger = setup_logging(__name__)


class RAGService:
    """Service RAG encapsulant le retriever V3.

    Responsabilités:
    - Chargement des index
    - Retrieval hybride
    - Gestion des erreurs
    """

    def __init__(self):
        """Initialise le service RAG."""
        self._indexes_loaded = False
        self._load_lock = asyncio.Lock()

    async def retrieve(
        self, query: str, top_k: int = 5
    ) -> tuple[str, list[dict], bool]:
        """Effectue le retrieval RAG.

        Args:
            query: Requête utilisateur
            top_k: Nombre de résultats à retourner

        Returns:
            Tuple (context_str, sources, low_confidence)
        """
        # Charger les index si nécessaire
        await self._ensure_indexes()

        # Lazy loading du module retriever_v3 pour éviter de charger les index
        # au démarrage de l'application. Cela permet un démarrage plus rapide
        # et une meilleure gestion de la mémoire. Le module n'est chargé que
        # lors de la première requête de retrieval.
        from retriever_v3 import retrieve_context_string

        # Exécuter le retrieval dans un thread séparé
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: retrieve_context_string(query, top_k=top_k)
        )

        return result

    async def _ensure_indexes(self) -> None:
        """Charge les index une seule fois de manière thread-safe."""
        async with self._load_lock:
            if self._indexes_loaded:
                return

            try:
                # Lazy loading du module retriever_v3 pour éviter de charger
                # les index au démarrage de l'application.
                from retriever_v3 import _load_indexes

                _load_indexes()
                self._indexes_loaded = True
                logger.info("✅ Indexes loaded successfully")
            except Exception as e:
                logger.error("❌ Failed to load indexes: %s", e)
                raise
