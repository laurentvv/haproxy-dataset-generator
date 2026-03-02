# HAProxy Dataset Generator - Project Context

## Project Overview

This project implements a **RAG (Retrieval-Augmented Generation) system** for HAProxy 3.2 documentation, featuring two parallel pipelines:

1. **Generic RAG Pipeline** (root directory) - Hybrid retrieval (vector + lexical) with reranking
2. **Agentic RAG Pipeline** (`agentic_rag/`) - LangGraph-based multi-agent system with parent/child chunking

**Tech Stack:**
- **Python**: 3.13+ (managed via `uv`)
- **LLM**: Ollama (qwen3:latest, gemma3:latest, qwen3-embedding:8b)
- **Vector DB**: ChromaDB
- **Lexical Search**: BM25
- **Reranking**: FlashRank
- **UI**: Gradio 6.8.0
- **Agent Framework**: LangGraph (agentic pipeline only)
- **Linting/Formatting**: ruff

## Key Performance Metrics

| Pipeline | Quality | Time/Query | Resolved | Status |
|----------|---------|------------|----------|--------|
| **V3 Generic** | 0.868/1.0 | ~24s | 88% | ✅ Production Ready |
| **Agentic RAG** | 0.796/1.0 | 11.46s | 68.5% | ⚠️ Needs Optimization |

## Project Structure

```
haproxy-dataset-generator/
├── # Main RAG Pipeline (Generic)
├── 00_rebuild_all.py         # Full pipeline orchestrator (~3h10)
├── 01_scrape.py              # Documentation scraping → data/sections.jsonl
├── 01b_enrich_metadata.py    # IA metadata enrichment → sections_enriched.jsonl
├── 02_chunking.py            # Semantic chunking → data/chunks_v2.jsonl
├── 03_indexing.py            # Index building (ChromaDB + BM25)
├── 04_chatbot.py             # Gradio chatbot (port 7861)
├── 05_bench_targeted.py      # Benchmark suite (quick/standard/full)
├── 06_bench_ollama.py        # LLM model comparison
├── 07_bench_config_correction.py  # Configuration correction benchmark
├── retriever_v3.py           # Hybrid retrieval V3 (vector + BM25 + RRF + FlashRank)
├── llm.py                    # LLM generation with streaming
├── config.py                 # Centralized configuration
│
├── # Agentic RAG Pipeline
├── agentic_rag/
│   ├── 00_rebuild_agentic.py       # Agentic pipeline orchestrator
│   ├── 01_scrape_verified.py       # Scraping with validation
│   ├── 02_chunking_parent_child.py # Parent/child hierarchical chunking
│   ├── 03_indexing_chroma.py       # ChromaDB indexing
│   ├── 04_agentic_chatbot.py       # LangGraph chatbot (port 7861)
│   ├── 05_bench_agentic.py         # Agentic benchmark
│   ├── rag_agent/                  # LangGraph module
│   ├── db/                         # Database management
│   ├── scraper/                    # Scraping tools
│   └── app/                        # Gradio UI
│
├── # Application (Modular Architecture)
├── app/
│   ├── main.py               # App entry point
│   ├── services/             # Business logic (RAG, LLM, Chat)
│   ├── state/                # State management
│   ├── ui/                   # Gradio UI components
│   └── utils/                # Utilities
│
├── # Data & Indexes
├── data/                     # Raw and processed data
├── index_v3/                 # V3 indexes (chroma/, bm25.pkl, chunks.pkl)
├── index_agentic/            # Agentic indexes
├── parent_store/             # Parent chunks JSON store
│
└── # Documentation
├── GUIDE_COMPLET.md          # Complete pipeline guide (French)
├── GUIDE_IMPLEMENTATION_AGENTIC.md  # Agentic implementation guide
├── PIPELINE_RAG_GENERIC.md   # Generic RAG guide
├── AGENTS.md                 # Agent instructions
├── LEARNING.md               # Project learnings (update before/after work)
└── V3_PERFORMANCE_TRACKING.md # Performance history
```

## Essential Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Install Ollama models (required)
ollama pull qwen3-embedding:8b    # Embeddings (MTEB 70.58)
ollama pull qwen3:latest          # LLM generation
ollama pull gemma3:latest         # Alternative LLM
ollama pull bge-m3                # Alternative embeddings
```

### Full Pipeline (Generic RAG)
```bash
# Rebuild everything (~3h10)
uv run python 00_rebuild_all.py --benchmark

# Individual steps:
uv run python 01_scrape.py              # Scraping (~5-10 min)
uv run python 01b_enrich_metadata.py    # Metadata enrichment (~5-10 min)
uv run python 02_chunking.py            # Chunking (~5 min)
uv run python 03_indexing.py            # Indexing (~2h with qwen3-embedding:8b)
```

### Chatbot
```bash
# Launch chatbot (Generic RAG V3)
uv run python 04_chatbot.py

