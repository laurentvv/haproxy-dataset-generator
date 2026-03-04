# Plan d'amélioration du README.md - Système RAG Agentic

## Objectif
Améliorer le README.md principal pour détailler plus complètement la solution Agentic RAG, tout le process, l'installation, le lancement et l'interface Gradio.

## Analyse actuelle

### Points forts du README.md actuel
- ✅ Vue d'ensemble claire des performances
- ✅ Installation rapide avec commandes essentielles
- ✅ Structure du projet bien organisée
- ✅ Documentation des composants principaux
- ✅ Configuration des variables d'environnement
- ✅ Instructions pour les tests et benchmarks

### Points à améliorer
- ❌ Processus complet du pipeline RAG Agentic pas détaillé
- ❌ Architecture LangGraph peu expliquée
- ❌ Hybrid retrieval (Vector + BM25 + RRF) pas documenté
- ❌ Chunking parent/child hiérarchique pas expliqué
- ❌ Interface Gradio peu détaillée
- ❌ Flux de données pas illustré
- ❌ Étapes individuelles du pipeline pas expliquées
- ❌ Dépannage limité
- ❌ Pas de guide de déploiement production détaillé

---

## Plan d'amélioration

### 1. Section "🚀 Installation Rapide" → "📦 Installation Complète"

#### 1.1 Prérequis détaillés
```markdown
## Prérequis

### Système
- **OS**: Linux, macOS, Windows 10+
- **RAM**: 16 GB minimum (32 GB recommandés)
- **Stockage**: 10 GB libres
- **GPU**: NVIDIA avec 8+ GB VRAM (optionnel, pour accélérer Ollama)

### Logiciels requis
- **Python 3.11+**: Pour exécuter le système
- **uv**: Gestionnaire de paquets Python (alternative à pip)
- **Ollama**: Pour exécuter les LLM locaux

### Installation des prérequis

#### Python 3.11+
```bash
# Vérifier la version Python
python --version  # Doit être 3.11 ou supérieur

# Installer uv (gestionnaire de paquets)
pip install uv
```

#### Ollama
```bash
# Installer Ollama
# Linux/macOS:
curl -fsSL https://ollama.com/install.sh | sh

# Windows:
# Télécharger depuis https://ollama.com/download

# Vérifier l'installation
ollama --version
```
```

#### 1.2 Installation des modèles Ollama détaillée
```markdown
### Installation des modèles Ollama

Le système RAG Agentic utilise deux modèles Ollama :

#### 1. Modèle d'Embedding (requis)
```bash
# qwen3-embedding:8b - 4096 dimensions, MTEB score 70.58
ollama pull qwen3-embedding:8b
```

#### 2. Modèle LLM principal (recommandé)
```bash
# qwen3.5:9b - Meilleure qualité pour production
ollama pull qwen3.5:9b
```

#### 3. Alternative (plus rapide, moins précis)
```bash
# qwen3:latest - Plus rapide mais moins précis
ollama pull qwen3:latest
```

### Vérification des modèles
```bash
# Lister les modèles installés
ollama list

# Vérifier que les modèles sont disponibles
ollama show qwen3-embedding:8b
ollama show qwen3.5:9b
```
```

---

### 2. Nouvelle section "🔄 Processus Complet du Pipeline RAG Agentic"

```markdown
## 🔄 Processus Complet du Pipeline RAG Agentic

Le système RAG Agentic pour HAProxy 3.2 utilise une architecture avancée avec LangGraph pour fournir des réponses de haute qualité basées sur la documentation officielle.

### Vue d'ensemble du pipeline

Le pipeline se compose de 4 phases principales :

```
Documentation HAProxy 3.2
    ↓
[Phase 1] Scraping & Validation (01_scrape_verified.py)
    ↓
[Phase 2] Chunking Parent/Child (02_chunking_parent_child.py)
    ↓
[Phase 3] Indexation ChromaDB + BM25 (03_indexing_chroma.py)
    ↓
