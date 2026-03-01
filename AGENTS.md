# AGENTS.md

## Project

HAProxy dataset generator with RAG system and configuration benchmarking. The project includes two pipelines: a generic RAG pipeline (root) and an agentic RAG pipeline (in `agentic_rag/` folder).

## Tech stack

- **Python**: 3.13.12
- **Dependency manager**: `uv` (replaces pip)
- **UI framework**: Gradio 6.6.0
- **Linting/Formatting**: ruff (>=0.15.2)
- **Vector DB**: ChromaDB
- **Agent framework**: LangGraph (for agentic pipeline)

## Project structure

```
├── agentic_rag/          # Agentic RAG pipeline with LangGraph
│   ├── app/              # Gradio applications (chatbot, evaluator)
│   ├── db/               # ChromaDB and parent store management
│   ├── rag_agent/        # LangGraph graph (nodes, edges, tools)
│   └── scraper/          # HAProxy scraping
├── app/                  # Generic RAG pipeline (Gradio)
├── index_v3/             # ChromaDB index for generic pipeline
└── data/                 # Raw and enriched data
```

## Essential commands

**Install dependencies**:
```bash
uv sync
```

**Start development server**:
```bash
uv run python 04_chatbot.py              # Generic pipeline
uv run python agentic_rag/04_agentic_chatbot.py  # Agentic pipeline
```

**Run tests**:
```bash
uv run pytest
```

**Format code** (mandatory after any modification):
```bash
uv run ruff check --fix .
uv run ruff format .
```

## Development workflow

1. Modify Python files
2. Format with ruff (mandatory before commit)
3. Test locally with Gradio server
4. Commit only after ruff validation

## Critical rules

### Resource Management

- **Never execute a Python script without verifying that no other script is currently running**. This rule is critical to avoid resource conflicts when loading Ollama models into memory. Multiple scripts loading models simultaneously can cause:
  - Memory exhaustion
  - Model loading failures
  - Inconsistent benchmark results
  - Port conflicts (typically port 11434 for Ollama)

- **Never execute a Python script without verifying that no models are loaded in 'ollama ps'**. This ensures accurate benchmark and performance measurements. Running benchmarks with pre-loaded models will:
  - Skew performance metrics (inflated speed)
  - Provide misleading memory usage data
  - Compromise result reproducibility

### Code Quality

- **Code style is managed automatically by ruff** (configured in `pyproject.toml`). Do not include manual style rules. Always run:
  ```bash
  uv run ruff check --fix .
  uv run ruff format .
  ```
  Before committing any changes.

## Additional documentation

- `GUIDE_COMPLET.md`: Complete documentation of the generic pipeline
- `GUIDE_IMPLEMENTATION_AGENTIC.md`: Implementation guide for the agentic pipeline
- `plans/PLAN_AGENTIC_RAG_HAPROXY.md`: Detailed architecture of the agentic system
- `agentic_rag/README_AGENTIC.md`: Specifics of the agentic pipeline
