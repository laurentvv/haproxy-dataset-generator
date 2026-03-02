#!/usr/bin/env python3
"""
Script d'indexation ChromaDB avec embeddings Ollama.

Ce script indexe les chunks enfants dans ChromaDB en utilisant
les embeddings générés par Ollama (qwen3-embedding:8b).

IMPORTANT: Les embeddings DOIVENT être générés explicitement pour que
la recherche vectorielle fonctionne correctement.
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

from langchain_ollama import OllamaEmbeddings

from agentic_rag.config_agentic import (
    CHROMA_DIR,
    CHUNKS_CHILD_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
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
BATCH_SIZE = 32  # Nombre de chunks à embedder en une fois
MAX_RETRIES = 3  # Nombre de tentatives en cas d'erreur Ollama


def generate_embeddings_batch(
    embeddings_model: OllamaEmbeddings,
    texts: list[str],
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """
    Génère les embeddings pour une liste de textes par batchs.
    
    Args:
        embeddings_model: Modèle d'embedding Ollama
        texts: Liste des textes à embedder
        batch_size: Taille des batchs
    
    Returns:
        Liste des embeddings
    
    Raises:
        RuntimeError: Si l'embedding échoue après MAX_RETRIES tentatives
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(texts) + batch_size - 1) // batch_size
        logger.debug(f"  Batch {batch_num}/{total_batches}")
        
        try:
            batch_embeddings = embeddings_model.embed_documents(batch_texts)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.warning(f"Erreur batch {batch_num}: {e}")
            # Tenter de retry avec des pauses exponentielles
            for retry in range(MAX_RETRIES):
                time.sleep(2 ** retry)  # Pause exponentielle: 1s, 2s, 4s
                try:
                    batch_embeddings = embeddings_model.embed_documents(batch_texts)
                    all_embeddings.extend(batch_embeddings)
                    logger.info(f"  Batch {batch_num} réussi après {retry + 1} tentative(s)")
                    break
                except Exception as retry_error:
                    if retry == MAX_RETRIES - 1:
                        # Échec définitif - logger les détails et lever une exception
                        logger.error(f"Échec batch {batch_num} après {MAX_RETRIES} tentatives")
                        logger.error(f"Erreur finale: {retry_error}")
                        logger.error(f"Nombre de textes dans le batch: {len(batch_texts)}")
                        logger.error(f"Position dans la liste: {i}/{len(texts)}")
                        # Afficher un échantillon des textes pour investigation
                        sample_size = min(2, len(batch_texts))
                        logger.error(f"Échantillon des textes concernés:")
                        for j in range(sample_size):
                            text_preview = batch_texts[j][:100] + "..." if len(batch_texts[j]) > 100 else batch_texts[j]
                            logger.error(f"  [{j}] {text_preview}")
                        
                        raise RuntimeError(
                            f"Impossible de générer les embeddings pour le batch {batch_num} "
                            f"après {MAX_RETRIES} tentatives. "
                            f"Erreur: {retry_error}"
                        ) from retry_error
                    else:
                        logger.debug(f"  Tentative {retry + 1}/{MAX_RETRIES} échouée: {retry_error}")
                        continue
    
    return all_embeddings


