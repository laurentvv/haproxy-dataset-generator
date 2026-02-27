# 🚀 Pipeline RAG HAProxy V3 - Guide de Reconstruction

**Version :** V3 (qwen3-embedding:8b, MTEB 70.58)  
**Date :** 2026-02-25  
**Statut :** ✅ Prêt pour production

---

## 📁 Structure des fichiers

```
haproxy-dataset-generator/
├── 00_rebuild_all.py      # ⭐ Script unique - Reconstruit tout
├── 01_scrape.py           # Scrapping docs.haproxy.org
├── 01b_enrich_metadata.py # Enrichissement metadata IA (keywords, synonyms, category)
├── 02_chunking.py         # Chunking intelligent avec propagation metadata
├── 03_indexing.py         # Construction index V3
├── 04_chatbot.py          # Interface Gradio
├── 05_bench_targeted.py   # Benchmark (quick/standard/full)
├── 06_bench_ollama.py     # Benchmark modèles LLM
├── bench_questions.py     # Base de questions (92 questions)
├── retriever_v3.py        # Retrieval hybride V3
├── llm.py                 # Génération LLM
├── README_V3.md           # Ce fichier
└── V3_PERFORMANCE_TRACKING.md # Historique des performances
```

---

## 🔄 Reconstruction complète (from scratch)

### **Option 1 : Script unique (recommandé)**

```bash
# Lance TOUT le pipeline automatiquement (~3h)
uv run python 00_rebuild_all.py
```

Ce script fait :
1. Scrapping (~5-10 min)
2. Enrichissement metadata IA avec gemma3:latest (~5-10 min)
3. Chunking avec propagation metadata (~5-10 min)
4. Indexing (~2h)
5. Benchmark Full (optionnel, ~45 min)

---

### **Option 2 : Commandes manuelles**

```bash
# Étape 1 : Scraper (~5-10 min)
uv run python 01_scrape.py

# Étape 2 : Enrichir les sections avec metadata IA (~5-10 min)
uv run python 01b_enrich_metadata.py

# Étape 3 : Chunker (~5-10 min)
uv run python 02_chunking.py

# Étape 4 : Indexer (~2h)
uv run python 03_indexing.py

# Étape 5 : Tester
uv run python 06_bench_v3.py --level full
```

---

## 📊 Commands rapides

### **Chatbot**
```bash
uv run python 04_chatbot.py
# Ouvre : http://localhost:7860
```

### **Benchmarks**
```bash
# Quick (7 questions, 3 min)
uv run python 05_bench_targeted.py --level quick

# Standard (20 questions, 8 min)
uv run python 05_bench_targeted.py --level standard

# Full (92 questions, 45 min)
uv run python 05_bench_targeted.py --level full

# Ciblé (backend/acl uniquement)
uv run python 05_bench_targeted.py --questions full_backend_name,full_acl
```

---

## 🎯 Performances attendues

| Métrique | Valeur | Objectif |
|----------|--------|----------|
| Qualité moyenne | 0.846/1.0 | 0.80+ ✅ |
| Questions résolues | 82% | 80%+ ✅ |
| Temps/requête | 22.4s | <25s ✅ |
| Chunks indexés | ~3650 | - |

---

## 🔧 Features V3

### **Enrichissement IA (01b_enrich_metadata.py)**
- **Modèle :** gemma3:latest
- **Metadata générées par section :**
  - `keywords` (5-10 mots-clés techniques présents dans le texte)
  - `synonyms` (3-5 termes associés, variantes)
  - `summary` (1 phrase résumé)
  - `category` (backend/frontend/acl/ssl/timeout/healthcheck/stick-table/logs/stats/general/loadbalancing)
- **Sortie :** `data/sections_enriched.jsonl`
- **Durée :** ~5-10 min

### **Indexing**
- **Embedding :** qwen3-embedding:8b (MTEB 70.58, #1 mondial)
- **Dimension :** 4096
- **Chunks :** ~3650 (taille moy: 600-800 chars)
- **Index :**
  - ChromaDB (vectoriel)
  - BM25 (lexical)
  - Metadata (pickle)

### **Retrieval**
- TOP_K_RETRIEVAL = 50
- TOP_K_RRF = 30
- TOP_K_RERANK = 10
- RRF_K = 60
- Metadata Filtering (backend, acl, ssl, etc.)
- Keyword Boosting
- Query Expansion

### **Chunks critiques correctement scrapés**
Le fichier `01_scrape.py` capture désormais correctement :
- `4. Proxies` - Syntaxe de déclaration `backend <name>`
- `5.2. Server and default-server options` - Paramètre `weight`

Ces sections étaient mal extraites dans la V2 et causaient des scores de 0.00-0.20 aux questions critiques.

---

## 📈 Historique des versions

| Version | Date | Qualité | Notes |
|---------|------|---------|-------|
| V2 | 2026-02-24 | 0.806 | bge-m3, 1024 dims |
| V3 baseline | 2026-02-25 | 0.846 | qwen3-embedding:8b |
| V3 + TOP_K | 2026-02-25 | 0.863 | TOP_K_RRF=30, TOP_K_RERANK=10 |
| V3 + Prompt | 2026-02-25 | 0.914 | Prompt few-shot strict |
| V3 + Metadata | 2026-02-25 | 0.846 | Metadata Filtering v2 |
| **V3 Fixed Scraper** | **2026-02-26** | **~0.846** | **Scrapping configuration.html amélioré** |

---

## 🎓 Architecture

```
Question utilisateur
       │
       ▼
┌─────────────────────┐
│  Query Expansion    │  Synonymes techniques HAProxy
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Vector Search      │  ChromaDB (qwen3-embedding:8b)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  BM25 Search        │  Lexical
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  RRF Fusion         │  Combine vectoriel + lexical
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  FlashRank Rerank   │  Cross-encoder (top-10)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Metadata Filtering │  Filtre par section
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Keyword Boosting   │  Booste les chunks avec keywords IA
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  LLM Generation     │  qwen3:latest avec contexte
└─────────────────────┘
       │
       ▼
Réponse finale + sources
```

### **Pipeline de données**
```
docs.haproxy.org
       │
       ▼
┌─────────────────────┐
│ 01_scrape.py        │  Scrapping HTML → Markdown
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ 01b_enrich_metadata │  IA enrichment (gemma3:latest)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ 02_chunking.py      │  Chunking + propagation metadata
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ 03_indexing.py      │  Embedding + BM25 + ChromaDB
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ 04_chatbot.py       │  RAG chatbot
└─────────────────────┘
```

---

## 🛠️ Prérequis

```bash
# Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances
uv sync

# Installer les modèles Ollama
ollama pull qwen3-embedding:8b
ollama pull qwen3:latest
```

---

## 📚 Documentation

- `GUIDE_COMPLET.md` - Guide détaillé du pipeline
- `PIPELINE_RAG_GENERIC.md` - Guide générique (adaptable à d'autres docs)
- `V3_PERFORMANCE_TRACKING.md` - Historique complet des performances
- `CORRECTION_QUESTIONS_CRITIQUES.md` - Détails sur les corrections

---

## ✅ Checklist de déploiement

- [ ] `uv sync` effectué
- [ ] Modèles Ollama installés
- [ ] `00_rebuild_all.py` lancé et terminé
- [ ] Benchmark Full > 80% de questions résolues
- [ ] Chatbot fonctionnel (http://localhost:7860)
- [ ] Temps de réponse < 30s

---

**Dernière mise à jour :** 2026-02-25  
**Version :** V3 Finale  
**Statut :** ✅ Prêt pour production
