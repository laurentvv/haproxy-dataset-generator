#!/usr/bin/env python3
"""
Script de chunking hiérarchique parent/child.

Ce script implémente la stratégie parent/child pour le RAG :
- Parent : Document complet (4000 chars max) pour le contexte
- Child : Chunk plus petit (500 chars) pour la recherche vectorielle

Chaque child référence son parent pour permettre la récupération du contexte complet.
"""

import json
import logging
import sys
import uuid
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurer l'encodage UTF-8 pour stdout
if sys.platform == 'win32':
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from langchain_text_splitters import RecursiveCharacterTextSplitter

from agentic_rag.config_agentic import (
    CHILD_CHUNK_OVERLAP,
    CHILD_CHUNK_SIZE,
    CHUNKS_CHILD_PATH,
    MAX_PARENT_SIZE,
    MIN_PARENT_SIZE,
    PARENT_STORE_DIR,
    SCRAPED_PAGES_PATH,
)
from agentic_rag.db.parent_store_manager import ParentStoreManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Seuils de qualité
MIN_CHILD_SIZE = 50  # Un child trop court est ignoré
MAX_CHILDREN_PER_PARENT = 20  # Limite pour éviter les parents trop gros


def main() -> int:
    """
    Point d'entrée principal.
    
    Returns:
        Code de retour (0 pour succès, 1 pour erreur).
    """
    print('=== Phase 2: Chunking Parent/Child ===\n')

    # Charger les données scrapées
    print('1. Chargement des données scrapées...')
    try:
        with open(SCRAPED_PAGES_PATH, encoding='utf-8') as f:
            scraped_pages = json.load(f)
        print(f'   ✓ {len(scraped_pages)} pages chargées')
    except FileNotFoundError:
        logger.error(f'Fichier non trouvé: {SCRAPED_PAGES_PATH}')
        logger.error("Veuillez d'abord exécuter 01_scrape_verified.py")
        return 1
    except json.JSONDecodeError as e:
        logger.error(f'Erreur de décodage JSON: {e}')
        return 1

    # Filtrer les pages avec contenu valide
    valid_pages = [p for p in scraped_pages if len(p.get('content', '')) >= MIN_PARENT_SIZE]
    if len(valid_pages) < len(scraped_pages):
        print(f'   ⚠️  {len(scraped_pages) - len(valid_pages)} pages ignorées (contenu trop court)')
    
    if not valid_pages:
        logger.error('Aucune page valide à chunker!')
        return 1
    
    print(f'   ✓ {len(valid_pages)} pages valides pour chunking')

    # Initialiser les gestionnaires
    print('\n2. Initialisation...')
    PARENT_STORE_DIR.mkdir(parents=True, exist_ok=True)
    parent_manager = ParentStoreManager(PARENT_STORE_DIR)
    
    # Nettoyer l'ancien store
    parent_manager.clear_store()
    print('   ✓ Parent store nettoyé')
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_SIZE,
        chunk_overlap=CHILD_CHUNK_OVERLAP,
        length_function=len,
        separators=['\n\n', '\n', '. ', ' ', ''],
    )
    print(f'   ✓ Text splitter configuré (chunk_size={CHILD_CHUNK_SIZE}, overlap={CHILD_CHUNK_OVERLAP})')

    # Traiter chaque page
    print('\n3. Chunking hiérarchique...')
    child_chunks: list[dict[str, object]] = []
    parent_count = 0
    skipped_pages = 0
    total_children = 0

    for i, page in enumerate(valid_pages, 1):
        if i % 20 == 0:
            print(f'   Progress: {i}/{len(valid_pages)} pages traitées')
        
        # Créer un ID unique pour le parent
        url = page.get('url', '')
        title = page.get('title', '')
        anchor = page.get('anchor', '')
        
        # Générer un parent_id unique et lisible
        parent_id = f'parent_{uuid.uuid4().hex[:12]}'
        
        # Nettoyer le contenu
        content = page.get('content', '')
        content = content.strip()
        
        # Vérifier la taille du parent
        parent_size = len(content)
        if parent_size < MIN_PARENT_SIZE:
            logger.debug(f'  ⚠️  Parent ignoré (trop court: {parent_size} chars): {title}')
            skipped_pages += 1
            continue
        
        if parent_size > MAX_PARENT_SIZE:
            logger.debug(f'  ⚠️  Parent ignoré (trop long: {parent_size} chars): {title}')
            skipped_pages += 1
            continue

        # Créer les métadonnées parent
        parent_metadata = {
            'parent_id': parent_id,
            'source': url,
            'section_path': page.get('section_path', []),
            'depth': page.get('depth', 0),
            'title': title,
            'anchor': anchor,
            'content_length': parent_size,
        }

        # Sauvegarder le parent
        parent_data = {
            'id': parent_id,
            'page_content': content,
            'metadata': parent_metadata,
        }
        
        try:
            parent_manager.save_parent(parent_id, parent_data)
            parent_count += 1
        except Exception as e:
            logger.error(f'Erreur lors de la sauvegarde du parent {parent_id}: {e}')
            skipped_pages += 1
            continue

        # Créer les chunks enfants
        try:
            child_docs = text_splitter.create_documents(
                texts=[content],
                metadatas=[parent_metadata],
            )

            # Filtrer les enfants trop courts
            valid_children = []
            for child in child_docs:
                if len(child.page_content) >= MIN_CHILD_SIZE:
                    # Ajouter child_id et parent_id explicite
                    child_id = f'child_{uuid.uuid4().hex[:12]}'
                    child.metadata['child_id'] = child_id
                    child.metadata['parent_id'] = parent_id
                    valid_children.append(child)
            
            # Limiter le nombre d'enfants par parent
            if len(valid_children) > MAX_CHILDREN_PER_PARENT:
                logger.debug(f'  ⚠️  Trop d\'enfants ({len(valid_children)}) pour {title}, limite à {MAX_CHILDREN_PER_PARENT}')
                valid_children = valid_children[:MAX_CHILDREN_PER_PARENT]
            
            for child in valid_children:
                child_chunks.append(
                    {
                        'id': child.metadata.get('child_id', f'child_{uuid.uuid4().hex[:12]}'),
                        'content': child.page_content,
                        'metadata': child.metadata,
                    }
                )
            
            total_children += len(valid_children)
            
        except Exception as e:
            logger.error(f'Erreur lors du chunking pour {title}: {e}')
            continue

    print(f'\n   ✓ {parent_count} parents créés')
    print(f'   ✓ {total_children} enfants créés')
    if skipped_pages > 0:
        print(f'   ⚠️  {skipped_pages} pages ignorées')

    # Sauvegarder les chunks enfants
    print('\n4. Sauvegarde des chunks enfants...')
    try:
        with open(CHUNKS_CHILD_PATH, 'w', encoding='utf-8') as f:
            json.dump(child_chunks, f, ensure_ascii=False, indent=2)
        print(f'   ✓ Chunks sauvegardés dans {CHUNKS_CHILD_PATH}')
    except Exception as e:
        logger.error(f'Erreur lors de la sauvegarde des chunks: {e}')
        return 1

    # Statistiques détaillées
    print('\n=== Statistiques ===')
    if parent_count > 0 and child_chunks:
        all_parents = parent_manager.load_all_parents()
        parent_sizes = [len(p['page_content']) for p in all_parents.values()]
        child_sizes = [len(c['content']) for c in child_chunks]
        
        avg_children_per_parent = total_children / parent_count if parent_count > 0 else 0
        
        print(f'   Parents:')
        print(f'      - Nombre: {parent_count}')
        print(f'      - Taille moyenne: {sum(parent_sizes) / len(parent_sizes):.0f} chars')
        print(f'      - Min: {min(parent_sizes)}, Max: {max(parent_sizes)}')
        print(f'\n   Children:')
        print(f'      - Nombre: {total_children}')
        print(f'      - Moyenne par parent: {avg_children_per_parent:.1f}')
        print(f'      - Taille moyenne: {sum(child_sizes) / len(child_sizes):.0f} chars')
        print(f'      - Min: {min(child_sizes)}, Max: {max(child_sizes)}')
        
        # Validation
        print(f'\n=== Validation ===')
        if avg_children_per_parent < 1:
            print(f'   ⚠️  ATTENTION: Moins d\'1 enfant par parent en moyenne')
        elif avg_children_per_parent > 10:
            print(f'   ⚠️  ATTENTION: Beaucoup d\'enfants par parent ({avg_children_per_parent:.1f})')
        else:
            print(f'   ✓ Ratio enfants/parent correct ({avg_children_per_parent:.1f})')
        
        if min(child_sizes) < MIN_CHILD_SIZE:
            print(f'   ⚠️  ATTENTION: Certains enfants sont trop courts')
        else:
            print(f'   ✓ Tous les enfants ont une taille valide (≥ {MIN_CHILD_SIZE} chars)')

    print('\n✓ Phase 2 terminée avec succès!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
