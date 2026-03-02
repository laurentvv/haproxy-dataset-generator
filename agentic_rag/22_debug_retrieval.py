#!/usr/bin/env python3
"""Debug retrieval for stats uri"""
import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from langchain_ollama import OllamaEmbeddings
from db.chroma_manager import ChromaManager

print("=" * 80)
print("DEBUG RETRIEVAL: stats uri")
print("=" * 80)

embeddings_model = OllamaEmbeddings(model='qwen3-embedding:8b')
chroma_manager = ChromaManager()

query = "stats uri enable listen"
print(f"\nQuery: {query}")

query_embedding = embeddings_model.embed_query(query)
results = chroma_manager.query_with_embedding(query_embedding=query_embedding, n_results=10)

print(f"\nTop {len(results)} results:")
for i, r in enumerate(results, 1):
    score = r.get('score', 0)
    metadata = r.get('metadata', {})
    content = r.get('content', '')
    source = metadata.get('source', '')
    section = metadata.get('section_path', [])
    
    # Check if this result has stats uri content
    has_stats = 'stats' in content.lower()
    has_uri = 'uri' in content.lower()
    has_enable = 'enable' in content.lower()
    
    print(f"\n[{i}] score={score:.3f}")
    print(f"    source: {source}")
    print(f"    section: {section}")
    print(f"    has stats/uri/enable: {has_stats}/{has_uri}/{has_enable}")
    print(f"    content ({len(content)} chars):")
    print(f"    {content[:300]}...")