[Phase 4] Chatbot Gradio (04_agentic_chatbot.py)
```

### Phase 1 : Scraping & Validation

**Script**: [`01_scrape_verified.py`](agentic_rag/01_scrape_verified.py)

**Objectif**: Extraire et valider la documentation HAProxy 3.2 depuis docs.haproxy.org

**Processus**:
1. **Crawl de la documentation**: Utilisation de crawl4ai pour scraper 168 sections
2. **Validation**: Vérification de la structure et du contenu
3. **Enrichissement**: Ajout de metadata (titres, sections, hiérarchie)
4. **Sauvegarde**: Stockage dans `data_agentic/scraped_pages/scraped_3.2.json`

**Durée**: ~5 minutes

**Sortie**:
- `data_agentic/scraped_pages/scraped_3.2.json`: 168 sections validées
- `data_agentic/hierarchy_report.json`: Rapport de hiérarchie
- `data_agentic/scraping_diff_report.json`: Différences avec version précédente

### Phase 2 : Chunking Parent/Child

**Script**: [`02_chunking_parent_child.py`](agentic_rag/02_chunking_parent_child.py)

**Objectif**: Diviser la documentation en chunks hiérarchiques pour un retrieval optimal

**Stratégie Parent/Child**:
- **Parent chunks**: Documents complets (max 4000 chars) pour le contexte
- **Child chunks**: Chunks plus petits (300 chars) pour la recherche vectorielle
- **Overlap**: 150 chars (50%) pour préserver le contexte

**Configuration**:
```python
CHUNKING_CONFIG = {
    'parent_max_chars': 4000,    # Taille max d'un parent
    'child_max_chars': 300,      # Taille max d'un child (optimisé)
    'chunk_overlap': 150,        # 50% overlap (meilleur contexte)
    'min_child_size': 30,        # Garder petits chunks pertinents
    'max_children_per_parent': 30,  # Plus d'enfants par parent
}
```

**Processus**:
1. **Création des parents**: Division en sections de 4000 chars maximum
2. **Création des children**: Subdivision des parents en chunks de 300 chars
3. **Indexation**: Assignation d'IDs parent/child
4. **Sauvegarde**: Stockage dans `data_agentic/chunks_child.json`

**Durée**: ~5 minutes

**Sortie**:
- `data_agentic/chunks_child.json`: 101 parents, 915 children
- `parent_store/`: Stockage JSON des parents

**Optimisation**: Chunking plus fin (300 vs 500 chars) → +91% de chunks → +12% qualité

### Phase 3 : Indexation ChromaDB + BM25

**Script**: [`03_indexing_chroma.py`](agentic_rag/03_indexing_chroma.py)

**Objectif**: Indexer les chunks pour un retrieval hybride (Vector + BM25 + RRF)

**Architecture Hybrid Retrieval**:
1. **Vector Search (ChromaDB)**: Recherche sémantique avec embeddings
2. **BM25 Search**: Recherche lexicale avec mots-clés exacts
3. **RRF Fusion**: Fusion des résultats avec Reciprocal Rank Fusion

**Processus**:
1. **Vectorisation**: Embedding des child chunks avec qwen3-embedding:8b
2. **Indexation ChromaDB**: Stockage vectoriel dans `index_agentic/chroma_db/`
3. **Indexation BM25**: Construction de l'index lexical dans `index_agentic/bm25_index.pkl`
4. **Optimisation**: Metadata filtering avec SECTION_HINTS

**Configuration**:
```python
HYBRID_RETRIEVAL_ENABLED = True
HYBRID_TOP_K = 15          # Résultats après fusion RRF
HYBRID_RRF_K = 60          # Paramètre RRF
HYBRID_VECTOR_WEIGHT = 0.5  # Poids égal Vector/BM25
HYBRID_BM25_WEIGHT = 0.5    # Poids de BM25
```

**Durée**: ~1 minute

**Sortie**:
- `index_agentic/chroma_db/`: Base de données vectorielle ChromaDB
- `index_agentic/bm25_index.pkl`: Index BM25 lexical

**Optimisation**: Hybrid retrieval → +14% qualité, +5% réussite

### Phase 4 : Chatbot Gradio

**Script**: [`04_agentic_chatbot.py`](agentic_rag/04_agentic_chatbot.py)

**Objectif**: Interface utilisateur interactive pour poser des questions sur HAProxy 3.2

**Architecture**:
1. **Interface Gradio**: UI web sur le port 7861
2. **Agent LangGraph**: Orchestration agentic avec multi-step reasoning
3. **Hybrid Retriever**: Vector + BM25 + RRF pour le retrieval
4. **Streaming**: Réponses en temps réel

**Détails**: Voir section "Interface Gradio" ci-dessous

---

## 🏗️ Architecture LangGraph

### Vue d'ensemble

Le système utilise LangGraph pour orchestrer un agent RAG agentic capable de multi-step reasoning.

### Graphe d'agent

```
START → summarize_conversation → analyze_and_rewrite_query
                                       ↓
                               [INTERRUPT_BEFORE: agent]
                                       ↓
                               should_use_tools?
                               ↙              ↘
                          YES (tools)      NO (end)
                             ↓
                     ToolNode (search_child_chunks + BM25)
                             ↓
                          agent → retrieve_parent_chunks
                             ↓
                          LLM (qwen3.5:9b) → réponse
                             ↓
                           END
