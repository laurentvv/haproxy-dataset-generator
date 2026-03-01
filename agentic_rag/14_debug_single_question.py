#!/usr/bin/env python3
"""Debug single question: full_stats_uri"""
import io
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

QUESTION = "full_stats_uri"
USER_QUESTION = "Comment configurer l'URI pour la page de stats ?"
EXPECTED_KEYWORDS = ["stats", "uri", "enable", "listen"]

print("=" * 80)
print(f"DEBUG: {QUESTION}")
print(f"Question: {USER_QUESTION}")
print(f"Keywords expected: {EXPECTED_KEYWORDS}")
print("=" * 80)

# Step 1: Check scraped_pages
print("\n[1/5] CHECKING SCRAPED PAGES...")
scraped_file = Path(__file__).parent / 'data_agentic' / 'scraped_pages' / 'scraped_3.2.json'
if scraped_file.exists():
    data = json.loads(scraped_file.read_text(encoding='utf-8', errors='replace'))
    
    # Find stats-related content
    stats_pages = []
    for page in data:
        url = page.get('url', '')
        content = page.get('content', '')
        if 'stats' in content.lower() and 'uri' in content.lower():
            stats_pages.append({
                'url': url,
                'title': page.get('title', '')[:50],
                'content_len': len(content),
                'has_stats_uri': 'stats uri' in content.lower()
            })
    
    print(f"  Found {len(stats_pages)} pages with 'stats' + 'uri'")
    for p in stats_pages[:5]:
        print(f"    - {p['url']}")
        print(f"      Title: {p['title']}")
        print(f"      Content: {p['content_len']} chars")
        print(f"      Has 'stats uri': {p['has_stats_uri']}")
else:
    print(f"  ERROR: {scraped_file} not found!")

# Step 2: Check sections.jsonl (V3 RAG)
print("\n[2/5] CHECKING sections.jsonl (V3 RAG)...")
sections_file = Path(__file__).parent.parent / 'data' / 'sections.jsonl'
if sections_file.exists():
    stats_sections = []
    with open(sections_file, 'r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f):
            section = json.loads(line)
            content = section.get('content', '')
            if 'stats' in content.lower() and 'uri' in content.lower():
                stats_sections.append({
                    'line': i,
                    'section': section.get('section', '')[:50],
                    'content_len': len(content),
                    'has_example': 'stats uri' in content.lower()
                })
    
    print(f"  Found {len(stats_sections)} sections with 'stats' + 'uri'")
    for s in stats_sections[:5]:
        print(f"    - Line {s['line']}: {s['section']}")
        print(f"      Content: {s['content_len']} chars")
        print(f"      Has example: {s['has_example']}")
else:
    print(f"  ERROR: {sections_file} not found!")

# Step 3: Check chunks_child.json
print("\n[3/5] CHECKING chunks_child.json...")
chunks_file = Path(__file__).parent / 'data_agentic' / 'chunks_child.json'
if chunks_file.exists():
    data = json.loads(chunks_file.read_text(encoding='utf-8', errors='replace'))
    
    stats_chunks = []
    for chunk in data:
        content = chunk.get('content', '')
        metadata = chunk.get('metadata', {})
        if 'stats' in content.lower() and 'uri' in content.lower():
            stats_chunks.append({
                'id': chunk.get('id', ''),
                'source': metadata.get('source', ''),
                'section': str(metadata.get('section_path', []))[:50],
                'content_preview': content[:100]
            })
    
    print(f"  Found {len(stats_chunks)} chunks with 'stats' + 'uri'")
    for c in stats_chunks[:10]:
        print(f"    - ID: {c['id']}")
        print(f"      Source: {c['source']}")
        print(f"      Section: {c['section']}")
        print(f"      Content: {c['content_preview']}...")
else:
    print(f"  ERROR: {chunks_file} not found!")

print("\n" + "=" * 80)
print("INITIAL CHECK COMPLETE")
print("=" * 80)
