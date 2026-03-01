"""
Gestionnaire ChromaDB pour le système RAG agentic.

Ce module gère l'indexation et la recherche vectorielle dans ChromaDB.
"""

import sys
from pathlib import Path
from typing import Any

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.config import Settings

from config_agentic import CHROMA_CONFIG, CHROMA_DIR


class ChromaManager:
    """
    Gestionnaire ChromaDB.

    Cette classe gère la connexion à ChromaDB, l'indexation
    des chunks et la recherche vectorielle.
    """

    def __init__(
        self,
        persist_directory: Path | None = None,
        collection_name: str | None = None,
    ) -> None:
        """
        Initialise le gestionnaire ChromaDB.

        Args:
            persist_directory: Répertoire de persistance.
            collection_name: Nom de la collection.
        """
        self.persist_directory = persist_directory or CHROMA_DIR
        self.collection_name = collection_name or CHROMA_CONFIG['collection_name']

        # Créer le répertoire s'il n'existe pas
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialiser le client ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        # Récupérer ou créer la collection
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self) -> chromadb.Collection:
        """
        Récupère ou crée la collection ChromaDB.

        Returns:
            Collection ChromaDB.
        """
        try:
            collection = self.client.get_collection(name=self.collection_name)
            return collection
        except Exception:
            # La collection n'existe pas, on la crée
            return self.client.create_collection(
                name=self.collection_name,
                metadata={'description': 'HAProxy Agentic RAG Collection'},
            )

    def add_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        """
        Ajoute des chunks à la collection.

        Args:
            chunks: Liste de chunks à ajouter.
            embeddings: Embeddings pré-calculés (optionnel).
        """
        ids = [chunk['id'] for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        metadatas = [chunk.get('metadata', {}) for chunk in chunks]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recherche des chunks similaires.

        Args:
            query_text: Texte de la requête.
            n_results: Nombre de résultats à retourner.
            where: Filtre sur les métadonnées.

        Returns:
            Liste de chunks avec leurs scores.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )

        # Formater les résultats
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append(
                {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': results['distances'][0][i],
                }
            )

        return formatted_results
    
    def query_with_embedding(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recherche des chunks similaires avec un embedding pré-calculé.
        
        IMPORTANT: Utiliser cette méthode pour la recherche avec des embeddings Ollama.

        Args:
            query_embedding: Embedding de la requête (déjà calculé).
            n_results: Nombre de résultats à retourner.
            where: Filtre sur les métadonnées.

        Returns:
            Liste de chunks avec leurs scores.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        # Formater les résultats
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append(
                {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': results['distances'][0][i],
                }
            )

        return formatted_results

    def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        """
        Récupère un chunk par son identifiant.

        Args:
            chunk_id: Identifiant du chunk.

        Returns:
            Chunk ou None si non trouvé.
        """
        results = self.collection.get(ids=[chunk_id])

        if not results['ids']:
            return None

        return {
            'id': results['ids'][0],
            'content': results['documents'][0],
            'metadata': results['metadatas'][0],
        }

    def delete_by_id(self, chunk_id: str) -> None:
        """
        Supprime un chunk par son identifiant.

        Args:
            chunk_id: Identifiant du chunk.
        """
        self.collection.delete(ids=[chunk_id])

    def clear_collection(self) -> None:
        """
        Vide la collection.
        """
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={'description': 'HAProxy Agentic RAG Collection'},
        )

    def get_collection_stats(self) -> dict[str, Any]:
        """
        Retourne les statistiques de la collection.

        Returns:
            Statistiques de la collection.
        """
        count = self.collection.count()
        return {
            'name': self.collection_name,
            'count': count,
        }

    def max_marginal_relevance_search(
        self,
        query_text: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Recherche avec Maximal Marginal Relevance (MMR).

        Cette méthode effectue une recherche vectorielle en utilisant
        l'algorithme MMR pour maximiser la diversité des résultats.

        Args:
            query_text: Texte de la requête.
            k: Nombre de résultats à retourner.
            fetch_k: Nombre de candidats à récupérer pour la diversification.
            lambda_mult: Facteur de diversité (0.0 = diversité maximale,
                        1.0 = similarité maximale).

        Returns:
            Liste de chunks avec leurs scores MMR.
        """
        # Récupérer plus de candidats que nécessaire
        candidates = self.query(query_text, n_results=fetch_k)

        if not candidates:
            return []

        # Implémentation simplifiée de MMR
        selected: list[dict[str, Any]] = []
        remaining = candidates.copy()

        # Sélectionner le premier résultat (le plus similaire)
        if remaining:
            selected.append(remaining.pop(0))

        # Sélectionner k-1 résultats supplémentaires avec MMR
        while len(selected) < k and remaining:
            best_score = -float('inf')
            best_idx = 0

            for idx, candidate in enumerate(remaining):
                # Score de similarité avec la requête
                similarity_score = 1.0 - candidate['score']

                # Score de similarité maximale avec les résultats déjà sélectionnés
                max_sim_to_selected = 0.0
                for sel in selected:
                    # Utiliser la distance comme métrique de similarité
                    sim = 1.0 - abs(candidate['score'] - sel['score'])
                    if sim > max_sim_to_selected:
                        max_sim_to_selected = sim

                # Score MMR: λ * similarity - (1-λ) * max_sim_to_selected
                mmr_score = (
                    lambda_mult * similarity_score - (1.0 - lambda_mult) * max_sim_to_selected
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            # Ajouter le meilleur candidat
            selected.append(remaining.pop(best_idx))

        return selected

    def create_collection(self) -> None:
        """
        Crée une nouvelle collection ChromaDB.

        Cette méthode supprime la collection existante et en crée une nouvelle.
        """
        self.clear_collection()

    def add_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> None:
        """
        Ajoute des documents à la collection.

        Args:
            documents: Liste de documents à ajouter.
        """
        self.add_chunks(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Effectue une recherche de similarité vectorielle.

        Args:
            query: Texte de la requête.
            k: Nombre de résultats à retourner.

        Returns:
            Liste de chunks avec leurs scores.
        """
        return self.query(query, n_results=k)

    def get_collection(self) -> chromadb.Collection:
        """
        Récupère la collection ChromaDB.

        Returns:
            Collection ChromaDB.
        """
        return self.collection

    def delete_collection(self) -> None:
        """
        Supprime la collection ChromaDB.
        """
        self.clear_collection()


def main() -> None:
    """
    Point d'entrée principal pour tester le gestionnaire.
    """
    manager = ChromaManager()
    stats = manager.get_collection_stats()
    print(f'Collection: {stats}')


if __name__ == '__main__':
    main()
