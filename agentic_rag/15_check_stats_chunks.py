#!/usr/bin/env python3
"""Check what's in chunks_child.json for stats"""
import io
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

chunks_file = Path(__file__).parent / 'data_agentic' / 'chunks_child.json'
data = json.loads(chunks_file.read_text(encoding='utf-8', errors='replace'))

print("=" * 80)
print("CHECKING chunks_child.json FOR 'stats' (ANY)")
print("=" * 80)

# Check ALL chunks with 'stats'
stats_chunks = []
for i, chunk in enumerate(data):
    content = chunk.get('content', '').lower()
    metadata = chunk.get('metadata', {})
    source = metadata.get('source', '')
    
    if 'stats' in content:
        stats_chunks.append({
            'idx': i,
            'id': chunk.get('id', ''),
            'source': source,
            'section': str(metadata.get('section_path', []))[:60],
            'content_len': len(content),
            'has_uri': 'uri' in content,
            'has_enable': 'enable' in content,
            'content_preview': content[:200]
        })

print(f"\nTotal chunks with 'stats': {len(stats_chunks)}")

# Group by source
by_source = {}
for c in stats_chunks:
    src = c['source']
    by_source[src] = by_source.get(src, 0) + 1

print("\nBy source:")
for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}")

# Show chunks that have stats + enable
print("\nChunks with 'stats' + 'enable':")
for c in stats_chunks:
    if c['has_enable']:
        print(f"\n  [{c['idx']}] ID: {c['id']}")
        print(f"      Source: {c['source']}")
        print(f"      Section: {c['section']}")
        print(f"      Content ({c['content_len']} chars):")
        print(f"        {c['content_preview']}...")

# Show first 10 stats chunks
print("\n\nFirst 10 chunks with 'stats':")
for c in stats_chunks[:10]:
    print(f"\n  [{c['idx']}] ID: {c['id']}")
    print(f"      Source: {c['source']}")
    print(f"      Section: {c['section']}")
    print(f"      Has uri: {c['has_uri']}, Has enable: {c['has_enable']}")
    print(f"      Content preview: {c['content_preview'][:150]}...")
