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

## ⚙️ Configuration Centralisée

Le projet utilise une configuration centralisée via le module [`config.py`](config.py:1) qui sert de **source unique de vérité** pour tous les paramètres configurables.

### Structure de la configuration

La configuration est organisée en **dataclasses** pour une meilleure lisibilité et maintenabilité :

#### [`OllamaConfig`](config.py:14) - Configuration Ollama
```python
@dataclass
class OllamaConfig:
    url: str = "http://localhost:11434"           # URL du serveur Ollama
    embed_model: str = "qwen3-embedding:8b"        # Modèle d'embedding
    llm_model: str = "qwen3.5:9b"                  # Modèle LLM principal
    fast_model: str = "lfm2.5-thinking:1.2b-bf16"  # Modèle rapide
    enrich_model: str = "qwen3.5:9b"               # Modèle d'enrichissement
    timeout: int = 120                              # Timeout par défaut
    llm_timeout: int = 300                          # Timeout LLM
    max_retries: int = 3                            # Nombre de tentatives
    rate_limit_calls_per_minute: int = 30          # Rate limiting
```

#### [`RetrievalConfig`](config.py:29) - Configuration du retrieval hybride
```python
@dataclass
class RetrievalConfig:
    top_k_retrieval: int = 50      # Candidats par méthode (vector + BM25)
    top_k_rrf: int = 30            # Résultats après fusion RRF
    top_k_rerank: int = 10         # Résultats finaux après reranking
    rrf_k: int = 60                # Paramètre RRF
    confidence_threshold: float = 0.0  # Seuil de confiance
    disable_flashrank: bool = False  # Désactiver FlashRank
```

#### [`BoostingConfig`](config.py:52) - Configuration du boosting IA metadata
```python
@dataclass
class BoostingConfig:
    title_boost: float = 2.0        # Boost pour les titres
    section_boost: float = 1.5      # Boost pour les sections
    content_boost: float = 1.0      # Boost pour le contenu
    example_boost: float = 1.2     # Boost pour les exemples
    warning_boost: float = 1.3     # Boost pour les avertissements
    metadata_boost: float = 0.8     # Boost pour les metadata
    max_boost: float = 3.0         # Maximum de boost appliqué
```

#### [`RerankerConfig`](config.py:68) - Configuration du reranking
```python
@dataclass
class RerankerConfig:
    enabled: bool = True           # Activer/désactiver le reranking
    top_k: int = 10                # Nombre de résultats à reranker
```

#### [`BenchmarkConfig`](config.py:79) - Configuration des benchmarks
```python
@dataclass
class BenchmarkConfig:
    default_benchmark_models: list[str] = ["qwen3.5:9b", "gemma3:latest"]
    quick_test_questions: int = 5  # Questions pour test rapide
    full_test_questions: int = 50  # Questions pour test complet
```

#### [`ChunkingConfig`](config.py:97) - Configuration du chunking
```python
@dataclass
class ChunkingConfig:
    min_chunk_chars: int = 300     # Taille minimale d'un chunk
    max_chunk_chars: int = 800     # Taille maximale d'un chunk
    overlap_chars: int = 150      # Overlap entre chunks
    merge_threshold: int = 500     # Seuil pour fusionner sections courtes
```

#### [`IndexConfig`](config.py:114) - Configuration de l'indexation
```python
@dataclass
class IndexConfig:
    base_dir: Path = Path.cwd()    # Répertoire de base
    data_dir: Path = "data"        # Répertoire des données
    index_dir: Path = "index_v3"   # Répertoire des index
    chroma_collection: str = "haproxy_docs_v3"  # Collection ChromaDB
    batch_size: int = 100          # Batch size pour l'embedding
```

#### [`LLMConfig`](config.py:147) - Configuration de la génération LLM
```python
@dataclass
class LLMConfig:
    default_model: str = "qwen3.5:9b"  # Modèle par défaut
    max_context_chars: int = 4000      # Limite de contexte
    temperature: float = 0.1            # Température (faible = factuel)
    rate_limit_calls_per_minute: int = 20  # Rate limiting
```