# Launch agentic chatbot
cd agentic_rag && uv run python 04_agentic_chatbot.py
```

### Benchmarking
```bash
# Generic RAG benchmarks
uv run python 05_bench_targeted.py --level quick     # 7 questions, ~3 min
uv run python 05_bench_targeted.py --level standard  # 20 questions, ~8 min
uv run python 05_bench_targeted.py --level full      # 92 questions, ~45 min

# Agentic RAG benchmarks
cd agentic_rag && uv run python 05_bench_agentic.py --level full
```

### Code Quality
```bash
# Linting and formatting
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .

# Tests
uv run pytest
```

## Configuration

All configuration is centralized in `config.py` with environment variable overrides:

```python
# Ollama
OLLAMA_URL=http://localhost:11434
EMBED_MODEL=qwen3-embedding:8b
LLM_MODEL=gemma3:latest

# Retrieval
TOP_K_RETRIEVAL=50
TOP_K_RRF=30
TOP_K_RERANK=10
RRF_K=60

# Chunking
MIN_CHUNK_CHARS=300
MAX_CHUNK_CHARS=800
OVERLAP_CHARS=150
```

## Architecture Details

### Generic RAG Pipeline (V3)

**Retrieval Flow:**
```
User Query
    ↓
Query Expansion (synonyms)
    ↓
ChromaDB Search (Top-50 vector) + BM25 Search (Top-50 lexical)
    ↓
RRF Fusion (k=60) → Top-30
    ↓
FlashRank Rerank → Top-10
    ↓
Metadata Filtering (SECTION_HINTS)
    ↓
Keyword Boosting (IA keywords from gemma3)
    ↓
LLM Generation (qwen3:latest)
    ↓
Response with sources
```

**Key Files:**
- `retriever_v3.py`: Hybrid retrieval with RRF fusion and FlashRank reranking
- `llm.py`: Streaming LLM generation with strict prompt constraints
- `config.py`: All configurable parameters

### Agentic RAG Pipeline

**Architecture:**
- **Parent/Child Chunking**: Hierarchical chunks for better context
- **LangGraph**: Multi-agent orchestration with conversation memory
- **Tools**: `search_child_chunks`, `retrieve_parent_chunks`, `validate_config`

**Key Files:**
- `agentic_rag/rag_agent/graph.py`: LangGraph construction
- `agentic_rag/rag_agent/tools.py`: Agent tools
- `agentic_rag/config_agentic.py`: Agentic-specific configuration

## Development Practices

### Critical Rules (from AGENTS.md)
1. **Use `uv` exclusively** - No pip, no requirements.txt
2. **Stop at checkpoints** - Wait for explicit user approval before proceeding
3. **No secrets in code** - Use environment variables
4. **Update LEARNING.md** - Check before starting, update after discoveries (max 60 lines)

### Skills Directory
Specialized capabilities are in `.agents/skills/`:
- `gradio/` - Build Gradio web UIs and components

### Coding Style
- **Line length**: 100 characters (ruff)
- **Quotes**: Single quotes (ruff format)
- **Indentation**: Spaces
- **Type hints**: Use typing module for complex types

## Known Issues & Optimizations

### Current Limitations
1. **Agentic RAG quality** (0.796 vs 0.868 target) - Needs optimization
2. **stick_table retrieval** - Less performant than V2
3. **Backend/ACL questions** - Some edge cases < 0.70

### Backlog Optimizations
- Multi-Query Retrieval (+3% quality estimated)
- Query Expansion with LLM (+1.6% quality)
- Hybrid Score Tuning (+1% quality)
- Better RRF k parameter tuning

## Troubleshooting

### Ollama Issues
```bash
# Check models
ollama list

# Restart Ollama
ollama serve

# Reinstall model
ollama rm qwen3-embedding:8b
ollama pull qwen3-embedding:8b
```

### Index Issues
```bash
# Rebuild indexes
rm -rf index_v3/chroma/
uv run python 03_indexing.py
```

### ChromaDB Issues
```bash
# Clear cache
rm -rf index_v3/chroma/chroma.sqlite3
uv run python 03_indexing.py
```

## Documentation Resources

- **HAProxy 3.2 Docs**: https://docs.haproxy.org/3.2/
- **GUIDE_COMPLET.md**: Complete pipeline documentation (French)
- **V3_PERFORMANCE_TRACKING.md**: Performance history and benchmarks
- **LEARNING.md**: Project discoveries and insights (check before work)

## Quick Reference

| Task | Command | Duration |
|------|---------|----------|
| Full rebuild | `uv run python 00_rebuild_all.py` | ~3h10 |
| Scraping only | `uv run python 01_scrape.py` | ~5-10 min |
| Indexing | `uv run python 03_indexing.py` | ~2h |
| Chatbot | `uv run python 04_chatbot.py` | - |
| Quick benchmark | `uv run python 05_bench_targeted.py --level quick` | ~3 min |
| Full benchmark | `uv run python 05_bench_targeted.py --level full` | ~45 min |

---

**Last Updated**: 2026-03-02
**Project Status**: V3 Production Ready | Agentic RAG In Development
