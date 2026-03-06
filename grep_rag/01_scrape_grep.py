import asyncio
import re
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

URLS = [
    "https://docs.haproxy.org/3.2/intro.html",
    "https://docs.haproxy.org/3.2/configuration.html",
    "https://docs.haproxy.org/3.2/management.html",
]

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def parse_markdown_to_flat_files(markdown, base_url, page_name):
    """
    Découpe le markdown en sections principales (h1/h2).
    Chaque fichier contient ses sous-sections (h3, h4...).
    """
    sections = []

    # Pattern crawl4ai: # [X](url#X) Titre
    pattern = r'^(#+) \s*\[(.*?)\]\(.*?#(.*?)\)\s*(.*?)$'
    matches = list(re.finditer(pattern, markdown, re.MULTILINE))

    if not matches:
        return [{
            "page": page_name,
            "title": "Documentation",
            "content": markdown,
            "url": base_url,
            "anchor": "",
            "depth": 0,
        }]

    # 1. Identifier les limites des sections principales (depth 1 ou 2)
    main_indices = [i for i, m in enumerate(matches) if len(m.group(1)) <= 2]

    # 2. Gérer l'éventuel contenu avant la première section principale
    if main_indices and matches[main_indices[0]].start() > 0:
        content = markdown[:matches[main_indices[0]].start()].strip()
        if content:
             sections.append({
                "page": page_name,
                "title": "Introduction",
                "content": content,
                "url": base_url,
                "anchor": "intro",
                "depth": 1,
            })

    # 3. Créer les sections basées sur les titres principaux
    for idx, main_idx in enumerate(main_indices):
        match = matches[main_idx]
        level = len(match.group(1))
        anchor_text = match.group(2).strip()
        anchor_id = match.group(3).strip()
        title_text = match.group(4).strip()
        full_title = f"{anchor_text} {title_text}".strip() or anchor_text

        start_pos = match.start() # On inclut le titre dans le fichier

        # La fin est le début de la prochaine section PRINCIPALE
        if idx + 1 < len(main_indices):
            end_pos = matches[main_indices[idx+1]].start()
        else:
            end_pos = len(markdown)

        content = markdown[start_pos:end_pos].strip()

        sections.append({
            "page": page_name,
            "title": full_title,
            "content": content,
            "url": f"{base_url}#{anchor_id}",
            "anchor": anchor_id,
            "depth": level,
        })

    return sections

async def scrape_all():
    print(f"[INFO] Scraping {len(URLS)} URLs avec crawl4ai (format raw)...")
    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    flat_files_dir = Path("grep_rag/data/flat_files")
    flat_files_dir.mkdir(parents=True, exist_ok=True)

    # Nettoyer les anciens fichiers pour éviter les doublons orphelins
    for f in flat_files_dir.glob("*.md"):
        f.unlink()

    all_scraped_sections = []

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for url in URLS:
            page_name = url.split('/')[-1].replace('.html', '')
            print(f"[FETCH] {url}...")
            result = await crawler.arun(url=url, config=run_cfg)

            if result.success:
                markdown = result.markdown
                if hasattr(markdown, 'raw_markdown'):
                    markdown = markdown.raw_markdown

                sections = parse_markdown_to_flat_files(markdown, url, page_name)
                print(f"[PARSE] {len(sections)} sections principales dans {page_name}")

                for sec in sections:
                    slug = slugify(sec['title'])
                    filename = f"{sec['page']}__{slug}.md"
                    filepath = flat_files_dir / filename

                    header = f"# SECTION: {sec['title']}\n"
                    header += f"# URL: {sec['url']}\n"
                    header += f"# DEPTH: {sec['depth']}\n"
                    header += f"# PAGE: {sec['page']}\n"
                    header += "---\n\n"

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(header + sec['content'])

                    all_scraped_sections.append({
                        "filename": filename,
                        "title": sec['title'],
                        "url": sec['url'],
                        "depth": sec['depth'],
                        "page": sec['page'],
                        "char_count": len(sec['content'])
                    })
            else:
                print(f"[ERROR] {url}: {result.error_message}")

    print(f"[SUCCESS] {len(all_scraped_sections)} fichiers .md générés.")

if __name__ == "__main__":
    asyncio.run(scrape_all())
