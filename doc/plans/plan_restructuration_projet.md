# Plan de Restructuration du Projet

## 📋 Objectif

Restructurer le projet pour séparer clairement :
- **agentic_rag/** : Système RAG agentic (implémentation principale)
- **rag/** : Système RAG standard (archive et comparaison)
- **doc/** : Documentation technique
- **Racine** : Fichiers de configuration uniquement

---

## 🗂️ Structure Cible

```
haproxy-dataset-generator/
├── README.md                          # Mis à jour (présentation agentic_rag)
├── pyproject.toml                     # Dépendances globales
├── .gitignore                         # Git ignore
├── .python-version                    # Version Python
├── skills-lock.json                   # Skills lock
├── .agents/                           # Config agents
├── .kilocode/                         # Config kilocode
│
├── agentic_rag/                       # ⭐ Système RAG Agentic (PRINCIPAL)
│   ├── README_AGENTIC.md
│   ├── config_agentic.py
│   ├── 00_rebuild_agentic.py
│   ├── 01_scrape_verified.py
│   ├── 02_chunking_parent_child.py
│   ├── 03_indexing_chroma.py
│   ├── 04_agentic_chatbot.py
│   ├── 05_bench_agentic.py
│   ├── 06_eval_parent_child.py
│   ├── 07_export_dataset_agentic.py
│   ├── app/
│   ├── rag_agent/
│   ├── db/
│   ├── scraper/
│   ├── tests/
│   ├── data_agentic/
│   ├── index_agentic/
│   └── parent_store/
│
├── rag/                               # 📦 Système RAG Standard (ARCHIVE)
│   ├── README.md                      # Nouveau fichier README dédié
│   ├── config.py
│   ├── llm.py
│   ├── retriever_v3.py
│   ├── logging_config.py
│   ├── haproxy_validator.py
│   ├── 00_rebuild_all.py
│   ├── 01_scrape.py
│   ├── 01_scrape_bs4.py
│   ├── 01b_enrich_metadata.py
│   ├── 02_chunking.py
│   ├── 03_indexing.py
│   ├── 04_chatbot.py
│   ├── 05_bench_targeted.py
│   ├── 06_bench_ollama.py
│   ├── 07_bench_config_correction.py
│   ├── bench_config_dataset.py
│   ├── bench_models.py
│   ├── bench_questions.py
│   ├── compare_content.py
│   ├── compare_rag_vs_agentic.py
│   ├── compare_rag.py
│   ├── compare_scrapers.py
│   ├── app/
│   ├── data/
│   └── index_v3/
│
└── doc/                               # 📚 Documentation Technique
    ├── AGENTS.md
    ├── BENCHMARK_TIMES.md
    ├── CORRECTION_QUESTIONS_CRITIQUES.md
    ├── GUIDE_COMPLET.md
    ├── GUIDE_IMPLEMENTATION_AGENTIC.md
    ├── LEARNING.md
    ├── PIPELINE_RAG_GENERIC.md
    ├── QWEN.md
    ├── V3_PERFORMANCE_TRACKING.md
    ├── config_crawl4ai.md
    ├── full_config.md
    ├── intro_crawl4ai.md
    └── plans/
        ├── ameliorations_chunking.md
        ├── analyse_elements_superflus.md
        ├── audit_technique_agentic_rag.md
        ├── benchmark_dataset_spec.md
        ├── benchmark_improvement_plan.md
        ├── benchmark_metrics_spec.md
        ├── benchmark_validator_spec.md
        ├── PLAN_AGENTIC_RAG_HAPROXY.md
        ├── plan_benchmark_correction_config.md
        ├── plan_integration_crawl4ai_agentic_rag.md
        ├── plan_reconstruction_04_chatbot.md
        ├── plan_verification_amelioration_gradio_6.8.0.md
        └── plan_restructuration_projet.md
```

---

## 📦 Étapes de Migration

### Étape 1 : Créer la structure rag/

**Créer les dossiers :**
```bash
mkdir rag
mkdir rag/app
mkdir rag/data
mkdir rag/index_v3
```

### Étape 2 : Déplacer les scripts Python RAG standard

**Fichiers à déplacer vers rag/ :**
- `00_rebuild_all.py`
- `01_scrape.py`
- `01_scrape_bs4.py`
- `01b_enrich_metadata.py`
- `02_chunking.py`
- `03_indexing.py`
- `04_chatbot.py`
- `05_bench_targeted.py`
- `06_bench_ollama.py`
- `07_bench_config_correction.py`
- `bench_config_dataset.py`
- `bench_models.py`
- `bench_questions.py`
- `compare_content.py`
- `compare_rag_vs_agentic.py`
- `compare_rag.py`
- `compare_scrapers.py`
- `config.py`
- `haproxy_validator.py`
- `llm.py`
- `logging_config.py`
- `retriever_v3.py`

**Commandes :**
```bash
mv 00_rebuild_all.py rag/
mv 01_scrape.py rag/
mv 01_scrape_bs4.py rag/
mv 01b_enrich_metadata.py rag/
mv 02_chunking.py rag/
mv 03_indexing.py rag/
mv 04_chatbot.py rag/
mv 05_bench_targeted.py rag/
mv 06_bench_ollama.py rag/
mv 07_bench_config_correction.py rag/
mv bench_config_dataset.py rag/
mv bench_models.py rag/
mv bench_questions.py rag/
mv compare_content.py rag/
mv compare_rag_vs_agentic.py rag/
mv compare_rag.py rag/
mv compare_scrapers.py rag/
mv config.py rag/
mv haproxy_validator.py rag/
mv llm.py rag/
mv logging_config.py rag/
mv retriever_v3.py rag/
```

### Étape 3 : Déplacer les répertoires RAG standard

**Répertoires à déplacer vers rag/ :**
- `app/`
- `data/`
- `index_v3/`

**Commandes :**
```bash
mv app rag/
mv data rag/
mv index_v3 rag/
```

### Étape 4 : Créer le fichier README.md dans rag/

**Contenu :**
```markdown
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
```

### Étape 5 : Créer le dossier doc/ et déplacer la documentation

**Créer le dossier :**
```bash
mkdir doc
```

**Déplacer les fichiers de documentation vers doc/ :**
```bash
mv AGENTS.md doc/
mv BENCHMARK_TIMES.md doc/
mv CORRECTION_QUESTIONS_CRITIQUES.md doc/
mv GUIDE_COMPLET.md doc/
mv GUIDE_IMPLEMENTATION_AGENTIC.md doc/
mv LEARNING.md doc/
mv PIPELINE_RAG_GENERIC.md doc/
mv QWEN.md doc/
mv V3_PERFORMANCE_TRACKING.md doc/
mv config_crawl4ai.md doc/
mv full_config.md doc/
mv intro_crawl4ai.md doc/
mv plans doc/
```

### Étape 6 : Mettre à jour le README.md à la racine

**Nouveau contenu :**
```markdown
# HAProxy Dataset Generator - RAG Agentic

**Système RAG Agentic pour la documentation HAProxy 3.2 utilisant LangGraph**

**Statut :** ✅ **PRÊT POUR PRODUCTION** (2026-03-04)

---

## 📊 Performances

| Benchmark | Questions | Qualité | Réussite | Temps |
|-----------|-----------|---------|----------|-------|
| **QUICK** | 7 | **0.880/1.0** | **85.7%** | 34.3s |
| **FULL** | 92 | **0.914/1.0** 🏆 | **92.4%** 🏆 | 34.6s |

---

## 🚀 Installation Rapide

```bash
# Installer les dépendances
uv sync

# Installer les modèles Ollama
ollama pull qwen3-embedding:8b
ollama pull qwen3.5:9b

# Reconstruire tout le pipeline (~1h10)
cd agentic_rag
uv run python 00_rebuild_agentic.py

# Lancer le chatbot
uv run python 04_agentic_chatbot.py
```

Accédez ensuite à `http://localhost:7861`

---

## 📁 Structure du Projet

```
haproxy-dataset-generator/
├── agentic_rag/          # ⭐ Système RAG Agentic (PRINCIPAL)
├── rag/                  # 📦 Système RAG Standard (ARCHIVE)
├── doc/                  # 📚 Documentation Technique
├── pyproject.toml        # Dépendances globales
└── README.md             # Ce fichier
```

---

## 🎯 Composants Principaux

### agentic_rag/ - Système RAG Agentic

Le système RAG agentic est l'implémentation **principale** et **recommandée** pour la production.

**Avantages :**
- ✅ Meilleure qualité : **0.914/1.0** (+5.3% vs RAG standard)
- ✅ Meilleure réussite : **92.4%** (+4.4% vs RAG standard)
- ✅ Architecture agentic avec LangGraph
- ✅ Chunking parent/child hiérarchique
- ✅ Hybrid retrieval (Vector + BM25 + RRF)
- ✅ Multi-step reasoning

**Documentation :** Voir [`agentic_rag/README_AGENTIC.md`](agentic_rag/README_AGENTIC.md)

### rag/ - Système RAG Standard (Archive)

Le dossier `rag/` contient l'implémentation **RAG standard** du projet.

**Objectif :**
- 📦 Maintenu comme **archive** pour comparaison
- 📚 Référence pour comprendre l'évolution du projet
- 🧪 Tests de régression et validation

**Performances :**
- Qualité : 0.846/1.0
- Réussite : 82%
- Temps : 22.4s

**Documentation :** Voir [`rag/README.md`](rag/README.md)

### doc/ - Documentation Technique

Le dossier `doc/` contient toute la documentation technique du projet :

- `GUIDE_COMPLET.md` : Guide complet du pipeline RAG standard
- `GUIDE_IMPLEMENTATION_AGENTIC.md` : Guide d'implémentation du RAG agentic
- `PIPELINE_RAG_GENERIC.md` : Guide générique RAG
- `V3_PERFORMANCE_TRACKING.md` : Historique des performances
- `plans/` : Plans et spécifications techniques

---

## 📖 Documentation

### Pour le système RAG Agentic (PRINCIPAL)

- **Guide complet :** [`agentic_rag/README_AGENTIC.md`](agentic_rag/README_AGENTIC.md)
- **Guide d'implémentation :** [`doc/GUIDE_IMPLEMENTATION_AGENTIC.md`](doc/GUIDE_IMPLEMENTATION_AGENTIC.md)
- **Architecture détaillée :** [`doc/plans/PLAN_AGENTIC_RAG_HAPROXY.md`](doc/plans/PLAN_AGENTIC_RAG_HAPROXY.md)

### Pour le système RAG Standard (ARCHIVE)

- **Guide complet :** [`rag/README.md`](rag/README.md)
- **Guide du pipeline :** [`doc/GUIDE_COMPLET.md`](doc/GUIDE_COMPLET.md)
- **Guide générique RAG :** [`doc/PIPELINE_RAG_GENERIC.md`](doc/PIPELINE_RAG_GENERIC.md)

### Documentation générale

- **Instructions pour les agents :** [`doc/AGENTS.md`](doc/AGENTS.md)
- **Apprentissage et découvertes :** [`doc/LEARNING.md`](doc/LEARNING.md)
- **Suivi des performances :** [`doc/V3_PERFORMANCE_TRACKING.md`](doc/V3_PERFORMANCE_TRACKING.md)

---

## ⚙️ Configuration

### Variables d'environnement principales

#### Ollama
- `OLLAMA_URL` - URL du serveur Ollama (défaut: `http://localhost:11434`)
- `EMBED_MODEL` - Modèle d'embedding (défaut: `qwen3-embedding:8b`)
- `LLM_MODEL` - Modèle LLM principal (défaut: `qwen3.5:9b`)

#### RAG Agentic
- `CHILD_CHUNK_SIZE` - Taille chunks enfants (défaut: `300`)
- `DEFAULT_K_CHILD` - Nombre de chunks enfants (défaut: `5`)
- `HYBRID_RETRIEVAL_ENABLED` - Activer hybrid retrieval (défaut: `true`)

#### RAG Standard
- `TOP_K_RETRIEVAL` - Candidats par méthode (défaut: `50`)
- `TOP_K_RRF` - Résultats après fusion RRF (défaut: `30`)
- `TOP_K_RERANK` - Résultats finaux (défaut: `10`)

---

## 🧪 Tests

### Tests RAG Agentic

```bash
cd agentic_rag
uv run pytest
```

### Benchmark RAG Agentic

```bash
cd agentic_rag
uv run python 05_bench_agentic.py --level quick
```

### Benchmark RAG Standard

```bash
cd rag
uv run python 05_bench_targeted.py --level quick
```

---

## 📝 License

Projet open-source pour la documentation HAProxy.

**Dernière mise à jour :** 2026-03-04
**Statut :** ✅ PRÊT POUR PRODUCTION (agentic_rag)
```

### Étape 7 : Vérifier la racine

**Fichiers qui doivent rester à la racine :**
- `.gitignore`
- `.python-version`
- `pyproject.toml`
- `README.md` (mis à jour)
- `skills-lock.json`
- `.agents/`
- `.kilocode/`
- `agentic_rag/`

**Fichiers qui ne doivent PAS être à la racine :**
- Tous les fichiers `.py` (sauf ceux dans les sous-dossiers)
- Tous les fichiers `.md` (sauf `README.md`)
- Tous les dossiers `app/`, `data/`, `index_v3/`, `plans/`

---

## 🔧 Imports à mettre à jour

Après le déplacement, les imports dans les fichiers de `rag/` devront peut-être être ajustés si ils référencent des modules déplacés.

**Imports à vérifier :**
- Imports relatifs dans les scripts de `rag/`
- Imports de `config.py` dans les scripts de `rag/`
- Imports de `llm.py`, `retriever_v3.py`, etc.

---

## ✅ Checklist de validation

- [ ] Dossier `rag/` créé avec sa structure
- [ ] Tous les scripts Python RAG standard déplacés dans `rag/`
- [ ] Répertoires `app/`, `data/`, `index_v3/` déplacés dans `rag/`
- [ ] Fichier `rag/README.md` créé
- [ ] Dossier `doc/` créé
- [ ] Tous les fichiers de documentation déplacés dans `doc/`
- [ ] Dossier `plans/` déplacé dans `doc/`
- [ ] Fichier `README.md` à la racine mis à jour
- [ ] Racine ne contient que : `.gitignore`, `.python-version`, `pyproject.toml`, `README.md`, `skills-lock.json`, `.agents/`, `.kilocode/`, `agentic_rag/`
- [ ] Imports dans les fichiers déplacés vérifiés et mis à jour si nécessaire

---

## 📊 Résumé

| Action | Nombre de fichiers/dossiers |
|--------|----------------------------|
| Scripts Python à déplacer | 21 |
| Répertoires à déplacer | 3 |
| Fichiers de documentation à déplacer | 11 |
| Dossier plans à déplacer | 1 |
| Nouveaux fichiers README | 2 |
| Fichiers à mettre à jour | 1 |

**Total :** 38 opérations de déplacement/création
