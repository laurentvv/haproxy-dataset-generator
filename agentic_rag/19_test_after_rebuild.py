#!/usr/bin/env python3
"""Test retrieval after rebuild"""
import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from langchain_ollama import OllamaEmbeddings
from db.chroma_manager import ChromaManager

print("=" * 80)
print("TEST RETRIEVAL AFTER REBUILD")
print("=" * 80)

embeddings_model = OllamaEmbeddings(model='qwen3-embedding:8b')
chroma_manager = ChromaManager()

# Test query for stats uri
query = "stats uri enable listen"
print(f"\nQUERY: '{query}'")

query_embedding = embeddings_model.embed_query(query)
results = chroma_manager.query_with_embedding(query_embedding=query_embedding, n_results=5)

print(f"\nResults: {len(results)}")
for i, r in enumerate(results, 1):
    score = r.get('score', 0)
    metadata = r.get('metadata', {})
    content = r.get('content', '')[:300]
    source = metadata.get('source', '')
    section = metadata.get('section_path', [])
    
    print(f"\n[{i}] score={score:.3f}")
    print(f"    source: {source}")
    print(f"    section: {section}")
    print(f"    content: {content}...")

# Check if we found stats uri content
found_stats_uri = any('stats uri' in r.get('content', '').lower() for r in results)
print(f"\n✓ Found 'stats uri' in results: {found_stats_uri}")

print("\n" + "=" * 80)
