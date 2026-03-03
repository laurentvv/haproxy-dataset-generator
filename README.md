# HAProxy Documentation Chatbot - RAG Hybride

Chatbot RAG (Retrieval-Augmented Generation) sur la documentation HAProxy 3.2, utilisant une approche hybride vectorielle + lexicale avec reranking.

## 📚 Documentation

Pour le guide complet d'installation et d'utilisation, consultez [GUIDE_COMPLET.md](GUIDE_COMPLET.md).

## 🚀 Installation Rapide

```bash
# Installer les dépendances
uv sync

# Installer les modèles Ollama
ollama pull qwen3-embedding:8b
ollama pull qwen3.5:9b

# Reconstruire tout le pipeline (~3h)
uv run python 00_rebuild_all.py

# Lancer le chatbot
uv run python 04_chatbot.py
```

## ⚙️ Configuration

Le projet utilise une configuration centralisée via le module [`config.py`](config.py:1). Toutes les configurations peuvent être surchargées par des variables d'environnement.

### Variables d'environnement principales

#### Ollama
- `OLLAMA_URL` - URL du serveur Ollama (défaut: `http://localhost:11434`)
- `EMBED_MODEL` - Modèle d'embedding (défaut: `qwen3-embedding:8b`)
- `LLM_MODEL` - Modèle LLM principal (défaut: `qwen3.5:9b`)
- `FAST_MODEL` - Modèle rapide (défaut: `lfm2.5-thinking:1.2b-bf16`)
- `ENRICH_MODEL` - Modèle d'enrichissement (défaut: `qwen3.5:9b`)

#### Retrieval
- `TOP_K_RETRIEVAL` - Candidats par méthode (défaut: `50`)
- `TOP_K_RRF` - Résultats après fusion RRF (défaut: `30`)
- `TOP_K_RERANK` - Résultats finaux (défaut: `10`)
- `RRF_K` - Paramètre RRF (défaut: `60`)
- `DISABLE_FLASHRANK` - Désactiver FlashRank (défaut: `false`)

#### Boosting
- `TITLE_BOOST` - Boost pour les titres (défaut: `2.0`)
- `SECTION_BOOST` - Boost pour les sections (défaut: `1.5`)
- `CONTENT_BOOST` - Boost pour le contenu (défaut: `1.0`)
- `MAX_BOOST` - Maximum de boost (défaut: `3.0`)

#### Reranker
- `RERANKER_ENABLED` - Activer le reranking (défaut: `true`)
- `RERANKER_TOP_K` - Nombre de résultats à reranker (défaut: `10`)

#### Chunking
- `MIN_CHUNK_CHARS` - Taille minimale chunk (défaut: `300`)
- `MAX_CHUNK_CHARS` - Taille maximale chunk (défaut: `800`)
- `OVERLAP_CHARS` - Overlap entre chunks (défaut: `150`)

#### LLM
- `DEFAULT_MODEL` - Modèle par défaut (défaut: `qwen3.5:9b`)
- `MAX_CONTEXT_CHARS` - Limite contexte (défaut: `4000`)
- `LLM_TEMPERATURE` - Température (défaut: `0.1`)

### Exemples de configuration

#### Utiliser un modèle LLM différent
```bash
# Linux/Mac
export LLM_MODEL="gemma3:latest"
uv run python 04_chatbot.py

# Windows (PowerShell)
$env:LLM_MODEL="gemma3:latest"
uv run python 04_chatbot.py

# Windows (cmd)
set LLM_MODEL=gemma3:latest
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

Pour plus de détails sur la configuration, consultez le [Guide Complet](GUIDE_COMPLET.md#⚙️-configuration-centralisée).

## 📖 Structure du Projet

- `00_rebuild_all.py` - Script unique de reconstruction complète
- `01_scrape.py` - Scrapping de la documentation
- `01b_enrich_metadata.py` - Enrichissement IA des métadonnées
- `02_chunking.py` - Chunking intelligent
- `03_indexing.py` - Construction des index
- `04_chatbot.py` - Interface Gradio du chatbot
- `retriever_v3.py` - Retrieval hybride V3
- `llm.py` - Génération LLM
- `app/` - Application Gradio refactorisée
- `data/` - Données brutes et traitées
- `index_v3/` - Index vectoriels et lexicaux

## 📊 Performance

- Qualité moyenne : 0.846/1.0
- Questions résolues : 82%
- Temps de réponse moyen : 22.4s

## 📄 Documentation Complète

- [GUIDE_COMPLET.md](GUIDE_COMPLET.md) - Guide complet du pipeline
- [PIPELINE_RAG_GENERIC.md](PIPELINE_RAG_GENERIC.md) - Guide générique RAG
- [AGENTS.md](AGENTS.md) - Instructions pour les agents

## 📝 License

Projet open-source pour la documentation HAProxy.
