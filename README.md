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

### 3. Construire l'index (30-60 min)
```bash
uv run python 03_build_index_v2.py
```

### 4. Lancer le chatbot
```bash
uv run python 04_app.py
# Ouvrir http://localhost:7860
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
├── 01_scrape.py          # Scraping HAProxy docs → Markdown
├── 02_ingest_v2.py       # Chunking intelligent + tags
├── 03_build_index_v2.py  # Build index ChromaDB + BM25
├── 04_app.py             # Interface Gradio
├── retriever.py          # Retrieval hybride (FAISS+BM25+RRF+Rerank)
├── llm.py                # Génération Ollama avec streaming
├── pyproject.toml        # Dépendances
├── data/                 # Données (sections, chunks)
└── index_v2/             # Index (ChromaDB, BM25, metadata)
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

| Composant | Technologie |
|-----------|-------------|
| **Embedding** | Ollama (bge-m3) |
| **Vector Index** | ChromaDB |
| **Lexical Index** | BM25 (rank-bm25) |
| **Reranking** | FlashRank (ms-marco-MiniLM-L-12-v2) |
| **LLM** | Ollama (gemma3:latest) |
| **UI** | Gradio 6.x |
| **Package Manager** | uv |

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

**Actuel :** `bge-m3` (MTEB: 67)

**Alternatives :**
- `mxbai-embed-large` (MTEB: 68) - Meilleur sur certains benchmarks
- `nomic-embed-text-v2-moe` - MoE architecture, multilingue

```bash
ollama pull mxbai-embed-large
# Modifier EMBED_MODEL dans 03_build_index_v2.py et retriever.py
```

**Gain attendu :** +3-5% sur la similarité sémantique

---

## 📊 Impact cumulé estimé

| Amélioration | Gain | Cumul |
|--------------|------|-------|
| Score actuel | - | 0.63 |
| Chunking thématique | +0.10 | 0.73 |
| Query rewriting | +0.05 | 0.78 |
| Fine-tuning LLM | +0.07 | 0.85 |
| Metadata filtering | +0.03 | 0.88 |

**Objectif réaliste : 0.80-0.85 (80-85% de questions résolues)**

---

## 📝 License

Projet open-source pour la documentation HAProxy.
