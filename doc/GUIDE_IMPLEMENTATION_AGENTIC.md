# Guide d'Implémentation Complet - Système RAG Agentic HAProxy 3.2

Ce guide fournit des instructions détaillées pour installer, configurer et déployer le système RAG agentic pour la documentation HAProxy 3.2.

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Pipeline de Données](#pipeline-de-données)
6. [Lancement du Chatbot](#lancement-du-chatbot)
7. [Tests](#tests)
8. [Dépannage](#dépannage)
9. [Architecture](#architecture)
10. [Métriques et Performance](#métriques-et-performance)

---

## Vue d'ensemble

Le système RAG agentic HAProxy 3.2 est un assistant intelligent basé sur la documentation officielle HAProxy 3.2. Il utilise:

- **LangGraph** pour l'orchestration de l'agent
- **ChromaDB** pour le stockage vectoriel
- **Ollama** pour les embeddings et le LLM
- **Gradio 6.6.0** pour l'interface utilisateur
- **Stratégie parent/child** pour le chunking

### Architecture

```
Documentation HAProxy 3.2 (Web)
    ↓ Scraping
Pages avec hiérarchie (data_agentic/scraped_pages.json)
    ↓ Analyse hiérarchie
Rapport parent/child (data_agentic/hierarchy_report.json)
    ↓ Chunking
Parents (parent_store/*.json) + Children (data_agentic/chunks_child.json)
    ↓ Indexation
Vector Store ChromaDB (index_agentic/chroma_db/)
    ↓ Agent LangGraph
Outils: search_child_chunks, retrieve_parent_chunks, validate_haproxy_config
    ↓ Chatbot Gradio
Interface utilisateur sur port 7861
```

---

## Prérequis

### Système
- Windows 10/11, macOS, ou Linux
- Python 3.11 ou supérieur
- 8 Go RAM minimum (16 Go recommandé)
- 10 Go d'espace disque libre

### Logiciels requis

#### 1. Python 3.11+
```bash
# Vérifier la version de Python
python --version

# Si Python n'est pas installé, télécharger depuis:
# https://www.python.org/downloads/
```

#### 2. uv (Gestionnaire de paquets Python)
```bash
# Installer uv
pip install uv

# Vérifier l'installation
uv --version
```

#### 3. Ollama (LLM et Embeddings)
```bash
# Télécharger Ollama depuis:
# https://ollama.com/download

# Installer Ollama (Windows)
# Exécuter le fichier .msi téléchargé

# Vérifier l'installation
ollama --version
```

#### 4. Modèles Ollama requis
```bash
# Pull le modèle LLM
ollama pull qwen3:latest

# Pull le modèle d'embeddings
ollama pull qwen3-embedding:8b

# Vérifier les modèles installés
ollama list
```

---

## Installation

### 1. Cloner le repository
```bash
# Si ce n'est pas déjà fait
cd c:/GIT/fork/haproxy-dataset-generator
```

### 2. Installer les dépendances Python
```bash
# Naviguer dans le répertoire du système agentic
cd agentic_rag

# Installer les dépendances avec uv
uv sync

# Vérifier l'installation
uv pip list
```

### 3. Vérifier la structure du projet
```bash
# La structure devrait ressembler à:
agentic_rag/
├── __init__.py
├── 00_rebuild_agentic.py
├── 01_scrape_verified.py
├── 02_chunking_parent_child.py
├── 03_indexing_chroma.py
├── 04_agentic_chatbot.py
├── config_agentic.py
├── pyproject_agentic.toml
├── README_AGENTIC.md
├── app/
├── rag_agent/
├── db/
├── scraper/
├── tests/
├── data_agentic/
├── index_agentic/
└── parent_store/
```

---

## Configuration

### 1. Configuration Ollama

Vérifier que Ollama est en cours d'exécution:
```bash
# Démarrer Ollama (si nécessaire)
ollama serve
```

### 2. Configuration du système

Le fichier [`config_agentic.py`](agentic_rag/config_agentic.py) contient toutes les configurations. Les valeurs par défaut sont généralement suffisantes.

Paramètres clés:
```python
# Modèles
LLM_MODEL = "qwen3:latest"
EMBEDDING_MODEL = "qwen3-embedding:8b"

# Chunking
CHILD_CHUNK_SIZE = 500
CHILD_CHUNK_OVERLAP = 80
MIN_PARENT_SIZE = 100
MAX_PARENT_SIZE = 4000

# Retrieval
DEFAULT_K_CHILD = 5
DEFAULT_K_MMR = 5
MMR_FETCH_K = 20
SCORE_THRESHOLD = 0.7

# Gradio
SERVER_PORT = 7861
```

### 3. Personnalisation (optionnel)

Si vous souhaitez modifier la configuration:
```bash
# Éditer le fichier de configuration
code agentic_rag/config_agentic.py
```

---

## Pipeline de Données

Le pipeline de données se compose de 3 phases principales:

### Phase 1: Scraping + Validation

Scrape la documentation HAProxy 3.2 et valide les résultats.

```bash
# Exécuter la phase 1
cd agentic_rag
uv run python 01_scrape_verified.py
```

**Sortie attendue:**
```
=== Phase 1: Scraping + Validation ===

1. Scraping des pages HAProxy 3.2...
✓ Scrapé X pages

2. Analyse de la hiérarchie...
✓ Rapport de hiérarchie généré

3. Comparaison avec le projet principal...
✓ Couverture: 98.5%

✓ Phase 1 terminée avec succès!
  - Pages scrapées: X
  - Couverture: 98.5%

Validation humaine requise avant de passer à Phase 2.
```

**Fichiers générés:**
- `data_agentic/scraped_pages.json` - Pages scrapées
- `data_agentic/hierarchy_report.json` - Rapport de hiérarchie
- `data_agentic/scraping_diff_report.json` - Rapport de comparaison

### Phase 2: Chunking Parent/Child

Effectue le chunking hiérarchique parent/child.

```bash
# Exécuter la phase 2
uv run python 02_chunking_parent_child.py
```

**Sortie attendue:**
```
=== Phase 2: Chunking Parent/Child ===

1. Chargement des données scrapées...
✓ X pages chargées

2. Chunking hiérarchique...
✓ X parents créés
✓ X enfants créés

3. Sauvegarde des chunks enfants...
✓ Chunks sauvegardés dans data_agentic/chunks_child.json

=== Statistiques ===
Parents - Taille moyenne: 1500 chars
Parents - Min: 100, Max: 4000
Children - Taille moyenne: 500 chars
Children - Min: 100, Max: 800

✓ Phase 2 terminée avec succès!
```

**Fichiers générés:**
- `parent_store/*.json` - Chunks parents
- `data_agentic/chunks_child.json` - Chunks enfants

### Phase 3: Indexation ChromaDB

Indexe les chunks dans ChromaDB.

```bash
# Exécuter la phase 3
uv run python 03_indexing_chroma.py
```

**Sortie attendue:**
```
=== Phase 3: Indexation ChromaDB ===

1. Chargement des chunks enfants...
✓ X chunks chargés

2. Initialisation des embeddings (qwen3-embedding:8b)...
✓ Embeddings initialisés

3. Initialisation de ChromaDB...
✓ Collection créée

4. Nettoyage de la collection existante...
✓ Collection créée

5. Création des documents LangChain...
✓ X documents créés

6. Indexation des documents...
✓ Documents indexés

7. Vérification de l'indexation...
✓ X documents dans la collection

8. Test de recherche...
✓ 3 résultats pour la requête de test

✓ Phase 3 terminée avec succès!
  - Documents indexés: X
  - Collection: haproxy_child_chunks
  - Chemin: index_agentic/chroma_db/
```

**Fichiers générés:**
- `index_agentic/chroma_db/` - Base de données vectorielle ChromaDB

### Pipeline complet

Pour exécuter tout le pipeline en une fois:

```bash
# Exécuter tout le pipeline
uv run python 00_rebuild_agentic.py
```

Le pipeline vous demandera une confirmation avant chaque phase.

---

## Lancement du Chatbot

Une fois le pipeline terminé, lancez le chatbot:

```bash
# Lancer le chatbot
uv run python 04_agentic_chatbot.py
```

**Sortie attendue:**
```
=== HAProxy 3.2 Agentic RAG Chatbot ===
Port: 7861
Démarrage de l'interface Gradio...

Running on local URL:  http://0.0.0.0:7861

To create a public link, set `share=True` in `launch()`.
```

### Accéder au chatbot

Ouvrez votre navigateur et accédez à:
```
http://localhost:7861
```

### Utilisation du chatbot

1. Posez une question sur HAProxy 3.2
2. L'agent analysera votre question
3. Il utilisera les outils de retrieval pour trouver les informations pertinentes
4. Il vous fournira une réponse avec les sources citées

**Exemples de questions:**
- "Comment configurer un frontend dans HAProxy ?"
- "Quels sont les paramètres globaux de HAProxy ?"
- "Comment activer SSL dans HAProxy ?"
- "Qu'est-ce qu'un backend dans HAProxy ?"

---

## Tests

### Exécuter tous les tests

```bash
# Exécuter tous les tests
uv run pytest

# Avec sortie détaillée
uv run pytest -v

# Avec couverture de code
uv run pytest --cov=agentic_rag --cov-report=html
```

### Tests individuels

```bash
# Tests du scraper
uv run pytest agentic_rag/tests/test_scraper_alignment.py -v

# Tests du chunking
uv run pytest agentic_rag/tests/test_chunking.py -v

# Tests du retrieval
uv run pytest agentic_rag/tests/test_retrieval.py -v

# Tests du graphe
uv run pytest agentic_rag/tests/test_graph_flow.py -v

# Tests E2E
uv run pytest agentic_rag/tests/test_end_to_end.py -v
```

### Résultats attendus

Tous les tests devraient passer (27 tests):
```
======================== test session starts =========================
collected 27 items

tests/test_scraper_alignment.py .....                          [ 18%]
tests/test_chunking.py .....                                  [ 37%]
tests/test_retrieval.py .....                                 [ 55%]
tests/test_graph_flow.py .......                               [ 81%]
tests/test_end_to_end.py .....                                [100%]

========================= 27 passed in X.XXs =========================
```

---

## Dépannage

### Problème: Ollama n'est pas accessible

**Symptôme:**
```
ConnectionError: Cannot connect to Ollama server
```

**Solution:**
```bash
# Vérifier si Ollama est en cours d'exécution
ollama ps

# Démarrer Ollama
ollama serve

# Dans un autre terminal, vérifier
curl http://localhost:11434/api/tags
```

### Problème: Modèle Ollama non trouvé

**Symptôme:**
```
Error: model 'qwen3:latest' not found
```

**Solution:**
```bash
# Pull le modèle manquant
ollama pull qwen3:latest
ollama pull qwen3-embedding:8b

# Vérifier les modèles installés
ollama list
```

### Problème: ChromaDB ne peut pas créer la collection

**Symptôme:**
```
Error: Cannot create collection
```

**Solution:**
```bash
# Supprimer le dossier ChromaDB existant
rm -rf agentic_rag/index_agentic/chroma_db/

# Relancer l'indexation
uv run python 03_indexing_chroma.py
```

### Problème: Le chatbot ne démarre pas

**Symptôme:**
```
Error: Port 7861 already in use
```

**Solution:**
```bash
# Changer le port dans config_agentic.py
# SERVER_PORT = 7862

# Ou arrêter le processus utilisant le port 7861
# Sur Windows:
netstat -ano | findstr :7861
taskkill /PID <PID> /F
```

### Problème: Tests échouent

**Symptôme:**
```
FAILED tests/test_retrieval.py::test_chroma_manager_delete_collection
```

**Solution:**
```bash
# Nettoyer les fichiers temporaires
rm -rf agentic_rag/.ruff_cache/
rm -rf agentic_rag/index_agentic/chroma_db/

# Relancer les tests
uv run pytest
```

---

## Architecture

### Composants principaux

#### 1. Module `rag_agent/` (LangGraph)

- **graph.py**: Construction du graphe LangGraph
- **graph_state.py**: État du graphe (State)
- **nodes.py**: Nœuds du graphe (summarize, analyze, agent, human_input)
- **edges.py**: Routing conditionnel
- **tools.py**: Outils de retrieval (search_child_chunks, retrieve_parent_chunks, validate_haproxy_config)
- **schemas.py**: Schémas Pydantic v2
- **prompts.py**: Prompts système

#### 2. Module `db/` (Bases de données)

- **chroma_manager.py**: Gestion ChromaDB
- **parent_store_manager.py**: Gestion JSON store des parents

#### 3. Module `scraper/` (Scraping)

- **haproxy_scraper.py**: Scraper HAProxy docs
- **html_structure_analyzer.py**: Analyse hiérarchie HTML
- **compare_with_reference.py**: Comparaison vs projet principal

#### 4. Module `app/` (Interface utilisateur)

- **rag_system.py**: Système RAG agentic
- **chat_interface.py**: Interface de chat Gradio
- **gradio_app.py**: Application Gradio
- **document_manager.py**: Gestionnaire de documents

#### 5. Scripts de pipeline

- **00_rebuild_agentic.py**: Orchestrateur principal
- **01_scrape_verified.py**: Scraping + validation
- **02_chunking_parent_child.py**: Chunking hiérarchique
- **03_indexing_chroma.py**: Indexation ChromaDB
- **04_agentic_chatbot.py**: Chatbot Gradio

### Flux de données

```
User Question
    ↓
Gradio ChatInterface
    ↓
AgenticRAGSystem.query()
    ↓
LangGraph State
    ↓
Nodes: summarize → analyze → human_input → agent
    ↓
Tools: search_child_chunks → retrieve_parent_chunks → validate_haproxy_config
    ↓
ChromaDB (similarity_search / MMR)
    ↓
ParentStore (load_parent)
    ↓
Response with sources
    ↓
Gradio Chatbot
```

---

## Métriques et Performance

### Métriques de qualité

```python
METRICS = {
    "answer_quality_score": "Score 0-1 évalué par LLM judge",
    "retrieval_precision": "% chunks pertinents (évaluation manuelle)",
    "parent_child_utilization_rate": "% réponses utilisant chunk parent",
    "clarification_rate": "% questions déclenchant human-in-the-loop",
    "response_time_p50_sec": "Médiane temps de réponse",
    "response_time_p95_sec": "95e percentile",
    "source_citation_rate": "% réponses avec citation de section"
}
```

### Paramètres de performance

```python
# Chunking
CHILD_CHUNK_SIZE = 500        # Taille chunks enfants
CHILD_CHUNK_OVERLAP = 80      # Chevauchement
MIN_PARENT_SIZE = 100         # Taille minimale parent
MAX_PARENT_SIZE = 4000        # Taille maximale parent

# Retrieval
SCORE_THRESHOLD = 0.7         # Distance cosine
DEFAULT_K_CHILD = 5           # Nombre de chunks enfants
DEFAULT_K_MMR = 5             # Nombre de résultats MMR
MMR_FETCH_K = 20              # Pool pour diversification MMR
```

### Exigences de qualité

- **Couverture parent/child**: >= 90%
- **Couverture contenu vs projet principal**: >= 95%
- **Taille parents**: 90% dans [100, 4000] chars
- **Taille children**: 90% dans [100, 800] chars
- **Tests**: 100% PASS avant passage à phase suivante

---

## Commandes Rapides

### Installation
```bash
cd agentic_rag
uv sync
```

### Pipeline complet
```bash
uv run python 00_rebuild_agentic.py
```

### Chatbot
```bash
uv run python 04_agentic_chatbot.py
```

### Tests
```bash
uv run pytest -v
```

### Formatage
```bash
uv run ruff check --fix .
uv run ruff format .
```

---

## Ressources

- [Documentation HAProxy 3.2](https://docs.haproxy.org/3.2/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Gradio Documentation](https://www.gradio.app/docs)
- [Ollama Documentation](https://ollama.com/docs)

---

## Support

Pour toute question ou problème:
1. Consultez ce guide
2. Vérifiez les logs dans la console
3. Consultez la documentation officielle des composants

---

**Version**: 1.0.0  
**Date**: 2025-02-28  
**Auteur**: Kilo Code