```

### Nœuds du graphe

#### 1. summarize_conversation
- **Rôle**: Résumer la conversation précédente
- **Objectif**: Maintenir le contexte sur les conversations longues
- **Condition**: Exécuté si la conversation dépasse un seuil

#### 2. analyze_and_rewrite_query
- **Rôle**: Analyser et réécrire la requête utilisateur
- **Objectif**: Améliorer la qualité de la requête pour le retrieval
- **Actions**: Expansion, clarification, reformulation

#### 3. agent
- **Rôle**: Nœud principal de l'agent LLM
- **Objectif**: Décider d'utiliser les outils ou de répondre directement
- **LLM**: qwen3.5:9b (temperature 0.1)

#### 4. tools
- **Rôle**: Exécuter les outils de retrieval
- **Outils disponibles**:
  - `search_child_chunks`: Hybrid retrieval (Vector + BM25 + RRF)
  - `retrieve_parent_chunks`: Récupérer le contexte complet
  - `validate_haproxy_config`: Valider la configuration HAProxy

### Outils de retrieval

#### search_child_chunks
- **Type**: Hybrid retrieval
- **Méthodes**: Vector + BM25 + RRF
- **Paramètres**: k=15, rrf_k=60
- **Optimisation**: Metadata filtering avec SECTION_HINTS

#### retrieve_parent_chunks
- **Type**: Context retrieval
- **Objectif**: Récupérer le contexte complet depuis les parents
- **Sortie**: Documents parents avec metadata

#### validate_haproxy_config
- **Type**: Validation
- **Objectif**: Valider la syntaxe HAProxy
- **Sortie**: Erreurs et avertissements

### Flux de données

```
Question utilisateur
    ↓
[summarize_conversation] Résumé de l'historique
    ↓
[analyze_and_rewrite_query] Analyse et réécriture
    ↓
[agent] Décision: outils ou réponse directe?
    ↓
[tools] Hybrid retrieval (Vector + BM25 + RRF)
    ↓
[retrieve_parent_chunks] Contexte complet
    ↓
[LLM qwen3.5:9b] Génération de la réponse
    ↓
