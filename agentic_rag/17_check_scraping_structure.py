#!/usr/bin/env python3
"""Check scraping structure"""
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
print("CHECKING SCRAPING STRUCTURE")
print("=" * 80)

# Group by URL
by_url = {}
for page in data:
    url = page.get('url', '')
    if url not in by_url:
        by_url[url] = []
    by_url[url].append(page)

print(f"\nTotal pages scraped: {len(data)}")
print(f"Unique URLs: {len(by_url)}")

print("\nPages by URL:")
for url, pages in sorted(by_url.items(), key=lambda x: -len(x[1])):
    total_chars = sum(len(p.get('content', '')) for p in pages)
    print(f"\n  {url}")
    print(f"    Count: {len(pages)} pages")
    print(f"    Total chars: {total_chars:,}")
    
    # Show size distribution
    sizes = [len(p.get('content', '')) for p in pages]
    print(f"    Min size: {min(sizes):,} chars")
    print(f"    Max size: {max(sizes):,} chars")
    print(f"    Avg size: {sum(sizes)//len(sizes):,} chars")
    
    # Show first 5 pages
    print(f"    Sample pages:")
    for i, p in enumerate(pages[:5]):
        content_len = len(p.get('content', ''))
        title = p.get('title', '')[:50]
        section = str(p.get('section_path', []))[:60]
        print(f"      [{i}] {content_len:,} chars | title='{title}' | section={section}")
    
    if len(pages) > 5:
        print(f"      ... and {len(pages)-5} more")
