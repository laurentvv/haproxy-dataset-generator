#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from db.chroma_manager import ChromaManager

chroma_manager = ChromaManager()
collection = chroma_manager.collection

# Get count
count = collection.count()
print(f"Total documents in ChromaDB: {count}")

# Get sample with metadata
result = collection.get(include=['metadatas', 'documents'], limit=20)
print(f"\nSample documents:")
for i, (doc, meta) in enumerate(zip(result['documents'], result['metadatas']), 1):
    source = meta.get('source', 'unknown')
    section = meta.get('section_path', [])
    print(f"{i}. source={source} | section={section[:30]}... | content='{doc[:80]}...'")

# Count by source
result_all = collection.get(include=['metadatas'])
sources = {}
for meta in result_all['metadatas']:
    src = meta.get('source', 'unknown')
    sources[src] = sources.get(src, 0) + 1

print(f"\nDocuments by source:")
for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}")
