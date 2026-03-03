# 🚀 HAProxy Agentic RAG - Production Ready

**Système RAG Agentic pour la documentation HAProxy utilisant LangGraph**

**Statut :** ✅ **PRÊT POUR PRODUCTION** (2026-03-03)

---

## 📊 Performances

| Benchmark | Questions | Qualité | Réussite | Temps |
|-----------|-----------|---------|----------|-------|
| **QUICK** | 7 | **0.880/1.0** | **85.7%** | 34.3s |
| **FULL** | 92 | **0.914/1.0** 🏆 | **92.4%** 🏆 | 34.6s |

**Comparaison avec RAG V3 (Standard) :**
| Système | Qualité | Réussite | Temps |
|---------|---------|----------|-------|
| RAG V3 | 0.868/1.0 | 88% | ~24s |
| **Agentic V3** | **0.914/1.0** (+5.3%) | **92.4%** (+4.4%) | 34.6s |

**🏆 Agentic RAG est SUPÉRIEUR au RAG V3 sur qualité et réussite !**

---

## Installation

### Prérequis

- Python 3.11 ou supérieur
- uv (gestionnaire de paquets Python)
- Ollama (pour les LLM locaux)

### Installation des dépendances

```bash
cd agentic_rag
uv sync
```

### Installation des modèles Ollama

```bash
# Embedding (MTEB 70.58, 4096 dims)
ollama pull qwen3-embedding:8b

# LLM principal (recommandé pour production)
ollama pull qwen3.5:9b

# Alternative (plus rapide, moins précis)
ollama pull qwen3:latest
```

## Structure du projet

```
agentic_rag/
├── 00_rebuild_agentic.py               # Orchestrateur principal
├── 01_scrape_verified.py               # Scraping + validation
├── 02_chunking_parent_child.py         # Chunking hiérarchique
├── 03_indexing_chroma.py               # Indexation ChromaDB
├── 04_agentic_chatbot.py               # Chatbot Gradio (port 7861)
├── 05_bench_agentic.py                 # Benchmark comparatif
├── 06_eval_parent_child.py             # Évaluation parent/child
├── 07_export_dataset_agentic.py        # Export dataset Q&A
│
├── app/                                # Interface utilisateur
├── rag_agent/                          # Module LangGraph
├── db/                                 # Gestion des bases de données
├── scraper/                            # Outils de scraping
├── tests/                              # Tests unitaires
│
├── data_agentic/                       # Données générées
├── index_agentic/                      # Index ChromaDB
├── parent_store/                       # Stockage JSON parents
│
├── pyproject_agentic.toml              # Dépendances
├── config_agentic.py                   # Configuration
└── README_AGENTIC.md                   # Ce fichier
```

## Utilisation

### 1. Pipeline complet (rebuild)

Exécutez tout le pipeline de scraping à l'indexation:

```bash
uv run python 00_rebuild_agentic.py
```

### 2. Étapes individuelles

#### Scraping

```bash
uv run python 01_scrape_verified.py
```

#### Chunking parent/child

```bash
uv run python 02_chunking_parent_child.py
```

#### Indexation ChromaDB

```bash
uv run python 03_indexing_chroma.py
```

### 3. Chatbot

Lancez l'interface Gradio sur le port 7861:

```bash
uv run python 04_agentic_chatbot.py
```

Accédez ensuite à `http://localhost:7861`

### 4. Benchmark

Exécutez les benchmarks comparatifs:

```bash
uv run python 05_bench_agentic.py
```

### 5. Évaluation

Évaluez la qualité du chunking parent/child:

```bash
uv run python 06_eval_parent_child.py
```

### 6. Export dataset

Exportez le dataset Q&A pour l'entraînement:

```bash
uv run python 07_export_dataset_agentic.py
```

## Tests

Exécutez tous les tests:

```bash
uv run pytest
```

Exécutez des tests spécifiques:

```bash
uv run pytest tests/test_scraper_alignment.py
uv run pytest tests/test_chunking.py
uv run pytest tests/test_retrieval.py
uv run pytest tests/test_graph_flow.py
uv run pytest tests/test_end_to_end.py
```

## Configuration

Les paramètres de configuration sont centralisés dans `config_agentic.py`:

- `SCRAPER_CONFIG`: Configuration du scraping
- `CHUNKING_CONFIG`: Paramètres de chunking
- `CHROMA_CONFIG`: Configuration ChromaDB
- `LANGGRAPH_CONFIG`: Paramètres LangGraph
- `LLM_CONFIG`: Configuration du LLM
- `GRADIO_CONFIG`: Paramètres de l'interface Gradio
- `BENCHMARK_CONFIG`: Configuration des benchmarks
- `EXPORT_CONFIG`: Configuration de l'export