def main() -> int:
    """
    Point d'entrée principal.
    
    Returns:
        Code de retour (0 pour succès, 1 pour erreur).
    """
    print('=== Phase 3: Indexation ChromaDB ===\n')

    # ─────────────────────────────────────────────────────────────
    # 1. Charger les chunks enfants
    # ─────────────────────────────────────────────────────────────
    print('1. Chargement des chunks enfants...')
    try:
        with open(CHUNKS_CHILD_PATH, encoding='utf-8') as f:
            child_chunks = json.load(f)
        print(f'   ✓ {len(child_chunks)} chunks chargés')
    except FileNotFoundError:
        logger.error(f'Fichier non trouvé: {CHUNKS_CHILD_PATH}')
        logger.error("Veuillez d'abord exécuter 02_chunking_parent_child.py")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f'Erreur de décodage JSON: {e}')
        return 1
    
    if not child_chunks:
        logger.error('Aucun chunk à indexer!')
        return 1

    # ─────────────────────────────────────────────────────────────
    # 2. Initialiser les embeddings Ollama
    # ─────────────────────────────────────────────────────────────
    print(f'\n2. Initialisation des embeddings ({EMBEDDING_MODEL})...')
    print('   ⏳ Connexion à Ollama...')
    
    try:
        embeddings_model = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url='http://localhost:11434')
        
        # Tester l'initialisation avec un petit embedding
        test_embedding = embeddings_model.embed_query('test')
        print(f'   ✓ Embeddings initialisés (dimension: {len(test_embedding)})')
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des embeddings: {e}")
        logger.error("Veuillez vous assurer qu'Ollama est en cours d'exécution:")
        logger.error("  ollama serve")
        logger.error(f"Et que le modèle est disponible:")
        logger.error(f"  ollama pull {EMBEDDING_MODEL}")
        return 1

    # ─────────────────────────────────────────────────────────────
    # 3. Créer le répertoire d'index et initialiser ChromaDB
    # ─────────────────────────────────────────────────────────────
    print('\n3. Initialisation de ChromaDB...')
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        chroma_manager = ChromaManager(
            persist_directory=CHROMA_DIR,
            collection_name=COLLECTION_NAME,
        )
        print('   ✓ ChromaDB initialisé')
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de ChromaDB: {e}")
        return 1

    # ─────────────────────────────────────────────────────────────
    # 4. Nettoyer et recréer la collection (IMPORTANT: reset complet)
    # ─────────────────────────────────────────────────────────────
    print('\n4. Nettoyage de la collection existante...')
    try:
        # Utiliser clear_collection qui delete + recrée
        chroma_manager.clear_collection()
        print('   ✓ Collection recréée à neuf')
    except Exception as e:
        logger.error(f'Erreur lors de la recréation de la collection: {e}')
        # Si la collection n'existe pas, la créer directement
        try:
            chroma_manager.collection = chroma_manager.client.create_collection(
                name=COLLECTION_NAME,
                metadata={'description': 'HAProxy Agentic RAG Collection'},
            )
            print('   ✓ Collection créée')
        except Exception as create_error:
            logger.error(f'Erreur lors de la création: {create_error}')
            return 1

    # ─────────────────────────────────────────────────────────────
    # 5. Préparer les documents pour ChromaDB
    # ─────────────────────────────────────────────────────────────
    print('\n5. Préparation des documents ChromaDB...')
    
    documents: list[dict[str, object]] = []
    texts_to_embed: list[str] = []
    
    for i, chunk in enumerate(child_chunks):
        doc_id = chunk.get('id', f'chunk_{i}')
        content = chunk['content']
        metadata = chunk.get('metadata', {})
        
        # Nettoyer les métadonnées pour ChromaDB (doivent être sérialisables)
        clean_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            elif isinstance(value, list):
                # Convertir les listes en strings si nécessaire
                clean_metadata[key] = ', '.join(map(str, value)) if value else ''
        
        documents.append({
            'id': doc_id,
            'content': content,
            'metadata': clean_metadata,
        })
        texts_to_embed.append(content)
    
    print(f'   ✓ {len(documents)} documents préparés')

    # ─────────────────────────────────────────────────────────────
    # 6. Générer les embeddings (ÉTAPE CRITIQUE)
    # ─────────────────────────────────────────────────────────────
    print('\n6. Génération des embeddings avec Ollama...')
    print(f'   📊 {len(texts_to_embed)} chunks à embedder')
    print(f'   📦 Batch size: {BATCH_SIZE}')
    print(f'   ⏱️  Temps estimé: ~{len(texts_to_embed) * 0.5:.0f}s')
    
    start_time = time.time()
    try:
        all_embeddings = generate_embeddings_batch(embeddings_model, texts_to_embed, BATCH_SIZE)
    except RuntimeError as e:
        logger.error(f"Erreur critique lors de la génération des embeddings: {e}")
        logger.error("L'indexation a été arrêtée pour éviter de corrompre la base de données.")
        logger.error("Vérifiez que:")
        logger.error("  1. Ollama est en cours d'exécution (ollama serve)")
        logger.error(f"  2. Le modèle {EMBEDDING_MODEL} est disponible (ollama pull {EMBEDDING_MODEL})")
        logger.error("  3. Vous avez suffisamment de mémoire disponible")
        logger.error("  4. Le serveur Ollama est accessible (http://localhost:11434)")
        return 1
    elapsed = time.time() - start_time
    
    print(f'   ✓ {len(all_embeddings)} embeddings générés en {elapsed:.1f}s')
    print(f'   ⚡ Vitesse: {len(texts_to_embed) / elapsed:.1f} chunks/s')
    
    # Vérifier que les embeddings sont valides
    if not all_embeddings or len(all_embeddings) != len(texts_to_embed):
        logger.error(f"Nombre d'embeddings incorrect: {len(all_embeddings)} vs {len(texts_to_embed)}")
        return 1
    
    # Vérifier la dimension des embeddings
    embedding_dim = len(all_embeddings[0])
    print(f'   ✓ Dimension des embeddings: {embedding_dim}')
    
    # Vérifier que les embeddings ne contiennent pas de valeurs nulles
    null_count = sum(1 for emb in all_embeddings if all(v == 0.0 for v in emb))
    if null_count > 0:
        logger.warning(f"⚠️  {null_count} embeddings contiennent uniquement des zéros")
        logger.warning("   Cela peut indiquer un problème avec le modèle d'embedding")

    # ─────────────────────────────────────────────────────────────
    # 7. Ajouter les documents avec embeddings à ChromaDB
    # ─────────────────────────────────────────────────────────────
    print('\n7. Indexation des documents dans ChromaDB...')
    
    try:
        chroma_manager.add_chunks(documents, embeddings=all_embeddings)
        print('   ✓ Documents indexés avec embeddings')
    except Exception as e:
        logger.error(f"Erreur lors de l'indexation: {e}")
        return 1

    # ─────────────────────────────────────────────────────────────
    # 8. Vérifier l'indexation
    # ─────────────────────────────────────────────────────────────
    print("\n8. Vérification de l'indexation...")
    try:
        collection = chroma_manager.get_collection()
        count = collection.count()
        print(f'   ✓ {count} documents dans la collection')

        if count != len(documents):
            logger.warning(f'{len(documents) - count} documents manquants')
            return 1
    except Exception as e:
        logger.error(f'Erreur lors de la vérification: {e}')
        return 1

    # ─────────────────────────────────────────────────────────────
    # 9. Test de recherche vectorielle (avec embeddings Ollama!)
    # ─────────────────────────────────────────────────────────────
    print('\n9. Test de recherche vectorielle...')
    
    test_queries = [
        'HAProxy configuration backend',
        'health check HTTP',
        'SSL termination',
    ]
    
    try:
        for query in test_queries:
            # IMPORTANT: Utiliser le MÊME modèle d'embedding pour la recherche
            query_embedding = embeddings_model.embed_query(query)
            
            # Rechercher avec l'embedding (pas avec le texte brut!)
            results = chroma_manager.query_with_embedding(query_embedding, n_results=3)
            if results:
                print(f'   ✓ "{query}" → {len(results)} résultats')
                # Afficher le premier résultat pour validation
                if results:
                    first_result = results[0]
                    content_preview = first_result.get('content', '')[:100]
                    score = first_result.get('score', 'N/A')
                    print(f'      1er résultat (score: {score:.4f}): {content_preview}...')
            else:
                print(f'   ⚠️  "{query}" → 0 résultat (problème!)')
    except Exception as e:
        logger.error(f'Erreur lors du test de recherche: {e}')
        return 1

    # ─────────────────────────────────────────────────────────────
    # Résumé final
    # ─────────────────────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('✓ Phase 3 terminée avec succès!')
    print('=' * 60)
    print(f'\n📊 Résumé:')
    print(f'   - Documents indexés: {count}')
    print(f'   - Embeddings générés: {len(all_embeddings)}')
    print(f'   - Modèle: {EMBEDDING_MODEL}')
    print(f'   - Dimension: {embedding_dim}')
    print(f'   - Collection: {COLLECTION_NAME}')
    print(f'   - Chemin: {CHROMA_DIR}')
    print(f'   - Temps total: {elapsed:.1f}s')
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