Réponse finale + sources
```

---

## 🎨 Interface Gradio

### Lancement du chatbot

```bash
cd agentic_rag
uv run python 04_agentic_chatbot.py
```

**Accès**: http://localhost:7861

### Fonctionnalités de l'interface

#### 1. Zone de chat
- **Conversation**: Historique des messages utilisateur/assistant
- **Streaming**: Réponses en temps réel
- **Sources**: Affichage des sources utilisées

#### 2. Zone de saisie
- **Input**: Textbox pour poser des questions
- **Exemples**: Questions prédéfinies pour démarrer
- **Submit**: Bouton pour envoyer la question

#### 3. Boutons de contrôle
- **Nouvelle conversation**: Effacer l'historique
- **Sauvegarder**: Exporter la conversation en JSON
- **Charger**: Importer une conversation depuis un fichier JSON

#### 4. Exemples de questions
- "Comment configurer un backend HTTP dans HAProxy 3.2 ?"
- "Quelles sont les nouvelles fonctionnalités de HAProxy 3.2 ?"
- "Comment utiliser le stick-table pour la persistance ?"
- "Comment configurer le load balancing avec round-robin ?"
- "Qu'est-ce que le multiplexer dans HAProxy 3.2 ?"

### Personnalisation

**Port**: Modifier `GRADIO_CONFIG['port']` dans [`config_agentic.py`](agentic_rag/config_agentic.py)

```python
GRADIO_CONFIG = {
    'port': 7861,  # Modifier le port si nécessaire
    'share': False,  # True pour créer un lien public
}
```

**Thème**: Le thème Gradio peut être personnalisé dans [`app/gradio_app.py`](agentic_rag/app/gradio_app.py)

```python
demo.launch(
    theme=gr.themes.Soft(),  # Changer le thème
    css="...",  # CSS personnalisé
)
```

---

## ⚙️ Configuration Avancée

### Variables d'environnement

#### Ollama
```bash
export OLLAMA_URL=http://localhost:11434  # URL du serveur Ollama
export EMBED_MODEL=qwen3-embedding:8b    # Modèle d'embedding
export LLM_MODEL=qwen3.5:9b              # Modèle LLM principal
export FAST_MODEL=lfm2.5-thinking:1.2b-bf16  # Modèle rapide (optionnel)
```

#### RAG Agentic
```bash
export CHILD_CHUNK_SIZE=300              # Taille chunks enfants
export DEFAULT_K_CHILD=5                 # Nombre de chunks enfants
export HYBRID_RETRIEVAL_ENABLED=true     # Activer hybrid retrieval
```

### Configuration dans config_agentic.py

Tous les paramètres sont centralisés dans [`config_agentic.py`](agentic_rag/config_agentic.py):

```python
# Configuration scraping
SCRAPER_CONFIG = {
    'base_url': 'https://docs.haproxy.org/',
    'version': '3.2',
    'max_pages': 1000,
    'timeout': 30,
}

# Configuration chunking
CHUNKING_CONFIG = {
    'parent_max_chars': 4000,
    'child_max_chars': 300,
    'chunk_overlap': 150,
    'min_child_size': 30,
    'max_children_per_parent': 30,
}

# Configuration ChromaDB
CHROMA_CONFIG = {
    'collection_name': 'haproxy_child_chunks',
    'embedding_model': 'qwen3-embedding:8b',
    'persist_directory': 'index_agentic/chroma_db',
}

# Configuration LangGraph
LANGGRAPH_CONFIG = {
    'max_retrieval_steps': 3,
    'max_refinement_steps': 2,
    'temperature': 0.1,
    'max_tokens': 2000,
}

# Configuration LLM
LLM_CONFIG = {
    'model': 'qwen3.5:9b',
    'temperature': 0.1,
    'top_p': 0.9,
    'num_ctx': 4096,
}

# Configuration Gradio
GRADIO_CONFIG = {
    'title': 'HAProxy Agentic RAG Chatbot',
    'description': 'Assistant intelligent basé sur LangGraph pour la documentation HAProxy 3.2',
    'port': 7861,
    'share': False,
}
```

---

## 🚨 Dépannage

### Problèmes Ollama

#### Ollama ne répond pas
```bash
# Vérifier si Ollama est en cours d'exécution
ollama ps

# Redémarrer Ollama
# Linux/macOS:
systemctl restart ollama  # ou
ollama serve

# Windows:
# Redémarrer depuis le gestionnaire de services
```

#### Modèles non disponibles
```bash
# Lister les modèles installés
ollama list

