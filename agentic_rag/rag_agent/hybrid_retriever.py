"""
Hybrid Retriever pour Agentic RAG - Vector + BM25 + RRF

Inspiré du RAG V3 standard, adapté pour l'architecture agentic.
"""

import logging
import pickle
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Retrieval hybride combinant :
    1. Vector search (ChromaDB) - sémantique
    2. BM25 (lexical) - mots-clés exacts
    3. RRF (Reciprocal Rank Fusion) - fusion des résultats
    """

    def __init__(self, chroma_manager, chunks: list[dict], bm25_index_path: str | None = None):
        """
        Initialise le retriever hybride.

        Args:
            chroma_manager: Instance de ChromaManager pour le vector search
            chunks: Liste des chunks (pour construire l'index BM25)
            bm25_index_path: Chemin vers l'index BM25 sauvegardé (optionnel)
        """
        self.chroma_manager = chroma_manager
        self.chunks = chunks

        # Charger ou construire l'index BM25
        if bm25_index_path and Path(bm25_index_path).exists():
            logger.info(f'Chargement index BM25 depuis {bm25_index_path}...')
            self.bm25_index = self._load_bm25_index(bm25_index_path)
            logger.info('✅ Index BM25 chargé')
        else:
            logger.info(f'Construction index BM25 avec {len(chunks)} chunks...')
            self.bm25_index = self._build_bm25_index(chunks)
            logger.info('✅ Index BM25 construit')

    def _load_bm25_index(self, path: str) -> BM25Okapi:
        """Charge l'index BM25 depuis un fichier pickle."""
        with open(path, 'rb') as f:
            return pickle.load(f)

    def _build_bm25_index(self, chunks: list[dict]) -> BM25Okapi:
        """Construit l'index BM25 à partir des chunks."""
        # Tokenizer simple : split par espaces + lowercase
        def tokenize(text: str) -> list[str]:
            return text.lower().split()

        corpus = []
        for chunk in chunks:
            content = chunk.get('content', '')
            # Ajouter metadata pour meilleur matching
            metadata = chunk.get('metadata', {})
            section_path = ' '.join(metadata.get('section_path', []))
            full_text = f"{content} {section_path}"
            corpus.append(tokenize(full_text))

        return BM25Okapi(corpus)

    def vector_search(self, query_embedding: list[float], k: int = 10) -> list[dict]:
        """Recherche vectorielle pure (ChromaDB)."""
        results = self.chroma_manager.query_with_embedding(
            query_embedding=query_embedding,
            n_results=k
        )
        return results

    def bm25_search(self, query: str, k: int = 10) -> list[dict]:
        """Recherche lexicale pure (BM25)."""
        scores = self.bm25_index.get_scores(query.lower().split())

        # Trier par score décroissant
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        # Retourner top k chunks avec score (gérer si k > len(chunks))
        results = []
        actual_k = min(k, len(indexed_scores))
        for idx, score in indexed_scores[:actual_k]:
            chunk = self.chunks[idx].copy()
            chunk['score'] = float(score)
            results.append(chunk)

        return results

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        k: int = 10,
        rrf_k: int = 60
    ) -> list[dict]:
        """
        Recherche hybride Vector + BM25 avec fusion RRF.

        Args:
            query: Requête texte (pour BM25)
            query_embedding: Embedding de la requête (pour vector)
            k: Nombre de résultats finaux
            rrf_k: Paramètre RRF (k=60 donne plus de poids au rang)

        Returns:
            Liste des k meilleurs chunks triés par score RRF
        """
        # 1. Vector search (top 50 pour avoir du choix)
        vector_results = self.vector_search(query_embedding, k=50)
        print(f"DEBUG hybrid_search: vector_results={len(vector_results)}", flush=True)

        # 2. BM25 search (top 50)
        bm25_results = self.bm25_search(query, k=50)
        print(f"DEBUG hybrid_search: bm25_results={len(bm25_results)}", flush=True)

        # 3. RRF Fusion
        rrf_scores = self._rrf_fusion(
            vector_results,
            bm25_results,
            k=rrf_k
        )
        print(f"DEBUG hybrid_search: rrf_scores={len(rrf_scores)}", flush=True)

        # 4. Trier par score RRF et retourner top k
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        # Reconstruire les résultats avec score RRF
        final_results = []
        for chunk_id, rrf_score in sorted_results:
            # Trouver le chunk original dans les résultats
            chunk = None
            for r in vector_results + bm25_results:
                if self._get_chunk_id(r) == chunk_id:
                    chunk = r.copy()
                    break
            
            if chunk:
                chunk['rrf_score'] = rrf_score
                final_results.append(chunk)

        print(f"DEBUG hybrid_search: final_results={len(final_results)}", flush=True)
        return final_results

    def _rrf_fusion(
        self,
        vector_results: list[dict],
        bm25_results: list[dict],
        k: int = 60
    ) -> dict[int, float]:
        """
        Fusion RRF (Reciprocal Rank Fusion) de deux listes de résultats.

        RRF Score = Σ 1 / (k + rank)

        Args:
            vector_results: Résultats du vector search
            bm25_results: Résultats du BM25 search
            k: Paramètre RRF (typiquement 60)

        Returns:
            Dict {chunk_id: rrf_score}
        """
        rrf_scores: dict[int, float] = {}

        # Score vector (rank-based)
        for rank, result in enumerate(vector_results):
            chunk_id = self._get_chunk_id(result)
            if chunk_id is not None:
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)

        # Score BM25 (rank-based)
        for rank, result in enumerate(bm25_results):
            chunk_id = self._get_chunk_id(result)
            if chunk_id is not None:
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)

        return rrf_scores

    def _get_chunk_id(self, result: dict) -> int | None:
        """Extrait l'ID du chunk depuis un résultat."""
        # Méthode 1: Depuis metadata (id ou parent_id)
        metadata = result.get('metadata', {})
        
        # Essayer d'abord 'id' direct
        if 'id' in metadata:
            try:
                chunk_id = int(metadata['id'])
                return chunk_id if chunk_id >= 0 else None
            except (ValueError, TypeError):
                pass
        
        # Essayer 'parent_id' avec index
        parent_id = metadata.get('parent_id', '')
        if parent_id:
            # Extraire les chiffres du parent_id (ex: "parent_123" → 123)
            import re
            match = re.search(r'(\d+)', parent_id)
            if match:
                return int(match.group(1))
        
        # Fallback: utiliser hash du content (stable)
        content = result.get('content', '')
        if content:
            return abs(hash(content)) % 1000000
        
        return None
