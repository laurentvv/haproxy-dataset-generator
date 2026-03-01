#!/usr/bin/env python3
"""Debug ChromaDB retrieval"""

import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from langchain_ollama import OllamaEmbeddings
from db.chroma_manager import ChromaManager

# Test queries
TEST_QUERIES = [
    "stats uri enable listen",
    "tcp-check check inter fall rise",
    "stick-table conn_rate track-sc deny",
    "http_req_rate store period",
    "converter json extract",
]

print("=" * 80)
print("DEBUG CHROMADB RETRIEVAL")
print("=" * 80)

embeddings_model = OllamaEmbeddings(model='qwen3-embedding:8b')
chroma_manager = ChromaManager()

for query in TEST_QUERIES:
    print(f"\n{'='*60}")
    print(f"QUERY: '{query}'")
    print(f"{'='*60}")
    
    query_embedding = embeddings_model.embed_query(query)
    results = chroma_manager.query_with_embedding(query_embedding=query_embedding, n_results=10)
    
    print(f"Results: {len(results)}")
    for i, r in enumerate(results[:5], 1):
        score = r.get('score', 0)
        metadata = r.get('metadata', {})
        content = r.get('content', '')[:100]
        section_path = metadata.get('section_path', [])
        print(f"  {i}. score={score:.3f} | section={section_path} | content='{content}...'")
    
    if not results:
        print("  NO RESULTS!")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
