import asyncio
import json
import re
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import sys

# Configuration des URLs à scraper
URLS = [
    "https://docs.haproxy.org/3.2/intro.html",
    "https://docs.haproxy.org/3.2/configuration.html",
    "https://docs.haproxy.org/3.2/management.html",
]

def parse_markdown_sections(markdown, base_url):
    """
    Découpe le markdown généré par crawl4ai en sections basées sur les titres numérotés de HAProxy.
    """
    sections = []

    # Regex pour capturer les titres de section avec ancre générés par crawl4ai
    # Format: # [3.4.1.](url#3.4.1) Titre
    pattern = r'^(#+) \s*\[(.*?)\]\(.*?#(.*?)\)\s*(.*?)$'

    matches = list(re.finditer(pattern, markdown, re.MULTILINE))

    if not matches:
        return [{"title": "Documentation", "content": markdown, "url": base_url}]

    if matches[0].start() > 0:
        intro_content = markdown[:matches[0].start()].strip()
        if intro_content:
            sections.append({
                "title": "Introduction",
                "content": intro_content,
                "url": base_url
            })

    for i, match in enumerate(matches):
        anchor_text = match.group(2).strip()
        anchor_id = match.group(3).strip()
        title_text = match.group(4).strip()

        full_title = f"{anchor_text} {title_text}".strip()
        if not title_text:
            full_title = anchor_text

        start_pos = match.end()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(markdown)

        content = markdown[start_pos:end_pos].strip()

        if content:
            sections.append({
                "title": full_title,
                "content": content,
                "url": f"{base_url}#{anchor_id}"
            })

    return sections

async def scrape_all_async():
    """
    Scrape toutes les URLs configurées en utilisant crawl4ai.
    """
    print(f"[INFO] Démarrage du scraping avec crawl4ai sur {len(URLS)} URLs...")

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "footer", "header"]
    )

    all_sections = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in URLS:
            print(f"[FETCH] Scraping {url}...")
            result = await crawler.arun(url=url, config=run_config)

            if result.success:
                sections = parse_markdown_sections(result.markdown, url)
                all_sections.extend(sections)
                print(f"[SUCCESS] Extrait {len(sections)} sections depuis {url}")
            else:
                print(f"[ERROR] Échec du scraping pour {url}: {result.error_message}")

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "sections.jsonl"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for section in all_sections:
                f.write(json.dumps(section, ensure_ascii=False) + "\n")
        print(f"\n[SUCCESS] {len(all_sections)} sections sauvegardées dans {output_path}")
    except IOError as e:
        print(f"\n[ERROR] Erreur lors de l'écriture du fichier {output_path}: {e}")
        sys.exit(1)

def main():
    """Point d'entrée pour le script (utilisé par pyproject.toml)"""
    asyncio.run(scrape_all_async())

if __name__ == "__main__":
    main()
