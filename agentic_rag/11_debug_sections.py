#!/usr/bin/env python3
"""Search for specific HAProxy sections"""

import io
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from db.chroma_manager import ChromaManager

chroma_manager = ChromaManager()

# Get all unique section paths
print("Getting all unique section paths...")
collection = chroma_manager.collection

# Get a sample to see what sections exist
result = collection.get(include=['metadatas'], limit=100)
sections = set()
sources = set()
for meta in result['metadatas']:
    sections.add(tuple(meta.get('section_path', [])))
    sources.add(meta.get('source', 'unknown'))

print(f"\nUnique sources ({len(sources)}):")
for s in sorted(sources)[:20]:
    print(f"  - {s}")

print(f"\nUnique section paths (first 50 of {len(sections)}):")
for sec in sorted(sections)[:50]:
    print(f"  - {sec}")
