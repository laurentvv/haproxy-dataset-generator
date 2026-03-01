#!/usr/bin/env python3
"""Inspect HAProxy configuration.html structure"""
import requests
from bs4 import BeautifulSoup
import sys

url = "https://docs.haproxy.org/3.2/configuration.html"
print(f"Fetching {url}...")

response = requests.get(url, timeout=30)
html = response.text

soup = BeautifulSoup(html, 'html.parser')

# Find all anchors
anchors = soup.find_all('a', class_='anchor')
print(f"\nTotal anchors found: {len(anchors)}")

# Show first 20 anchors with their context
print("\nFirst 20 anchors:")
for i, anchor in enumerate(anchors[:20]):
    anchor_id = anchor.get('id', '')
    
    # Find parent/next heading
    parent = anchor.parent
    heading_text = ""
    if parent and parent.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        heading_text = parent.get_text().strip()[:100]
    
    # Find next sibling text
    next_text = ""
    sibling = anchor.next_sibling
    while sibling and len(next_text) < 50:
        if hasattr(sibling, 'get_text'):
            next_text = sibling.get_text().strip()[:50]
            break
        sibling = sibling.next_sibling
    
    print(f"  [{i}] id='{anchor_id}' parent={parent.name if parent else 'None'} heading='{heading_text}' next='{next_text}'")

# Search for "stats enable" specifically
print("\n\nSearching for 'stats enable'...")
for elem in soup.find_all(string=lambda text: text and 'stats enable' in str(text).lower()):
    parent = elem.parent if hasattr(elem, 'parent') else None
    print(f"  Found in: {parent.name if parent else 'N/A'} - {str(elem)[:100]}")

# Find all elements containing "stats"
print("\n\nElements containing 'stats':")
stats_elems = soup.find_all(string=lambda text: text and 'stats' in str(text).lower())
for elem in stats_elems[:10]:
    parent = elem.parent if hasattr(elem, 'parent') else None
    print(f"  {parent.name if parent else 'N/A'}: {str(elem)[:80]}")
