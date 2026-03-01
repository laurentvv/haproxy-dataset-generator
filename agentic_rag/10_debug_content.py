#!/usr/bin/env python3
"""Check what's actually in ChromaDB for specific keywords"""

import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from langchain_ollama import OllamaEmbeddings
from db.chroma_manager import ChromaManager

# Test specific keywords
TEST_QUERIES = [
    "stick-table type ip size expire store conn_rate",
    "option httpchk GET POST",
    "stats enable uri auth realm",
    "tcp-check connect send expect",
]

print("=" * 80)
print("DEBUG CHROMADB - DETAILED CONTENT CHECK")
print("=" * 80)

embeddings_model = OllamaEmbeddings(model='qwen3-embedding:8b')
chroma_manager = ChromaManager()

for query in TEST_QUERIES:
    print(f"\n{'='*60}")
    print(f"QUERY: '{query}'")
    print(f"{'='*60}")
    
    query_embedding = embeddings_model.embed_query(query)
    results = chroma_manager.query_with_embedding(query_embedding=query_embedding, n_results=5)
    
    print(f"Results: {len(results)}")
    for i, r in enumerate(results, 1):
        score = r.get('score', 0)
        metadata = r.get('metadata', {})
        content = r.get('content', '')
        section_path = metadata.get('section_path', [])
        source = metadata.get('source', 'unknown')
        
        print(f"\n  [{i}] score={score:.3f}")
        print(f"      source: {source}")
        print(f"      section: {section_path}")
        print(f"      content ({len(content)} chars):")
        # Print first 500 chars
        for line in content[:500].split('\n')[:8]:
            print(f"        {line[:100]}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