# Réinstaller les modèles
ollama pull qwen3-embedding:8b
ollama pull qwen3.5:9b
```

### Problèmes ChromaDB

#### Erreur de persistance
```bash
# Supprimer l'index existant
rm -rf index_agentic/chroma_db/*

# Réindexer
cd agentic_rag
uv run python 03_indexing_chroma.py
```

#### Erreur de connexion
```bash
# Vérifier que l'index existe
ls -la index_agentic/chroma_db/

# Reconstruire l'index
uv run python 03_indexing_chroma.py
```

### Problèmes de performance

#### Réponses lentes
```bash
# Vérifier l'utilisation de la mémoire
ollama ps

# Utiliser un modèle plus rapide
export LLM_MODEL=qwen3:latest

# Réduire le nombre de chunks
export DEFAULT_K_CHILD=5
```

#### Qualité des réponses insuffisante
```bash
# Vérifier que le hybrid retrieval est activé
export HYBRID_RETRIEVAL_ENABLED=true

# Utiliser un modèle plus précis
export LLM_MODEL=qwen3.5:9b

# Augmenter le nombre de chunks
export DEFAULT_K_CHILD=10
```

### Problèmes de scraping

#### Erreur de connexion
```bash
# Vérifier la connexion Internet
ping docs.haproxy.org

# Augmenter le timeout
# Modifier SCRAPER_CONFIG['timeout'] dans config_agentic.py
```

#### Erreur de validation
```bash
# Vérifier le rapport de hiérarchie
cat data_agentic/hierarchy_report.json

# Vérifier le rapport de différences
cat data_agentic/scraping_diff_report.json
```

---

## 📊 Performances et Optimisations

### Résultats des benchmarks

| Benchmark | Questions | Qualité | Réussite | Temps |
|-----------|-----------|---------|----------|-------|
| **QUICK** | 7 | **0.880/1.0** | **85.7%** | 34.3s |
| **FULL** | 92 | **0.914/1.0** 🏆 | **92.4%** 🏆 | 34.6s |

### Comparaison avec RAG V3 (Standard)

| Système | Qualité | Réussite | Temps |
|---------|---------|----------|-------|
| RAG V3 | 0.868/1.0 | 88% | ~24s |
| **Agentic V3** | **0.914/1.0** (+5.3%) | **92.4%** (+4.4%) | 34.6s |

### Optimisations implémentées

#### Phase 1 : Chunking Plus Fin
- **Changement**: 500 → 300 chars
- **Résultat**: +91% de chunks (915 vs 434)
- **Impact**: +12% qualité

#### Phase 2 : Metadata Filtering
- **Changement**: SECTION_HINTS avec 50+ keywords
- **Résultat**: Boost configuration.html > intro.html
- **Impact**: +3-5% sur questions techniques

#### Phase 3 : Hybrid Retrieval
- **Changement**: Vector + BM25 + RRF
- **Résultat**: k=15 résultats, rrf_k=60
- **Impact**: +14% qualité, +5% réussite

---

## 🚀 Guide de Déploiement Production

### 1. Prérequis système

```bash
# RAM minimale : 16 GB (32 GB recommandés)
# GPU : NVIDIA avec 8+ GB VRAM (pour accélérer Ollama)
# Stockage : 10 GB libres

# Vérifier Ollama
ollama --version

# Vérifier Python
python --version  # 3.11+ requis
```

### 2. Installation

```bash
# Cloner le projet
cd haproxy-dataset-generator/agentic_rag

# Installer dépendances
uv sync

# Installer modèles Ollama
ollama pull qwen3-embedding:8b
ollama pull qwen3.5:9b
```

### 3. Build initial

```bash
# Pipeline complet (~1h10)
uv run python -u 00_rebuild_agentic.py

# Ou étapes individuelles (recommandé pour debug)
uv run python -u 01_scrape_verified.py      # ~5 min
uv run python -u 02_chunking_parent_child.py # ~5 min
uv run python -u 03_indexing_chroma.py      # ~1 min
```

### 4. Validation

```bash
# Quick benchmark (~4 min)
uv run python -u 05_bench_agentic.py --level quick

# Vérifier résultats attendus :
# - Qualité >= 0.80/1.0
# - Réussite >= 80%
```

### 5. Démarrage chatbot

```bash
# Production (port 7861)
uv run python -u 04_agentic_chatbot.py

# Accès : http://localhost:7861
```

### 6. Monitoring

```bash
# Vérifier Ollama
ollama ps  # Modèles chargés en mémoire

# Vérifier ChromaDB
ls -la index_agentic/chroma_db/

# Logs
tail -f logs/*.log  # Si logging activé
```

### 7. Maintenance

```bash
# Rebuild complet (si documentation mise à jour)
uv run python -u 00_rebuild_agentic.py

# Benchmark régulier (validation continue)
uv run python -u 05_bench_agentic.py --level standard

# Nettoyage (si problèmes)
rm -rf index_agentic/chroma_db/*
rm -rf data_agentic/chunks_child.json
uv run python -u 03_indexing_chroma.py
```

### 8. Scaling (Optionnel)

#### Multi-GPU
```bash
# Ollama supporte multi-GPU automatiquement
# Configurer OLLAMA_NUM_GPU dans .env
```

#### Rate Limiting
```python
# config_agentic.py
LLM_CONFIG = {
    'rate_limit_calls_per_minute': 20,  # Ajuster selon charge
}
```

#### Session Persistence
```python
# LangGraph checkpointing activé par défaut
# Sessions sauvegardées dans memory (InMemorySaver)
# Pour production : utiliser PostgresSaver
```

---

## 📚 Documentation Additionnelle

- **[`agentic_rag/README_AGENTIC.md`](agentic_rag/README_AGENTIC.md)**: Guide complet du système RAG Agentic
- **[`agentic_rag/PERFORMANCE.md`](agentic_rag/PERFORMANCE.md)**: Suivi détaillé des performances et optimisations
- **[`doc/GUIDE_IMPLEMENTATION_AGENTIC.md`](doc/GUIDE_IMPLEMENTATION_AGENTIC.md)**: Guide d'implémentation du RAG agentic
- **[`doc/plans/PLAN_AGENTIC_RAG_HAPROXY.md`](doc/plans/PLAN_AGENTIC_RAG_HAPROXY.md)**: Architecture détaillée
- **[`doc/V3_PERFORMANCE_TRACKING.md`](doc/V3_PERFORMANCE_TRACKING.md)**: Comparaison avec RAG V3

---

## 🎯 Backlog - Questions à Améliorer (7/92)

**Questions avec score < 0.80/1.0 :**

| Question | Score | Catégorie | Action Requise |
|----------|-------|-----------|----------------|
| `full_httpchk_uri` | 0.55 | healthcheck | Améliorer retrieval URI health check |
| `full_balance_uri` | 0.70 | balance | URI hashing balance configuration |
| `full_ssl_default_bind` | 0.60 | ssl | SSL default bindings clarification |
| `full_stats_socket` | 0.70 | stats | Stats socket configuration details |
| `full_option_forwardfor` | 0.60 | option | forwardfor option implementation |
| `full_map_beg` | 0.70 | map | Map begin matching examples |
| `full_converter_json` | 0.70 | converter | JSON converter HAProxy-specific |

**Actions Planifiées :**

### Phase 4 : Enrichissement IA Metadata (Optionnel)
- **Objectif** : +2-3% qualité
- **Tâche** : Générer keywords + synonyms pour chaque chunk
- **Fichier** : `01b_enrich_metadata.py` (inspiré du RAG V3)
- **Effort** : ~2h

### Phase 5 : Query Expansion avec LLM (Optionnel)
- **Objectif** : +1-2% qualité
- **Tâche** : Générer 3-5 variantes de query pour retrieval
- **Fichier** : `rag_agent/nodes.py` (analyze_and_rewrite_query)
- **Effort** : ~1h

### Phase 6 : FlashRank Reranking (Optionnel)
- **Objectif** : +1-2% qualité
- **Tâche** : Ajouter reranking post-retrieval
- **Fichier** : `rag_agent/tools.py` (search_child_chunks)
- **Effort** : ~1h

**Cible Finale :** 0.95+/1.0 qualité, 95%+ réussite
