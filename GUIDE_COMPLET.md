# 📘 Guide Complet : Pipeline RAG HAProxy

**Version :** V3 (qwen3-embedding:8b, MTEB 70.58)  
**Date :** 2026-02-25  
**Statut :** ✅ Prêt pour production

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Étape 1 : Scraper la documentation](#etape-1-scraper-la-documentation)
4. [Étape 1.5 : Enrichir les metadata IA](#etape-15-enrichir-les-metadata-ia)
5. [Étape 2 : Parser et chunker](#etape-2-parser-et-chunker)
6. [Étape 3 : Construire l'index](#etape-3-construire-lindex)
7. [Étape 4 : Lancer le chatbot](#etape-4-lancer-le-chatbot)
8. [Étape 5 : Benchmarker](#etape-5-benchmarker)
9. [Architecture technique](#architecture-technique)
10. [Dépannage](#depannage)

---

## 🎯 Vue d'ensemble

Ce projet implémente un **chatbot RAG (Retrieval-Augmented Generation)** pour la documentation HAProxy 3.2.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE RAG COMPLET                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  docs.haproxy.org                                               │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐  Scrapping  →  data/sections.jsonl            │
│  │ 01_scrape.py│                                                │
│  └─────────────┘                                                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐  Enrichissement  →  data/sections_enrichies.jsonl │
│  │01b_enrich_meta  │  IA (gemma3)     │  (keywords, synonyms,    │
│  └─────────────────┘                  │   category, summary)     │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐  Chunking   →  data/chunks_v2.jsonl           │
│  │02_chunking  │              + propagation metadata IA        │
│  └─────────────┘                                                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐  Indexing   →  index_v3/                      │
│  │03_indexing  │              - chroma/ (embeddings)           │
│  │.py          │              - bm25.pkl (lexical)             │
│  └─────────────┘              - chunks.pkl (metadata)          │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐  RAG Chat   →  Gradio UI                      │
│  │ 04_chatbot  │              - Retrieval hybride              │
│  └─────────────┘              - LLM (qwen3:latest)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Prérequis

### **Système**
- **OS :** Windows 10/11, Linux, macOS
- **Python :** 3.11+
- **RAM :** 16GB minimum (32GB recommandé)
- **Stockage :** 10GB libre

### **Logiciels**

#### 1. **uv** (package manager)
```bash
# Windows/Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Vérifier
uv --version
```

#### 2. **Ollama** (LLM local)
```bash
# Télécharger : https://ollama.com

# Installer les modèles
ollama pull qwen3-embedding:8b    # Embedding (MTEB #1)
ollama pull qwen3:latest          # LLM (génération)
ollama pull bge-m3                # Embedding alternatif (V2)
ollama pull gemma3:latest         # LLM alternatif

# Vérifier
ollama list
ollama serve
```

---

## 📥 Installation

```bash
# 1. Cloner le repo
git clone <repo-url>
cd haproxy-dataset-generator

# 2. Créer l'environnement virtuel
uv sync

# 3. Vérifier les modèles Ollama
ollama list
# Doit afficher : qwen3-embedding:8b, qwen3:latest
```

---

## Étape 1 : Scraper la documentation

**Objectif :** Télécharger la documentation HAProxy en Markdown.

### **Execution**

```bash
uv run python 01_scrape.py
```

### **Ce que ça fait :**
- Télécharge les pages de https://docs.haproxy.org/3.2/
- Convertit le HTML en Markdown
- Nettoie le contenu (headers, footers, pubs)
- Sauvegarde dans `data/sections.jsonl`

### **Sortie attendue :**
```
2026-02-25 10:00:00 - INFO - Scraping HAProxy 3.2 documentation...
2026-02-25 10:05:00 - INFO - ✅ 150 sections scrapées
2026-02-25 10:05:00 - INFO - 📁 data/sections.jsonl (2.5 MB)
```

### **Contenu de `data/sections.jsonl` :**
```json
{"id": "section_5.2", "title": "5.2. Server and default-server options", "content": "...", "url": "https://docs.haproxy.org/3.2/configuration.html#5.2"}
{"id": "section_4.2", "title": "4.2. Alphabetically sorted keywords reference", "content": "...", "url": "https://docs.haproxy.org/3.2/configuration.html#4.2"}
...
```

### **Durée :** ~5-10 minutes

---

## Étape 1.5 : Enrichir les metadata IA

**Objectif :** Générer des métadonnées sémantiques pour chaque section via IA.

### **Execution**

```bash
uv run python 01b_enrich_metadata.py
```

### **Ce que ça fait :**
- Lit `data/sections.jsonl`
- Pour chaque section, appelle gemma3:latest pour générer :
  - `keywords` (5-10 mots-clés techniques présents dans le texte)
  - `synonyms` (3-5 termes associés, variantes)
  - `summary` (1 phrase résumé)
  - `category` (backend/frontend/acl/ssl/timeout/healthcheck/stick-table/logs/stats/general/loadbalancing)
- Sauvegarde dans `data/sections_enriched.jsonl`

### **Sortie attendue :**
```
[INFO] 150 sections chargees depuis data/sections.jsonl
[INFO] Modele IA: gemma3:latest
[INFO] Temps estime: ~5 min (150 sections x 2s)

[1/150] 5.2. Server and default-server options... OK 8 keywords | backend
[2/150] 4.2. Alphabetically sorted keywords reference... OK 7 keywords | general
...

[SUCCESS] ENRICHISSEMENT TERMINE
[INFO] Sections enrichies: 150
[INFO] Keywords totaux: 1050 (7.0/section)
[INFO] Categories:
   backend: 45 (30%)
   general: 30 (20%)
   acl: 25 (17%)
   ...
```

### **Contenu de `data/sections_enriched.jsonl` :**
```json
{
  "id": "section_5.2",
  "title": "5.2. Server and default-server options",
  "content": "...",
  "url": "https://docs.haproxy.org/3.2/configuration.html#5.2",
  "metadata": {
    "keywords": ["server", "backend", "weight", "check", "option httpchk", "inter", "fall", "rise"],
    "synonyms": ["désactiver", "disabled", "down", "inactive"],
    "summary": "Configuration des serveurs backend et options de health check HTTP.",
    "category": "backend"
  }
}
...
```

### **Durée :** ~5-10 minutes (gemma3:latest)

---

## Étape 2 : Parser et chunker

**Objectif :** Découper la documentation en chunks intelligents avec propagation des metadata IA.

### **Execution**

```bash
uv run python 02_chunking.py
```

### **Ce que ça fait :**
- Lit `data/sections_enriched.jsonl` (avec metadata IA)
- Découpe en chunks de ~300-800 caractères (chunking sémantique)
- Propage les metadata IA aux chunks (ia_keywords, ia_synonyms, ia_category, ia_summary)
- Ajoute des metadata HAProxy (tags, keywords, section hierarchy)
- Sauvegarde dans `data/chunks_v2.jsonl`

### **Sortie attendue :**
```
[INFO] 150 sections enrichies chargees depuis data/sections_enriched.jsonl
   Apres fusion : 180 sections
[INFO] Resultat re-chunking V2:
   Chunks totaux     : 3645
   Avec code         : 2121 (58%)
   Taille moy.       : 669 chars
   Min / Max         : 150 / 1200
   Tags HAProxy      : 10935 (3.0/chunk)
   Avec metadata IA  : 3645 (100%)
   IA keywords tot.  : 25515 (7.0/chunk)

[SUCCESS] 3645 chunks sauvegardes dans data/chunks_v2.jsonl
```

### **Contenu de `data/chunks_v2.jsonl` :**
```json
{
  "id": "chunk_0",
  "title": "5.2. Server and default-server options",
  "content": "option httpchk - Enable HTTP protocol to check server health...",
  "embed_text": "5.2. Server and default-server options\n\noption httpchk...",
  "url": "https://docs.haproxy.org/3.2/configuration.html#5.2",
  "source": "configuration",
  "parent_section": "5",
  "current_section": "5.2",
  "tags": ["healthcheck", "httpchk", "server", "option"],
  "keywords": ["healthcheck", "httpchk", "server", "option", "backend", "weight"],
  "has_code": true,
  "char_len": 669,
  "ia_keywords": ["server", "backend", "weight", "check", "option httpchk", "inter", "fall", "rise"],
  "ia_synonyms": ["désactiver", "disabled", "down", "inactive"],
  "ia_category": "backend",
  "ia_summary": "Configuration des serveurs backend et options de health check HTTP."
}
...
```

### **Durée :** ~5 minutes

---

## Étape 3 : Construire l'index

**Objectif :** Créer les index vectoriels et lexicaux avec metadata IA.

### **Execution**

```bash
uv run python 03_indexing.py
```

### **Ce que ça fait :**
- Charge `data/chunks_v2.jsonl` (3645 chunks avec metadata IA)
- Génère les embeddings avec `qwen3-embedding:8b` (4096 dims)
- Crée l'index ChromaDB (vectoriel) avec metadata :
  - `ia_keywords` : Keywords IA de gemma3:latest
  - `ia_synonyms` : Synonymes IA
  - `ia_category` : Catégorie IA
  - `ia_summary` : Résumé IA
  - `keywords` : Keywords combines (HAProxy + IA)
  - `tags` : Tags HAProxy
- Crée l'index BM25 (lexical)
- Sauvegarde les metadata

### **Sortie attendue :**
```
2026-02-25 10:20:00 - INFO - ============================================================
2026-02-25 10:20:00 - INFO - 🔍 Indexation V3 - HAProxy RAG
2026-02-25 10:20:00 - INFO - ============================================================
2026-02-25 10:20:00 - INFO - 📂 3645 chunks charges depuis data/chunks_v2.jsonl
2026-02-25 10:20:00 - INFO - ✅ Ollama OK - Modele: qwen3-embedding:8b
2026-02-25 10:20:00 - INFO -
📦 Indexation de 3645 chunks...
2026-02-25 10:20:00 - INFO -    Progression: 500/3645 (13%) | ETA: ~104 min
2026-02-25 10:20:00 - INFO -    Progression: 1000/3645 (27%) | ETA: ~88 min
...
2026-02-25 12:31:22 - INFO -    Progression: 3645/3645 (100%) | ETA: ~0 min
2026-02-25 12:31:22 - INFO - ✅ Index BM25 sauvegarde: index_v3/bm25.pkl
2026-02-25 12:31:22 - INFO - ✅ Chunks sauvegardes: index_v3/chunks.pkl
2026-02-25 12:31:22 - INFO -
✅ Index V3 termine !
   Collection ChromaDB: haproxy_docs_v3
   Nombre de chunks: 3645
   Dimensions embedding: 4096
```
```

### **Fichiers générés :**
```
index_v3/
├── chroma/           # Index vectoriel ChromaDB
│   ├── chroma.sqlite3
│   └── ...
├── bm25.pkl          # Index lexical BM25
└── chunks.pkl        # Metadata des chunks
```

### **Durée :** ~2 heures (135 min)

---

## Étape 4 : Lancer le chatbot

**Objectif :** Interface Gradio pour poser des questions.

### **Execution**

```bash
uv run python 04_chatbot.py
```

### **Ce que ça fait :**
- Charge les index V3 (ChromaDB + BM25)
- Lance un serveur Gradio
- Interface web pour poser des questions
- Retrieval hybride (vectoriel + lexical + rerank)
- Génération de réponse avec `qwen3:latest`
- Utilise les metadata IA pour le keyword boosting

### **Sortie attendue :**
```
2026-02-25 13:00:00 - INFO - Importation des modules V3 (qwen3-embedding:8b)...
2026-02-25 13:00:00 - INFO - ✅ Module retriever_v3 importé avec succès
2026-02-25 13:00:00 - INFO - ✅ Module llm importé avec succès
2026-02-25 13:00:00 - INFO - Modèle par défaut: qwen3:latest
2026-02-25 13:00:00 - INFO - Tentative de chargement des index V3...
2026-02-25 13:00:01 - INFO - ✅ Index V3 chargés avec succès (qwen3-embedding:8b)
2026-02-25 13:00:01 - INFO - Starting Gradio server...
* Running on local URL: http://localhost:7860
```

### **Interface :**
- **URL :** http://localhost:7860
- **Fonctionnalités :**
  - Chat avec historique
  - Affichage des sources
  - Exemples de questions
  - Toggle "Montrer les sources"

### **Exemples de questions :**
- "Comment configurer un health check HTTP ?"
- "Syntaxe de la directive bind ?"
- "Comment limiter les connexions par IP ?"
- "Comment utiliser les ACLs ?"
- "Options de timeout disponibles ?"

---

## Étape 5 : Benchmarker

**Objectif :** Mesurer la performance du RAG.

### **Niveaux de benchmark**

#### **Quick (7 questions, ~3 min)**
```bash
uv run python 05_bench_targeted.py --level quick
```

#### **Standard (20 questions, ~8 min)**
```bash
uv run python 05_bench_targeted.py --level standard
```

#### **Full (92 questions, ~45 min)**
```bash
uv run python 05_bench_targeted.py --level full
```

### **Benchmark ciblé (questions spécifiques)**
```bash
# Tester des questions spécifiques
uv run python 05_bench_targeted.py --questions full_backend_name,full_acl_status
```

### **Comparaison V2 vs V3**
```bash
# Script supprimé - utiliser 05_bench_targeted.py directement
uv run python 05_bench_targeted.py --level full
```

### **Benchmark des modèles LLM**
```bash
uv run python 06_bench_ollama.py --all
```

### **Résultats attendus (Full 100 questions) :**
```
======================================================================
📈 RÉSULTATS BENCHMARK V3
======================================================================

🎯 Modèle LLM: qwen3:latest
📝 Questions: 100
   Index: index_v3/ (qwen3-embedding:8b, MTEB 70.58)

----------------------------------------------------------------------
Métrique                       | Valeur
----------------------------------------------------------------------
Qualité moyenne                | 0.846          /1.0
Taux de réussite (>0.7)        | 82.0           %
Questions résolues             : 82/100
Temps de retrieval moy.        : 6.84           s
Temps de génération moy.       : 15.58          s
Temps total                    : 2241.90        s
Tokens moy.                    : 504.1
----------------------------------------------------------------------

======================================================================
💡 INTERPRÉTATION
======================================================================
✅ TRÈS BON - Qualité >= 0.80/1.0
✅ 82.0% des questions résolues (objectif >= 80%)
```

---

## 🏗️ Architecture technique

### **Pipeline de retrieval**

```
Question utilisateur
       │
       ▼
┌─────────────────────┐
│  Query Expansion    │  Ajoute synonymes techniques
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  ChromaDB Search    │  Top-50 vectoriel (cosine)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  BM25 Search        │  Top-50 lexical
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  RRF Fusion         │  Combine les 2 scores
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  FlashRank Rerank   │  Top-10 avec cross-encoder
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Metadata Filtering │  Filtre par section (optionnel)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Keyword Boosting   │  Booste les chunks avec keywords
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  LLM Generation     │  qwen3:latest avec contexte
└─────────────────────┘
       │
       ▼
Réponse finale avec sources
```

### **Configurations clés**

#### **`retriever_v3.py`**
```python
TOP_K_RETRIEVAL      = 50  # Candidats par méthode
TOP_K_RRF            = 30  # Après fusion RRF
TOP_K_RERANK         = 10  # Après reranking
RRF_K                = 60  # Paramètre RRF
CONFIDENCE_THRESHOLD = 0.0  # Seuil de confiance
```

#### **Metadata Filtering**
```python
SECTION_HINTS = {
    "stick-table": ["11.1", "11.2", "7.3", "11.3"],
    "acl": ["7.1", "7.2", "7.3", "7.4", "7.5", "8.1", "8.2"],
    "backend": ["5.1", "5.2", "5.3", "4.1", "4.3", "3.1"],
    "ssl": ["4.2", "5.1", "5.3", "3.1", "4.1"],
    ...
}
```

---

## 🔧 Dépannage

### **Problème : Ollama inaccessible**
```bash
# Vérifier qu'Ollama tourne
ollama serve

# Vérifier les modèles
ollama list

# Réinstaller un modèle
ollama rm qwen3-embedding:8b
ollama pull qwen3-embedding:8b
```

### **Problème : Index manquants**
```bash
# Reconstruire l'index
uv run python 03_indexing.py

# Ou supprimer et reconstruire
rm -rf index_v3/
uv run python 03_indexing.py
```

### **Problème : ChromaDB error**
```bash
# Supprimer le cache ChromaDB
rm -rf index_v3/chroma/chroma.sqlite3

# Reconstruire
uv run python 03_build_index_v3.py
```

### **Problème : Gradio ne démarre pas**
```bash
# Vérifier les dépendances
uv sync

# Réinstaller Gradio
uv add gradio
```

### **Problème : Qualité faible**
```bash
# Vérifier le retrieval sur des questions spécifiques
uv run python 05_bench_targeted.py --questions full_backend_name,full_acl_status --verbose

# Ajuster SECTION_HINTS dans retriever_v3.py
# Reconstruire l'index si nécessaire
```

---

## 📊 Performance attendue

| Métrique | Valeur | Objectif |
|----------|--------|----------|
| Qualité moyenne | 0.846/1.0 | 0.80+ ✅ |
| Questions résolues | 82% | 80%+ ✅ |
| Temps/requête | 22.4s | <25s ✅ |
| Chunks indexés | 3645 | - |
| Taille index | ~500 MB | - |

---

## 📁 Structure des fichiers

```
haproxy-dataset-generator/
├── 00_rebuild_all.py         # ⭐ Script unique - Reconstruit tout
├── 01_scrape.py              # Scrapping → sections.jsonl
├── 01b_enrich_metadata.py    # Enrichissement IA → sections_enriched.jsonl
├── 02_chunking.py            # Chunking + propagation metadata → chunks_v2.jsonl
├── 03_indexing.py            # Indexing → index_v3/
├── 04_chatbot.py             # Chatbot Gradio
├── retriever_v3.py           # Retrieval hybride V3
├── llm.py                    # Génération LLM
├── bench_questions.py        # 92 questions de benchmark
├── 05_bench_targeted.py      # Benchmark (quick/standard/full)
├── 06_bench_ollama.py        # Benchmark modèles LLM
├── V3_PERFORMANCE_TRACKING.md# Historique des perfs
├── data/                     # Données brutes
│   ├── sections.jsonl
│   ├── sections_enriched.jsonl
│   └── chunks_v2.jsonl
└── index_v3/                 # Index construits
    ├── chroma/
    ├── bm25.pkl
    └── chunks.pkl
```

---

## 🚀 Commandes rapides

```bash
# Installation
uv sync
ollama pull qwen3-embedding:8b
ollama pull qwen3:latest
ollama pull gemma3:latest         # Pour l'enrichissement metadata

# Reconstruction complète (~3h10)
uv run python 00_rebuild_all.py

# Ou étapes individuelles :

# Scrapping (~5-10 min)
uv run python 01_scrape.py

# Enrichissement metadata IA (~5-10 min)
uv run python 01b_enrich_metadata.py

# Chunking (~5-10 min)
uv run python 02_chunking.py

# Indexing (~2h)
uv run python 03_indexing.py

# Chatbot
uv run python 04_chatbot.py

# Benchmark Quick (3 min)
uv run python 05_bench_targeted.py --level quick

# Benchmark Full (45 min)
uv run python 05_bench_targeted.py --level full
```

---

## 📚 Ressources

- [HAProxy 3.2 Docs](https://docs.haproxy.org/3.2/)
- [Ollama](https://ollama.com)
- [ChromaDB](https://docs.trychroma.com/)
- [FlashRank](https://github.com/PrithivirajDamodaran/FlashRank)
- [Qwen3 Embedding](https://ollama.com/library/qwen3-embedding:8b)

---

**Dernière mise à jour :** 2026-02-25  
**Version :** V3 (qwen3-embedding:8b, MTEB 70.58)  
**Statut :** ✅ Prêt pour production