#### [`ValidationConfig`](config.py:164) - Configuration de la validation
```python
@dataclass
class ValidationConfig:
    max_query_length: int = 2000           # Longueur max des requêtes
    max_metadata_length: int = 500         # Longueur max des metadata
    max_metadata_items: int = 20           # Nombre max d'items
    max_metadata_item_length: int = 100   # Longueur max par item
```

#### [`LoggingConfig`](config.py:181) - Configuration du logging
```python
@dataclass
class LoggingConfig:
    log_level: str = "INFO"      # Niveau de log
    log_file: str = ""           # Fichier de log (vide = stdout)
```

### Variables d'environnement

Toutes les configurations peuvent être surchargées via des variables d'environnement :

#### Ollama
- `OLLAMA_URL` - URL du serveur Ollama (défaut: `http://localhost:11434`)
- `EMBED_MODEL` - Modèle d'embedding (défaut: `qwen3-embedding:8b`)
- `LLM_MODEL` - Modèle LLM principal (défaut: `qwen3.5:9b`)
- `FAST_MODEL` - Modèle rapide (défaut: `lfm2.5-thinking:1.2b-bf16`)
- `ENRICH_MODEL` - Modèle d'enrichissement (défaut: `qwen3.5:9b`)
- `OLLAMA_TIMEOUT` - Timeout par défaut en secondes (défaut: `120`)
- `LLM_TIMEOUT` - Timeout LLM en secondes (défaut: `300`)
- `OLLAMA_MAX_RETRIES` - Nombre de tentatives (défaut: `3`)
- `OLLAMA_RATE_LIMIT` - Rate limiting calls/min (défaut: `30`)

#### Retrieval
- `TOP_K_RETRIEVAL` - Candidats par méthode (défaut: `50`)
- `TOP_K_RRF` - Résultats après fusion RRF (défaut: `30`)
- `TOP_K_RERANK` - Résultats finaux (défaut: `10`)
- `RRF_K` - Paramètre RRF (défaut: `60`)
- `CONFIDENCE_THRESHOLD` - Seuil de confiance (défaut: `0.0`)
- `DISABLE_FLASHRANK` - Désactiver FlashRank (défaut: `false`)

#### Boosting
- `TITLE_BOOST` - Boost pour les titres (défaut: `2.0`)
- `SECTION_BOOST` - Boost pour les sections (défaut: `1.5`)
- `CONTENT_BOOST` - Boost pour le contenu (défaut: `1.0`)
- `EXAMPLE_BOOST` - Boost pour les exemples (défaut: `1.2`)
- `WARNING_BOOST` - Boost pour les avertissements (défaut: `1.3`)
- `METADATA_BOOST` - Boost pour les metadata (défaut: `0.8`)
- `MAX_BOOST` - Maximum de boost (défaut: `3.0`)

#### Reranker
- `RERANKER_ENABLED` - Activer le reranking (défaut: `true`)
- `RERANKER_TOP_K` - Nombre de résultats à reranker (défaut: `10`)

#### Benchmark
- `DEFAULT_BENCHMARK_MODELS` - Modèles par défaut (défaut: `qwen3.5:9b,gemma3:latest`)
- `QUICK_TEST_QUESTIONS` - Questions test rapide (défaut: `5`)
- `FULL_TEST_QUESTIONS` - Questions test complet (défaut: `50`)

#### Chunking
- `MIN_CHUNK_CHARS` - Taille minimale chunk (défaut: `300`)
- `MAX_CHUNK_CHARS` - Taille maximale chunk (défaut: `800`)
- `OVERLAP_CHARS` - Overlap entre chunks (défaut: `150`)
- `MERGE_THRESHOLD` - Seuil fusion sections (défaut: `500`)

#### Index
- `HAPROXY_RAG_BASE_DIR` - Répertoire de base (défaut: répertoire courant)
- `DATA_DIR` - Répertoire des données (défaut: `data`)
- `INDEX_DIR` - Répertoire des index (défaut: `index_v3`)
- `CHROMA_COLLECTION` - Collection ChromaDB (défaut: `haproxy_docs_v3`)
- `CHUNKS_FILE` - Fichier des chunks (défaut: `chunks_v2.jsonl`)
- `BM25_FILE` - Fichier BM25 (défaut: `bm25.pkl`)
- `CHUNKS_PKL` - Fichier chunks.pkl (défaut: `chunks.pkl`)
- `EMBED_BATCH_SIZE` - Batch size embedding (défaut: `100`)

