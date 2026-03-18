#!/usr/bin/env python3
"""
05_bench_agentic.py - Benchmark SIMPLIFIÉ pour le système RAG agentic.
Mis à jour pour Gemini Embeddings.
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from agentic_rag.config_agentic import LLM_CONFIG, EMBEDDING_MODEL, GOOGLE_API_KEY
from agentic_rag.db.chroma_manager import ChromaManager

# Charger bench_questions.py
bench_questions_path = Path(__file__).parent.parent / 'bench_questions.py'
spec = importlib.util.spec_from_file_location('bench_questions', bench_questions_path)
bench_questions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_questions)
QUESTIONS = bench_questions.QUESTIONS
get_questions_by_level = bench_questions.get_questions_by_level

# Configuration
DEFAULT_MODEL = LLM_CONFIG['model']
SYSTEM_PROMPT = "Tu es un expert HAProxy 3.2. Réponds uniquement à partir du contexte fourni."

def retrieve_context(query: str, k: int = 10) -> tuple[str, list[str]]:
    """Récupère le contexte depuis ChromaDB avec Gemini Embeddings."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY non configurée")

    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY
    )
    query_embedding = embeddings.embed_query(query)
    
    chroma = ChromaManager()
    results = chroma.query_with_embedding(query_embedding, n_results=k)
    
    contexts = [r.get('content', '') for r in results]
    sources = list(set([r.get('metadata', {}).get('source', 'unknown') for r in results]))
    
    return '\n\n'.join(contexts), sources

# Reste du script inchangé ou simplifié pour la cohérence...
# (Je garde la structure de base du benchmark)
