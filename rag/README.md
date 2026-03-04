# 📦 HAProxy RAG Standard - Archive

**Système RAG (Retrieval-Augmented Generation) standard pour la documentation HAProxy 3.2**

**Statut :** 📦 **ARCHIVE** (maintenu pour comparaison et référence)

---

## 📊 Performances

| Benchmark | Questions | Qualité | Réussite | Temps |
|-----------|-----------|---------|----------|-------|
| **V3** | 100 | **0.846/1.0** | **82%** | 22.4s |

---

## 📝 Note Importante

Ce dossier contient l'implémentation **RAG standard** du projet. Cette version est maintenue comme **archive** pour :

1. **Comparaison** avec le système RAG agentic (dans `../agentic_rag/`)
2. **Référence** pour comprendre l'évolution du projet
3. **Tests** de régression et validation

Pour la production, utilisez le système **RAG agentic** dans `../agentic_rag/` qui offre de meilleures performances :
- Qualité : **0.914/1.0** (+5.3%)
- Réussite : **92.4%** (+4.4%)
- Temps : 34.6s

---

## Installation

### Prérequis

- Python 3.11 ou supérieur
- uv (gestionnaire de paquets Python)
- Ollama (pour les LLM locaux)

### Installation des dépendances

```bash
cd rag
uv sync
```

### Installation des modèles Ollama

```bash
# Embedding (MTEB 70.58, 4096 dims)
ollama pull qwen3-embedding:8b

# LLM principal
ollama pull qwen3:latest

# Alternative
ollama pull qwen3.5:9b
```

---

## Utilisation

### Pipeline complet

```bash
uv run python 00_rebuild_all.py
```

### Étapes individuelles

```bash
# Scrapping
uv run python 01_scrape.py

# Enrichissement metadata
uv run python 01b_enrich_metadata.py

# Chunking
uv run python 02_chunking.py

# Indexation
uv run python 03_indexing.py

# Chatbot
uv run python 04_chatbot.py
```

### Benchmark

```bash
# Quick (7 questions)
uv run python 05_bench_targeted.py --level quick

# Standard (20 questions)
uv run python 05_bench_targeted.py --level standard

# Full (100 questions)
uv run python 05_bench_targeted.py --level full
```

---

## Structure du projet

```
rag/
├── 00_rebuild_all.py              # Orchestrateur principal
├── 01_scrape.py                   # Scrapping documentation
├── 01_scrape_bs4.py               # Scrapping alternatif (BeautifulSoup)
├── 01b_enrich_metadata.py         # Enrichissement IA metadata
├── 02_chunking.py                 # Chunking intelligent
├── 03_indexing.py                 # Indexation vectorielle + lexicale
├── 04_chatbot.py                  # Chatbot Gradio
├── 05_bench_targeted.py           # Benchmark ciblé
├── 06_bench_ollama.py             # Benchmark modèles LLM
├── 07_bench_config_correction.py # Benchmark correction config
├── bench_config_dataset.py        # Dataset benchmark config
├── bench_models.py                 # Benchmark modèles
├── bench_questions.py             # Questions de benchmark
├── compare_content.py            # Comparaison contenu
├── compare_rag_vs_agentic.py     # Comparaison RAG vs Agentic
├── compare_rag.py                 # Comparaison RAG
├── compare_scrapers.py            # Comparaison scrapers
├── config.py                      # Configuration centralisée
├── retriever_v3.py                # Retrieval hybride V3
├── llm.py                         # Génération LLM
├── logging_config.py              # Configuration logging
├── haproxy_validator.py           # Validation config HAProxy
├── app/                           # Application Gradio refactorisée
├── data/                          # Données brutes et traitées
└── index_v3/                      # Index vectoriels et lexicaux
```

---

## Architecture

### Pipeline de retrieval

```
Question utilisateur
    ↓
Query Expansion (synonymes techniques)
    ↓
ChromaDB Search (Top-50 vectoriel)
    ↓
BM25 Search (Top-50 lexical)
    ↓
RRF Fusion (combine les 2 scores)
    ↓
FlashRank Rerank (Top-10)
    ↓
Metadata Filtering (filtre par section)
    ↓
Keyword Boosting (booste chunks avec keywords)
    ↓
LLM Generation (qwen3:latest avec contexte)
    ↓
Réponse finale avec sources
```

### Configurations clés

- `TOP_K_RETRIEVAL = 50` : Candidats par méthode
- `TOP_K_RRF = 30` : Après fusion RRF
- `TOP_K_RERANK = 10` : Après reranking
- `RRF_K = 60` : Paramètre RRF
- `CONFIDENCE_THRESHOLD = 0.0` : Seuil de confiance

---

## Comparaison RAG Standard vs Agentic

| Métrique | RAG Standard | RAG Agentic | Amélioration |
|----------|-------------|-------------|--------------|
| Qualité | 0.846/1.0 | 0.914/1.0 | +5.3% |
| Réussite | 82% | 92.4% | +4.4% |
| Temps | 22.4s | 34.6s | +54% |

**RAG Agentic est SUPÉRIEUR en qualité et réussite, mais plus lent.**

---

## Documentation Complète

Pour plus de détails sur le pipeline RAG standard, consultez la documentation dans `../doc/` :

- `GUIDE_COMPLET.md` : Guide complet du pipeline
- `PIPELINE_RAG_GENERIC.md` : Guide générique RAG
- `V3_PERFORMANCE_TRACKING.md` : Historique des performances

---

## Licence

Ce projet fait partie du projet haproxy-dataset-generator.

**Dernière mise à jour :** 2026-03-04
**Statut :** 📦 ARCHIVE (maintenu pour comparaison et référence)