#### LLM
- `DEFAULT_MODEL` - Modèle par défaut (défaut: `qwen3.5:9b`)
- `MAX_CONTEXT_CHARS` - Limite contexte (défaut: `4000`)
- `LLM_TEMPERATURE` - Température (défaut: `0.1`)
- `LLM_RATE_LIMIT` - Rate limiting calls/min (défaut: `20`)

#### Validation
- `MAX_QUERY_LENGTH` - Longueur max requête (défaut: `2000`)
- `MAX_METADATA_LENGTH` - Longueur max metadata (défaut: `500`)
- `MAX_METADATA_ITEMS` - Nombre max items (défaut: `20`)
- `MAX_METADATA_ITEM_LENGTH` - Longueur max item (défaut: `100`)

#### Logging
- `LOG_LEVEL` - Niveau de log (défaut: `INFO`)
- `LOG_FILE` - Fichier de log (défaut: vide = stdout)

### Méthodes utilitaires

#### [`get_model_config(model_type, use_fast=False)`](config.py:219)
Retourne le modèle approprié selon le type demandé.

```python
from config import get_model_config

# Récupérer le modèle LLM
llm_model = get_model_config("llm")  # "qwen3.5:9b"

# Récupérer le modèle rapide
fast_model = get_model_config("llm", use_fast=True)  # "lfm2.5-thinking:1.2b-bf16"

# Récupérer le modèle d'embedding
embed_model = get_model_config("embedding")  # "qwen3-embedding:8b"

# Récupérer le modèle d'enrichissement
enrich_model = get_model_config("enrichment")  # "qwen3.5:9b"
```

#### [`validate_model_availability(model_name)`](config.py:250)
Vérifie la disponibilité d'un modèle dans Ollama.

```python
from config import validate_model_availability

if validate_model_availability("qwen3.5:9b"):
    print("Le modèle est disponible")
else:
    print("Le modèle n'est pas disponible")
```

#### [`get_available_models(exclude_embeddings=True)`](config.py:274)
Liste les modèles disponibles dans Ollama.

```python
from config import get_available_models

# Lister tous les modèles LLM (exclut les embeddings)
models = get_available_models(exclude_embeddings=True)
print(f"Modèles disponibles: {models}")

# Lister tous les modèles (y compris les embeddings)
all_models = get_available_models(exclude_embeddings=False)
print(f"Tous les modèles: {all_models}")
```

### Validation de la configuration

Le script [`config_validator.py`](config_validator.py:1) permet de valider la configuration :

```bash
uv run python config_validator.py
```

Ce script vérifie :
- La connexion à Ollama
- La disponibilité des modèles configurés
- La cohérence des configurations
- Affiche un résumé complet de toutes les configurations

### Exemples d'utilisation

#### Utiliser un modèle LLM différent
```bash
# Via variable d'environnement
export LLM_MODEL="gemma3:latest"
uv run python 04_chatbot.py
```

#### Désactiver le reranking
```bash
export RERANKER_ENABLED="false"
uv run python 04_chatbot.py
```

#### Ajuster les paramètres de retrieval
```bash
export TOP_K_RETRIEVAL="100"
export TOP_K_RRF="50"
export TOP_K_RERANK="20"
uv run python 04_chatbot.py
```

#### Utiliser un modèle d'embedding différent
```bash
export EMBED_MODEL="bge-m3"
uv run python 03_indexing.py
```

### Aliases pour compatibilité ascendante

Pour maintenir la compatibilité avec le code existant, des aliases sont fournis :

```python
from config import (
    OLLAMA_URL,           # ollama_config.url
    EMBED_MODEL,          # ollama_config.embed_model
    DEFAULT_MODEL,        # llm_config.default_model
    TOP_K_RETRIEVAL,      # retrieval_config.top_k_retrieval
    TOP_K_RRF,            # retrieval_config.top_k_rrf
    TOP_K_RERANK,         # retrieval_config.top_k_rerank
    RRF_K,                # retrieval_config.rrf_k
    CONFIDENCE_THRESHOLD, # retrieval_config.confidence_threshold
)
```

**Note :** Ces aliases sont marqués pour dépréciation. Il est recommandé d'utiliser directement les instances de dataclasses dans le nouveau code.

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
