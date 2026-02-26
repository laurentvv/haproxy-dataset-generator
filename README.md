# HAProxy Documentation Chatbot - RAG Hybride

Chatbot RAG (Retrieval-Augmented Generation) sur la documentation HAProxy 3.2, utilisant une approche hybride vectorielle + lexicale avec reranking.

---

## 🚀 Installation

### Prérequis
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- [Ollama](https://ollama.com) (LLM local)

### Setup

```bash
# 1. Installer les dépendances
uv sync

# 2. Installer les modèles Ollama
ollama pull bge-m3          # Embedding (MTEB SOTA)
ollama pull gemma3:latest   # LLM (défaut)
```

---

## 📋 Pipeline RAG

```
docs.haproxy.org
      │
      ▼
01_scrape.py ─────────────► data/sections.jsonl
      │
      ▼
02_ingest_v2.py ──────────► data/chunks_v2.jsonl
      │
      ▼
03_build_index_v2.py ─────► index_v2/chroma/
                            index_v2/bm25.pkl
                            index_v2/chunks.pkl
      │
      ├──────────────┬──────────────────┐
      ▼              ▼                  ▼
retriever.py   (FAISS+BM25         04_app.py
(Hybrid)       +RRF+Rerank)         (Gradio UI)
      │
      ▼
llm.py (Ollama streaming)
```

---

## 🔧 Commandes

### 1. Scraper la documentation
```bash
uv run python 01_scrape.py
```

### 2. Chunking intelligent
```bash
uv run python 02_ingest_v2.py
```

### 3. Construire l'index

**Index V2 (bge-m3, rapide) :**
```bash
uv run python 03_build_index_v2.py
# ~30-60 min | bge-m3 (MTEB 67) | 1024 dims
```

**Index V3 (qwen3-embedding:8b, SOTA) :**
```bash
uv run python 03_build_index_v3.py
# ~60-120 min | qwen3-embedding:8b (MTEB 70.58) | 4096 dims
```

### 4. Lancer le chatbot

**Avec index V2 (bge-m3) :**
```bash
uv run python 04_app.py
```

**Avec index V3 (qwen3-embedding:8b) :**
```bash
uv run python 04_app_v3.py  # (à créer ou modifier pour utiliser retriever_v3)
```

---

## 📊 Architecture de retrieval

| Étape | Technologie | Top-K |
|-------|-------------|-------|
| Vector search | ChromaDB (bge-m3) | 50 |
| Lexical search | BM25 | 50 |
| Fusion | RRF (Reciprocal Rank Fusion) | 25 |
| Reranking | FlashRank (ms-marco-MiniLM) | 5 |

---

## ⚙️ Configuration

### Changer le modèle LLM

Dans `llm.py` :
```python
DEFAULT_MODEL = "gemma3:latest"  # ou qwen3:latest, llama3.1:8b
```

### Changer le modèle d'embedding

Dans `03_build_index_v2.py` et `retriever.py` :
```python
EMBED_MODEL = "bge-m3"  # ou mxbai-embed-large
```

### Ajuster le retrieval

Dans `retriever.py` :
```python
TOP_K_RETRIEVAL = 50    # Candidats par méthode
TOP_K_RRF       = 25    # Après fusion RRF
TOP_K_RERANK    = 5     # Résultats finaux
```

---

## 📁 Structure des fichiers

```
├── 01_scrape.py              # Scraping HAProxy docs → Markdown
├── 02_ingest_v2.py           # Chunking intelligent + tags
├── 03_build_index_v2.py      # Build index V2 (bge-m3)
├── 03_build_index_v3.py      # Build index V3 (qwen3-embedding:8b)
├── 04_app.py                 # Interface Gradio V2 (bge-m3)
├── 04_app_v3.py              # Interface Gradio V3 (qwen3-embedding:8b)
├── retriever.py              # Retrieval V2 (bge-m3)
├── retriever_v3.py           # Retrieval V3 (qwen3-embedding:8b)
├── llm.py                    # Génération Ollama avec streaming
├── 06_bench_ollama.py        # Benchmark de modèles Ollama
├── bench_questions.py        # Base de questions (92 questions)
├── pyproject.toml            # Dépendances
├── data/                     # Données (sections, chunks)
├── index_v2/                 # Index V2 (bge-m3)
└── index_v3/                 # Index V3 (qwen3-embedding:8b)
```

---

## 🎯 Qualité de retrieval

| Métrique | Score |
|----------|-------|
| Score moyen (benchmark) | 0.63/1.0 |
| Questions résolues | 4/6 (67%) |
| Embedding | bge-m3 (MTEB: 67) |
| Chunks | 3645 (taille moy: 669 chars) |

---

## 💡 Exemples de questions

✅ **Bien fonctionner :**
- "Comment configurer un health check HTTP ?"
- "Syntaxe de la directive bind ?"
- "Options de timeout disponibles ?"
- "Configurer SSL/TLS sur un frontend ?"
- "Comment limiter les connexions par IP ?"

⚠️ **Partiel :**
- "Comment utiliser les ACLs ?" (réponse partielle)

---

## 🛠️ Technologies

| Composant | Technologie V2 | Technologie V3 |
|-----------|----------------|----------------|
| **Embedding** | Ollama (bge-m3) | **Ollama (qwen3-embedding:8b)** |
| **MTEB Score** | 67 | **70.58 (#1 mondial)** |
| **Dimension** | 1024 | **4096** |
| **Contexte** | 8K tokens | **40K tokens** |
| **Vector Index** | ChromaDB | ChromaDB |
| **Lexical Index** | BM25 (rank-bm25) | BM25 (rank-bm25) |
| **Reranking** | FlashRank (ms-marco-MiniLM) | FlashRank (ms-marco-MiniLM) |
| **LLM** | Ollama (gemma3:latest) | Ollama (gemma3:latest) |
| **UI** | Gradio 6.x | Gradio 6.x |
| **Package Manager** | uv | uv |

---

## 📚 Documentation

- [HAProxy 3.2 Docs](https://docs.haproxy.org/3.2/)
- [Ollama](https://ollama.com)
- [ChromaDB](https://docs.trychroma.com/)
- [FlashRank](https://github.com/PrithivirajDamodaran/FlashRank)
- [MODELE_CONFIG.md](MODELE_CONFIG.md) - Configuration détaillée des modèles

---

## 🚀 Améliorations futures

### Objectif : Passer de 0.63 à 0.80+ de score moyen

Actuellement **67% de questions résolues (4/6)**. Voici les pistes pour atteindre **80%+** :

---

### 1. Chunking thématique HAProxy

**Problème :** Les sections sur `stick-table`, `ACLs` et `http-request` sont dispersées dans plusieurs chunks.

**Solution :** Regrouper par concept HAProxy au lieu de découper par taille.

```python
# Dans 02_ingest_v2.py
# Fusionner les chunks d'une même section thématique
THEMATIC_SECTIONS = {
    "stick-table": ["7.3", "11.1", "11.2"],  # Sections à fusionner
    "acl": ["7.1", "7.2", "7.4"],
    "http-request": ["4.2", "7.3"],
}
```

**Gain attendu :** +10-15% sur les questions rate limiting et ACLs

---

### 2. HyDE (Hypothetical Document Embeddings)

**Idée :** Générer une réponse hypothétique avec le LLM, puis l'embedder pour améliorer le retrieval.

```python
# Avant le retrieval
hypothetical_answer = llm.generate(
    f"Réponds brièvement à: {query}",
    context=""  # Pas de contexte, juste la connaissance du modèle
)
query_embedding = get_embedding(hypothetical_answer)
```

**Gain attendu :** +5-10% sur la précision du retrieval vectoriel

---

### 3. Query Rewriting avec LLM

**Idée :** Reformuler la question utilisateur pour inclure les termes techniques HAProxy.

```python
# Exemple de transformation
"Comment bloquer une IP avec trop de requêtes ?"
→ "stick-table type ip store http_req_rate track-sc0 deny 429"

def rewrite_query(query: str) -> str:
    prompt = f"""Reformule cette question pour un moteur de recherche HAProxy.
    Utilise les termes techniques précis (directives, keywords).
    
    Question: {query}
    
    Termes techniques:"""
    return ollama.generate(prompt)
```

**Gain attendu :** +10% sur la compréhension des questions utilisateurs

---

### 4. Fine-tuning du LLM

**Idée :** Fine-tuner `gemma3:latest` sur des QA HAProxy pour qu'il apprenne :
- Le format de réponse attendu
- Les directives HAProxy importantes
- À ne pas halluciner hors du contexte

**Dataset :** Générer 1000+ paires QA avec `07_generate_qa.py`

```bash
# Générer le dataset
uv run python 07_generate_qa.py

# Fine-tuner (Ollama ou Unsloth)
ollama finetune gemma3:latest --data qa_dataset.jsonl
```

**Gain attendu :** +15-20% sur la qualité des réponses (moins d'hallucinations)

---

### 5. Metadata Filtering avancé

**Idée :** Utiliser les tags et sections pour filtrer avant le retrieval.

```python
# Dans retriever.py
# Extraire les tags de la query
query_tags = extract_tags(query)  # ["stick-table", "rate-limit"]

# Filtrer ChromaDB par tags
results = chroma_collection.query(
    query_embeddings=[query_emb],
    where={"tags": {"$contains": "stick-table"}}
)
```

**Gain attendu :** +5% sur la précision du retrieval

---

### 6. Multi-query retrieval

**Idée :** Poser 3 variations de la question et fusionner les résultats.

```python
# Générer 3 variations
variations = llm.generate(f"""
Génère 3 reformulations techniques de cette question:
{query}
""")

# Retrieval sur chaque variation
all_chunks = []
for variation in variations:
    chunks = retrieve(variation)
    all_chunks.extend(chunks)

# Dédupliquer et reranker
final_chunks = rerank(all_chunks)[:5]
```

**Gain attendu :** +5-8% sur le recall

---

### 7. Changer d'embedding

**V2 :** `bge-m3` (MTEB: 67)

**V3 :** `qwen3-embedding:8b` (MTEB: 70.58 - #1 mondial) ✅

**Alternatives :**
- `mxbai-embed-large` (MTEB: 68) - Meilleur sur certains benchmarks
- `nomic-embed-text-v2-moe` - MoE architecture, multilingue

```bash
ollama pull qwen3-embedding:8b
# Déjà utilisé dans 03_build_index_v3.py et retriever_v3.py
```

**Gain V2 → V3 :** +8% sur la qualité de retrieval (0.63 → 0.68)

---

## 📊 Impact cumulé estimé

| Amélioration | Gain | Cumul |
|--------------|------|-------|
| Score V2 (bge-m3) | - | 0.63 |
| **Score V3 (qwen3-embedding:8b)** | **+0.05** | **0.68** ✅ |
| Chunking thématique | +0.10 | 0.78 |
| Query rewriting | +0.05 | 0.83 |
| Fine-tuning LLM | +0.07 | 0.90 |
| Metadata filtering | +0.03 | 0.93 |

**Objectif V3 + optimisations : 0.85-0.90 (85-90% de questions résolues)**

---

## 🧪 Benchmark des modèles Ollama

Un script de benchmark est inclus pour comparer les modèles Ollama :

```bash
uv run python 06_bench_ollama.py --all
```

### Résultats du benchmark (5 modèles testés)

| Rang | Modèle | Qualité | Vitesse | Temps | Recommandation |
|------|--------|---------|---------|-------|----------------|
| 🥇 | **gemma3:latest** | **0.96/1.0** | 50.6 tok/s | 8s | ✅ **MEILLEUR** |
| 🥇 | gemma3n:latest | 0.96/1.0 | 20.8 tok/s | 24s | ⚠️ Lent |
| 🥇 | qwen3:latest | 0.96/1.0 | 8.7 tok/s | 92s | ⚠️ Très lent |
| 4️⃣ | lfm2.5-thinking:1.2b-bf16 | 0.72/1.0 | **83.8 tok/s** | 8s | ⚡ Rapide |
| 5️⃣ | Nanbeige4.1-3B-GGUF | 0.20/1.0 | 35.8 tok/s | 29s | ❌ À éviter |

### 🏆 Recommandations

| Catégorie | Modèle | Pourquoi |
|-----------|--------|----------|
| ✅ **Meilleure qualité** | `gemma3:latest` | 0.96/1.0 + rapide (50 tok/s) |
| ⚡ **Meilleure vitesse** | `lfm2.5-thinking:1.2b-bf16` | 83.8 tok/s + correct (0.72) |
| 🎯 **Meilleur compromis** | **`gemma3:latest`** | Qualité max + vitesse correcte |

### ⚠️ Modèles à éviter

- **Nanbeige4.1-3B-GGUF** : Qualité 0.20/1.0 (réponses vides)
- **qwen3:latest** : Très lent (92s vs 8s pour gemma3)

---

## 📝 License

Projet open-source pour la documentation HAProxy.
