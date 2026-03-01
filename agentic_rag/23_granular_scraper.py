#!/usr/bin/env python3
"""
Granular scraper for HAProxy configuration.html
Extracts each keyword as a separate section with its full documentation.
"""

import requests
import json
import re
from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def fetch_url(url, timeout=30):
    """Fetch HTML content from URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def element_to_text(element):
    """Convert an HTML element to plain text."""
    if isinstance(element, NavigableString):
        return str(element).strip()
    
    text_parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text_parts.append(str(child).strip())
        else:
            text_parts.append(element_to_text(child))
    
    return ' '.join(filter(None, text_parts))


def extract_keyword_sections(soup, base_url):
    """
    Extract each keyword as a separate section from configuration.html.
    
    The HAProxy config page has structure like:
    <a class="anchor" id="4.2-stats%20enable"></a>
    <h4><a class="anchor" id="4.2-stats%20enable"></a><code>stats enable</code></h4>
    <p>Description of stats enable...</p>
    <pre><code>Example usage...</code></pre>
    """
    sections = []
    
    # Find all numbered anchors (section IDs like "1", "2.1", "4.2-stats enable", etc.)
    all_anchors = soup.find_all("a", class_="anchor")
    
    # Filter to section 4.2 (Alphabetically sorted keywords)
    keywords_anchors = []
    for anchor in all_anchors:
        anchor_id = anchor.get("id", "")
        # Match anchors in section 4.2 (keyword definitions)
        if anchor_id.startswith("4.2-") or anchor_id.startswith("4.1-"):
            keywords_anchors.append(anchor)
    
    print(f"  Found {len(keywords_anchors)} keyword anchors in section 4.x")
    
    # For each anchor, extract the keyword and its documentation
    for i, anchor in enumerate(keywords_anchors):
        anchor_id = anchor.get("id", "")
        
        # Find the heading (usually h3 or h4 after the anchor)
        heading = None
        content_start = anchor
        
        # Navigate to find the heading
        sibling = anchor.next_sibling
        while sibling:
            if hasattr(sibling, 'name'):
                if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    heading = sibling
                    break
                # Skip empty elements
                if sibling.name == 'a' and 'anchor' in sibling.get('class', []):
                    sibling = sibling.next_sibling
                    continue
            sibling = sibling.next_sibling
        
        # Extract keyword name from heading or anchor_id
        keyword_name = ""
        if heading:
            # Extract text from heading, removing the anchor
            keyword_name = heading.get_text().strip()
            # Clean up: remove section number prefix if present
            if keyword_name.startswith(anchor_id.replace("4.2-", "").replace("4.1-", "")):
                keyword_name = keyword_name[len(anchor_id.replace("4.2-", "").replace("4.1-", "")):].strip()
        
        if not keyword_name and anchor_id:
            # Fallback: use anchor_id
            keyword_name = anchor_id.replace("4.2-", "").replace("4.1-", "").replace("%20", " ")
        
        if not keyword_name:
            continue
        
        # Now extract the content for this keyword
        # Content is everything between this anchor and the next keyword anchor
        content_elements = []
        
        try:
            all_body_contents = list(soup.body.children) if soup.body else []
            anchor_pos = all_body_contents.index(anchor)
            
            # Find next keyword anchor
            next_anchor_pos = len(all_body_contents)
            for j, anchor_elem in enumerate(keywords_anchors[i+1:], i+1):
                if anchor_elem in all_body_contents:
                    next_anchor_pos = all_body_contents.index(anchor_elem)
                    break
            
            # Collect content between anchors
            for k in range(anchor_pos + 1, min(next_anchor_pos, len(all_body_contents))):
                elem = all_body_contents[k]
                # Skip the heading (already captured)
                if elem == heading:
                    continue
                content_elements.append(elem)
                
        except (ValueError, IndexError):
            # Fallback: collect next siblings until we hit another heading
            sibling = anchor.next_sibling
            while sibling:
                if hasattr(sibling, 'name') and sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Check if this is another keyword heading
                    if sibling.find('a', class_='anchor'):
                        break
                content_elements.append(sibling)
                sibling = sibling.next_sibling
        
        # Convert content to text
        content_parts = []
        for elem in content_elements:
            if isinstance(elem, NavigableString):
                text = str(elem).strip()
                if text:
                    content_parts.append(text)
            elif hasattr(elem, 'get_text'):
                text = elem.get_text().strip()
                if text:
                    content_parts.append(text)
        
        content = '\n\n'.join(filter(None, content_parts))
        
        # Only add if there's meaningful content (at least 100 chars)
        if len(content) >= 100:
            sections.append({
                'url': base_url,
                'title': keyword_name[:200],
                'content': content,
                'section_path': [f"4.x. {keyword_name}"],
                'depth': 2,
                'anchor': anchor_id,
                'keyword': keyword_name,
            })
    
    return sections


def extract_by_heading(soup, base_url):
    """
    Alternative extraction: find each keyword by its heading structure.
    
    HAProxy config has headings like:
    <h4><code>stats enable</code></h4>
    <p>May be used in sections: defaults frontend listen backend</p>
    <p>Arguments: none</p>
    <p>Description...</p>
    """
    sections = []
    
    # Find all h3, h4 headings that contain code elements (keyword names)
    headings = soup.find_all(['h3', 'h4'])
    
    for heading in headings:
        code_elem = heading.find('code')
        if not code_elem:
            continue
        
        keyword_name = code_elem.get_text().strip()
        
        # Skip if keyword is too short (probably not a real keyword)
        if len(keyword_name) < 3:
            continue
        
        # Extract content after this heading until next heading
        content_elements = []
        sibling = heading.next_sibling
        
        while sibling:
            if hasattr(sibling, 'name') and sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Check if next heading also has a code element (new keyword)
                if sibling.find('code'):
                    break
            content_elements.append(sibling)
            sibling = sibling.next_sibling
        
        # Convert to text
        content_parts = []
        for elem in content_elements:
            if isinstance(elem, NavigableString):
                text = str(elem).strip()
                if text:
                    content_parts.append(text)
            elif hasattr(elem, 'get_text'):
                text = elem.get_text().strip()
                if text:
                    content_parts.append(text)
        
        content = '\n\n'.join(filter(None, content_parts))
        
        # Only add if there's meaningful content
        if len(content) >= 100:
            sections.append({
                'url': base_url,
                'title': keyword_name[:200],
                'content': content,
                'section_path': [f"Keyword: {keyword_name}"],
                'depth': 2,
                'anchor': None,
                'keyword': keyword_name,
            })
    
    return sections


def main():
    urls = [
        "https://docs.haproxy.org/3.2/configuration.html",
        "https://docs.haproxy.org/3.2/management.html",
    ]
    
    all_sections = []
    
    for url in urls:
        print(f"\nScraping {url}...")
        html_content = fetch_url(url)
        
        if not html_content:
            continue
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if 'configuration.html' in url:
            # Try heading-based extraction (more reliable for keywords)
            sections = extract_by_heading(soup, url)
            print(f"  ✓ Extracted {len(sections)} keyword sections (by heading)")
            
            # Also try anchor-based extraction
            anchor_sections = extract_keyword_sections(soup, url)
            print(f"  ✓ Extracted {len(anchor_sections)} keyword sections (by anchor)")
            
            # Merge, avoiding duplicates
            existing_keywords = set(s['title'] for s in sections)
            for s in anchor_sections:
                if s['title'] not in existing_keywords:
                    sections.append(s)
                    existing_keywords.add(s['title'])
            
            print(f"  → Total: {len(sections)} unique keyword sections")
        else:
            # For management.html, use generic extraction
            sections = []
            h2_tags = soup.find_all('h2')
            for h2 in h2_tags:
                title = h2.get_text().strip()
                content_parts = []
                sibling = h2.next_sibling
                while sibling:
                    if hasattr(sibling, 'name') and sibling.name in ['h1', 'h2']:
                        break
                    if hasattr(sibling, 'get_text'):
                        content_parts.append(sibling.get_text().strip())
                    sibling = sibling.next_sibling
                
                content = '\n\n'.join(filter(None, content_parts))
                if len(content) >= 100:
                    sections.append({
                        'url': url,
                        'title': title[:200],
                        'content': content,
                        'section_path': [title],
                        'depth': 1,
                    })
            print(f"  ✓ Extracted {len(sections)} sections")
        
        all_sections.extend(sections)
    
    # Save
    output_dir = Path(__file__).parent / 'data_agentic' / 'scraped_pages'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'scraped_3.2_granular.json'
    
    # Convert to agentic RAG format
    scraped_pages = []
    for section in all_sections:
        page = {
            'url': section['url'],
            'title': section.get('title', '')[:200],
            'content': section['content'],
            'section_path': section.get('section_path', []),
            'depth': section.get('depth', 1),
            'anchor': section.get('anchor'),
        }
        scraped_pages.append(page)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(scraped_pages, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Saved {len(scraped_pages)} pages to {output_path}")
    
    # Stats
    by_url = {}
    for p in scraped_pages:
        url = p['url']
        by_url[url] = by_url.get(url, 0) + 1
    
    print("\nPages by URL:")
    for url, count in sorted(by_url.items(), key=lambda x: -x[1]):
        print(f"  {url}: {count} pages")
    
    # Sample keywords from configuration.html
    config_pages = [p for p in scraped_pages if 'configuration.html' in p['url']]
    print(f"\nSample keywords extracted:")
    for p in config_pages[:10]:
        print(f"  - {p['title']}")


if __name__ == "__main__":
    main()
