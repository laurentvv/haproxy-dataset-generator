#!/usr/bin/env python3
import json
from pathlib import Path

scraped_file = Path(__file__).parent / 'data_agentic' / 'scraped_pages' / 'scraped_3.2.json'
data = json.loads(scraped_file.read_text(encoding='utf-8', errors='replace'))

# Check structure
print("Data structure:", type(data))
if isinstance(data, dict):
    print("Keys:", list(data.keys())[:10])
    pages = data.get('pages', data.get('data', []))
else:
    pages = data

print(f"Pages count: {len(pages) if pages else 0}")

# Get unique URLs
if pages and isinstance(pages, list):
    urls = set(p.get('url', '') for p in pages[:100])
    print(f"\nUnique URLs (from first 100 pages):")
    for u in sorted(urls)[:20]:
        print(f"  {u}")
