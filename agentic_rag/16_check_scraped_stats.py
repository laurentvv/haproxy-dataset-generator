#!/usr/bin/env python3
"""Check what content is in scraped pages for stats section"""
import io
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

scraped_file = Path(__file__).parent / 'data_agentic' / 'scraped_pages' / 'scraped_3.2.json'
data = json.loads(scraped_file.read_text(encoding='utf-8', errors='replace'))

print("=" * 80)
print("CHECKING SCRAPED CONTENT FOR 'stats uri' SECTION")
print("=" * 80)

# Find the specific section about stats uri
for i, page in enumerate(data):
    content = page.get('content', '')
    url = page.get('url', '')
    
    # Look for stats uri specific content
    if 'stats uri' in content.lower() and 'configuration.html' in url:
        # Find the context around "stats uri"
        idx = content.lower().find('stats uri')
        if idx >= 0:
            print(f"\n{'='*60}")
            print(f"PAGE {i}: {url}")
            print(f"Found 'stats uri' at position {idx}")
            print(f"\nContext (500 chars before/after):")
            start = max(0, idx - 500)
            end = min(len(content), idx + 1000)
            print(content[start:end])
            print("...")
            
            # Also check if this content got chunked
            print(f"\nFull page content length: {len(content)} chars")

print("\n" + "=" * 80)
print("CHECK COMPLETE")
print("=" * 80)
