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
ollama pull qwen3:latest

# Reconstruire tout le pipeline (~3h)
uv run python 00_rebuild_all.py

# Lancer le chatbot
uv run python 04_chatbot.py
```

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
