# AGENTS.md

## Project

HAProxy dataset generator with RAG system and configuration benchmarking. The project includes two pipelines: a generic RAG pipeline (root) and an agentic RAG pipeline (in `agentic_rag/` folder).

## Tech stack

- **Python**: 3.13.12
- **Dependency manager**: `uv` (replaces pip)
- **UI framework**: Gradio 6.6.0
- **Linting/Formatting**: ruff
- **Vector DB**: ChromaDB
- **Agent framework**: LangGraph (for agentic pipeline)

## HOW TO WORK
### Essential Commands
- Python Management: Use uv exclusively (e.g., uv add <pkg>). No pip, no requirements.txt.

### Critical Rules
- Behavior: STOP at each CHECKPOINT and wait for explicit user approval.
- Security: No secrets in source code. Use process.env or os.environ.
- Reliability: Check LEARNING.md before starting and update it with new discoveries after.

## ARCHITECTURE & NAVIGATION

- `GUIDE_COMPLET.md`: Complete documentation of the generic pipeline
- `GUIDE_IMPLEMENTATION_AGENTIC.md`: Implementation guide for the agentic pipeline
- `plans/PLAN_AGENTIC_RAG_HAPROXY.md`: Detailed architecture of the agentic system
- `agentic_rag/README_AGENTIC.md`: Specifics of the agentic pipeline
- **Skills**: Use `.agents\skills` directory for specialized capabilities:
  - `gradio/`: Build Gradio web UIs and demos in Python. Use when creating or editing Gradio apps, components, event listeners, layouts, or chatbots. 
- `LEARNING.md`: Document discoveries, learnings, and insights about the project. Check before starting work and update with new findings. Max 60 lines. 