## Architecture

### Composants principaux

1. **Scraper**: Extraction et validation de la documentation HAProxy (crawl4ai)
2. **Chunking**: Division hiérarchique parent/child (300 chars, 150 overlap)
3. **Indexation**: Stockage vectoriel ChromaDB + BM25 (hybrid retrieval)
4. **Agent LangGraph**: Orchestration agentic (multi-step reasoning)
5. **Hybrid Retriever**: Vector + BM25 + RRF (meilleur retrieval)
6. **Chatbot**: Interface Gradio pour l'interaction utilisateur

### Optimisations Clés (Phases 1-3)

**Phase 1 : Chunking Plus Fin**
- 300 chars (vs 500 avant) → **+91% de chunks** (915 vs 434)
- 150 overlap (50%) → meilleur contexte
- Résultat : +12% qualité

**Phase 2 : Metadata Filtering**
- SECTION_HINTS : 50+ keywords mappés
- Boost configuration.html > intro.html
- Résultat : +3-5% sur questions techniques

**Phase 3 : Hybrid Retrieval**
- Vector (ChromaDB) + BM25 (lexical) + RRF (fusion)
- k=15 résultats, rrf_k=60
- Résultat : **+14% qualité**, +5% réussite

### Flux de données

```
Documentation HAProxy (docs.haproxy.org/3.2/)
    ↓
Scraper (crawl4ai, 168 sections)
    ↓
Chunking Parent/Child (101 parents, 915 children)
    ↓
Indexation (ChromaDB + BM25, ~60s)
    ↓
Agent LangGraph (query analysis → tools → response)
    ↓
Hybrid Retrieval (Vector + BM25 + RRF → top 15 chunks)
    ↓
LLM qwen3.5:9b (génération avec contexte)
    ↓
Chatbot Gradio (réponse + sources)
```

### Architecture Agent LangGraph

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

**Outils :**
- `search_child_chunks` : Hybrid retrieval (Vector + BM25 + RRF, k=15)
- `retrieve_parent_chunks` : Contexte complet depuis parents
- `validate_haproxy_config` : Validation syntaxe HAProxy (optionnel)

**Configuration Hybrid Retrieval :**
```python
HYBRID_RETRIEVAL_ENABLED = True
HYBRID_TOP_K = 15          # Résultats finaux
HYBRID_RRF_K = 60          # Paramètre RRF
HYBRID_VECTOR_WEIGHT = 0.5 # Poids égal Vector/BM25
HYBRID_BM25_WEIGHT = 0.5
```

## Développement

### Formatage du code

```bash
uv run ruff check --fix .
uv run ruff format .
```

### Linting

```bash
uv run ruff check .
```

## Dépannage

### Problèmes Ollama

Si Ollama ne répond pas, vérifiez:

```bash
ollama list
ollama ps
```

### Problèmes ChromaDB

Si ChromaDB a des problèmes de persistance:

```bash
# Supprimer l'index existant
rm -rf index_agentic/chroma_db/*

# Réindexer
uv run python 03_indexing_chroma.py
```

---

## 📚 Documentation Additionnelle

- **PERFORMANCE.md** : Suivi détaillé des performances et optimisations
- **V3_PERFORMANCE_TRACKING.md** : Comparaison avec RAG V3 (racine du projet)
- **GUIDE_COMPLET.md** : Guide complet du pipeline RAG (racine du projet)

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

---

## 🚀 Guide de Déploiement Production

### 1. Prérequis Système

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

### 3. Build Initial

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

### 5. Démarrage Chatbot

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

**Multi-GPU :**
```bash
# Ollama supporte multi-GPU automatiquement
# Configurer OLLAMA_NUM_GPU dans .env
```

**Rate Limiting :**
```python
# config_agentic.py
LLM_CONFIG = {
    'rate_limit_calls_per_minute': 20,  # Ajuster selon charge
}
```

**Session Persistence :**
```python
# LangGraph checkpointing activé par défaut
# Sessions sauvegardées dans memory (InMemorySaver)
# Pour production : utiliser PostgresSaver
```

---

## Licence

Ce projet fait partie du projet haproxy-dataset-generator.

**Dernière mise à jour :** 2026-03-03
**Statut :** ✅ PRODUCTION READY (0.914/1.0, 92.4% réussite)
