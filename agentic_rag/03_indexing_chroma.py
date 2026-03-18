#!/usr/bin/env python3
"""
Script d'indexation ChromaDB avec Gemini Embeddings.

Ce script indexe les chunks enfants dans ChromaDB en utilisant
les embeddings Gemini de Google AI Studio.
"""

import json
import logging
import sys
import time
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurer l'encodage UTF-8 pour stdout
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from agentic_rag.config_agentic import (
    CHROMA_DIR,
    CHUNKS_CHILD_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    GOOGLE_API_KEY,
    INDEX_DIR,
)
from agentic_rag.db.chroma_manager import ChromaManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Configuration pour le batch processing
# Google Gemini API a ses propres limites de rate limit
BATCH_SIZE = 16
MAX_RETRIES = 5


def generate_embeddings_batch(
    embeddings_model: GoogleGenerativeAIEmbeddings,
    texts: list[str],
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """
    Génère les embeddings par batchs avec gestion des erreurs et pauses.
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(texts) + batch_size - 1) // batch_size
        logger.info(f"  Batch {batch_num}/{total_batches}...")

        success = False
        for retry in range(MAX_RETRIES):
            try:
                batch_embeddings = embeddings_model.embed_documents(batch_texts)
                all_embeddings.extend(batch_embeddings)
                success = True
                # Petite pause pour éviter de saturer le rate limit de l'API gratuite
                time.sleep(1)
                break
            except Exception as e:
                wait_time = 2 ** (retry + 1)
                logger.warning(f"Erreur batch {batch_num} (tentative {retry+1}/{MAX_RETRIES}): {e}")
                logger.info(f"Attente de {wait_time}s avant nouvelle tentative...")
                time.sleep(wait_time)

        if not success:
            raise RuntimeError(f"Échec définitif du batch {batch_num} après {MAX_RETRIES} tentatives.")

    return all_embeddings


def main() -> int:
    """Point d'entrée principal."""
    print('=== Phase 3: Indexation ChromaDB (Gemini) ===\n')

    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY non trouvée dans l'environnement.")
        logger.error("Veuillez remplir votre clé dans le fichier .env")
        return 1

    # 1. Charger les chunks
    print('1. Chargement des chunks enfants...')
    try:
        with open(CHUNKS_CHILD_PATH, encoding='utf-8') as f:
            child_chunks = json.load(f)
        print(f'   ✓ {len(child_chunks)} chunks chargés')
    except Exception as e:
        logger.error(f'Erreur chargement chunks: {e}')
        return 1

    if not child_chunks:
        logger.error('Aucun chunk à indexer!')
        return 1

    # 2. Initialiser Gemini Embeddings
    print(f'\n2. Initialisation des embeddings Gemini ({EMBEDDING_MODEL})...')
    try:
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )
        # Test rapide
        test_emb = embeddings_model.embed_query("test")
        print(f'   ✓ Embeddings initialisés (dim: {len(test_emb)})')
    except Exception as e:
        logger.error(f"Erreur initialisation Gemini: {e}")
        return 1

    # 3. Initialiser ChromaDB
    print('\n3. Initialisation de ChromaDB...')
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    try:
        chroma_manager = ChromaManager(
            persist_directory=CHROMA_DIR,
            collection_name=COLLECTION_NAME,
        )
        chroma_manager.clear_collection()
        print(f'   ✓ Collection {COLLECTION_NAME} prête')
    except Exception as e:
        logger.error(f"Erreur ChromaDB: {e}")
        return 1

    # 4. Préparer les docs
    documents = []
    texts_to_embed = []
    for i, chunk in enumerate(child_chunks):
        doc_id = chunk.get('id', f'chunk_{i}')
        content = chunk['content']
        metadata = chunk.get('metadata', {})

        clean_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            elif isinstance(value, list):
                clean_metadata[key] = ', '.join(map(str, value)) if value else ''

        documents.append({'id': doc_id, 'content': content, 'metadata': clean_metadata})
        texts_to_embed.append(content)

    # 5. Générer embeddings
    print('\n4. Génération des embeddings (Gemini)...')
    start_time = time.time()
    try:
        all_embeddings = generate_embeddings_batch(embeddings_model, texts_to_embed)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        return 1
    elapsed = time.time() - start_time
    print(f'   ✓ {len(all_embeddings)} embeddings générés en {elapsed:.1f}s')

    # 6. Indexer
    print('\n5. Indexation dans ChromaDB...')
    try:
        chroma_manager.add_chunks(documents, embeddings=all_embeddings)
        print('   ✓ Documents indexés')
    except Exception as e:
        logger.error(f"Erreur indexation: {e}")
        return 1

    # 7. BM25
    print('\n6. Sauvegarde de l\'index BM25...')
    try:
        import pickle

        from rank_bm25 import BM25Okapi
        corpus = [c['content'].lower().split() for c in child_chunks]
        bm25_index = BM25Okapi(corpus)
        bm25_path = INDEX_DIR / 'bm25_index_gemini.pkl'
        with open(bm25_path, 'wb') as f:
            pickle.dump(bm25_index, f)
        print(f'   ✓ BM25 sauvegardé: {bm25_path}')
    except Exception as e:
        logger.warning(f"Erreur BM25: {e}")

    print('\n' + '=' * 60)
    print('✓ Indexation Gemini terminée!')
    print('=' * 60)
    return 0

if __name__ == '__main__':
    sys.exit(main())
