# HAProxy Agentic RAG System

Système RAG Agentic pour la documentation HAProxy utilisant LangGraph.

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

### Installation du modèle Ollama

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
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

1. **Scraper**: Extraction et validation de la documentation HAProxy
2. **Chunking**: Division hiérarchique en chunks parents et enfants
3. **Indexation**: Stockage vectoriel dans ChromaDB
4. **Agent LangGraph**: Orchestration agentic de la récupération
5. **Chatbot**: Interface Gradio pour l'interaction utilisateur

### Flux de données

```
Documentation HAProxy
    ↓
Scraper (validation)
    ↓
Chunking parent/child
    ↓
Indexation ChromaDB
    ↓
Agent LangGraph (retrieval + refinement)
    ↓
Chatbot Gradio
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

## Licence

Ce projet fait partie du projet haproxy-dataset-generator.
