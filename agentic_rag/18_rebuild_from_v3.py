#!/usr/bin/env python3
"""
Rebuild agentic RAG index using V3 sections.jsonl (which has correct sectioning).

This bypasses the broken scraping that created 1.4MB blobs.
"""

import io
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

# Input: V3 sections.jsonl
V3_SECTIONS_FILE = Path(__file__).parent.parent / 'data' / 'sections.jsonl'

# Output: New scraped_pages format for agentic RAG
OUTPUT_FILE = Path(__file__).parent / 'data_agentic' / 'scraped_pages' / 'scraped_3.2_v3.json'

print("=" * 80)
print("REBUILDING SCRAPED PAGES FROM V3 sections.jsonl")
print("=" * 80)

# Load V3 sections
print(f"\nLoading {V3_SECTIONS_FILE}...")
sections = []
with open(V3_SECTIONS_FILE, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                section = json.loads(line)
                sections.append(section)
            except json.JSONDecodeError:
                continue

print(f"  Loaded {len(sections)} sections")

# Convert to agentic RAG scraped_pages format
# The format expected by 02_chunking_parent_child.py:
# {
#   'url': str,
#   'title': str,
#   'content': str,
#   'section_path': list[str],
#   'depth': int,
#   'anchor': str | None,
# }

print("\nConverting to agentic RAG format...")
converted_pages = []

for section in sections:
    url = section.get('url', '')
    title = section.get('section_title', section.get('title', ''))
    content = section.get('content', '')
    
    # Skip empty or too short content
    if len(content) < 100:
        continue
    
    # Build section_path from hierarchy
    section_path = []
    if title:
        section_path = [title]
    
    page = {
        'url': url,
        'title': title[:200],  # Limit title length
        'content': content,
        'section_path': section_path,
        'depth': len(section_path),
        'anchor': None,
    }
    converted_pages.append(page)

print(f"  Converted {len(converted_pages)} pages")

# Stats by URL
by_url = {}
for p in converted_pages:
    url = p['url']
    by_url[url] = by_url.get(url, 0) + 1

print("\nPages by URL:")
for url, count in sorted(by_url.items(), key=lambda x: -x[1]):
    print(f"  {url}: {count} pages")

# Save
print(f"\nSaving to {OUTPUT_FILE}...")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(converted_pages, f, ensure_ascii=False, indent=2)

print(f"  ✓ Saved {len(converted_pages)} pages ({OUTPUT_FILE.stat().st_size:,} bytes)")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("  1. Run: 02_chunking_parent_child.py (with new scraped data)")
print("  2. Run: 03_indexing_chroma.py (to rebuild ChromaDB)")
print("  3. Run: bench_langgraph_92.py (to test)")
print("=" * 80)
