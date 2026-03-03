#!/usr/bin/env python3
"""
Étape 1 : Scraping HAProxy docs avec crawl4ai pour agentic_rag.

Ce script utilise crawl4ai (AsyncWebCrawler) pour scraper la documentation HAProxy
et génère un fichier JSON avec des métadonnées riches pour le chunking parent/child.
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# Configuration de l'encodage UTF-8 pour la sortie standard (Windows)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Configuration des URLs à scraper
URLS = [
    "https://docs.haproxy.org/3.2/intro.html",
    "https://docs.haproxy.org/3.2/configuration.html",
    "https://docs.haproxy.org/3.2/management.html",
]

# Chemins de sortie (basés sur config_agentic.py)
OUTPUT_DIR = Path(__file__).parent / "data_agentic" / "scraped_pages"
OUTPUT_FILE = OUTPUT_DIR / "scraped_3.2.json"


def parse_markdown_sections(markdown: str, base_url: str) -> list[dict[str, Any]]:
    """
    Découpe le markdown généré par crawl4ai en sections basées sur les titres numérotés de HAProxy.
    
    Args:
        markdown: Contenu markdown généré par crawl4ai
        base_url: URL de base de la page
        
    Returns:
        Liste de sections avec métadonnées riches
    """
    sections = []

    # Extraire le titre de la page parente
    parent_title = extract_page_title(markdown, base_url)

    # Regex pour capturer les titres de section avec ancre générés par crawl4ai
    # Format: # [3.4.1.](url#3.4.1) Titre
    pattern = r'^(#+) \s*\[(.*?)\]\(.*?#(.*?)\)\s*(.*?)$'

    matches = list(re.finditer(pattern, markdown, re.MULTILINE))

    if not matches:
        # Pas de sections trouvées, créer une section unique avec tout le contenu
        return [{
            "url": base_url,
            "title": parent_title,
            "content": markdown.strip(),
            "parent_url": base_url,
            "parent_title": parent_title,
            "depth": 1,
            "section_path": [parent_title],
            "anchor": None,
            "source_file": None
        }]

    # Ajouter l'introduction si elle existe
    if matches[0].start() > 0:
        intro_content = markdown[:matches[0].start()].strip()
        if intro_content:
            sections.append({
                "url": base_url,
                "title": f"{parent_title} - Introduction",
                "content": intro_content,
                "parent_url": base_url,
                "parent_title": parent_title,
                "depth": 1,
                "section_path": [parent_title, "Introduction"],
                "anchor": None,
                "source_file": None
            })

    # Traiter chaque section
    for i, match in enumerate(matches):
        anchor_text = match.group(2).strip()
        anchor_id = match.group(3).strip()
        title_text = match.group(4).strip()

        # Construire le titre complet
        full_title = f"{anchor_text} {title_text}".strip()
        if not title_text:
            full_title = anchor_text

        # Extraire le contenu de la section
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        content = markdown[start_pos:end_pos].strip()

        # Calculer la profondeur à partir du titre numéroté
        depth = calculate_depth(anchor_text)

        # Construire le chemin de section
        section_path = build_section_path(anchor_text, parent_title)

        if content:
            sections.append({
                "url": f"{base_url}#{anchor_id}",
                "title": full_title,
                "content": content,
                "parent_url": base_url,
                "parent_title": parent_title,
                "depth": depth,
                "section_path": section_path,
                "anchor": anchor_id,
                "source_file": None
            })

    return sections


def extract_page_title(markdown: str, base_url: str) -> str:
    """
    Extrait le titre de la page parente à partir du markdown ou de l'URL.
    
    Args:
        markdown: Contenu markdown
        base_url: URL de base
        
    Returns:
        Titre de la page parente
    """
    # Essayer de trouver le premier titre H1
    h1_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()
    
    # Extraire depuis l'URL (ex: configuration.html -> Configuration)
    url_match = re.search(r'/([^/]+)\.html$', base_url)
    if url_match:
        return url_match.group(1).replace('-', ' ').title()
    
    return "Documentation"


def calculate_depth(anchor_text: str) -> int:
    """
    Calcule la profondeur d'une section à partir de son titre numéroté.
    
    Args:
        anchor_text: Texte de l'ancre (ex: "3.4.1.")
        
    Returns:
        Profondeur (nombre de niveaux)
    """
    # Extraire les nombres du titre numéroté
    numbers = re.findall(r'\d+', anchor_text)
    return len(numbers) if numbers else 1


def build_section_path(anchor_text: str, parent_title: str) -> list[str]:
    """
    Construit le chemin de section pour une section donnée.
    
    Args:
        anchor_text: Texte de l'ancre (ex: "3.4.1.")
        parent_title: Titre de la page parente
        
    Returns:
        Liste des sections dans le chemin
    """
    path = [parent_title]
    
    # Extraire les nombres pour construire un chemin hiérarchique
    numbers = re.findall(r'\d+', anchor_text)
    if numbers:
        # Créer des étiquettes pour chaque niveau
        for i, num in enumerate(numbers):
            if i == 0:
                label = f"Section {num}"
            else:
                label = f"{'.'.join(numbers[:i+1])}"
            path.append(label)
    
    return path


async def scrape_all_async() -> list[dict[str, Any]]:
    """
    Scrape toutes les URLs configurées en utilisant crawl4ai.
    
    Returns:
        Liste de toutes les sections scrapées
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

    return all_sections


def validate_sections(sections: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Valide les sections scrapées et génère un rapport.
    
    Args:
        sections: Liste des sections scrapées
        
    Returns:
        Dictionnaire contenant les statistiques de validation
    """
    total_sections = len(sections)
    
    # Sections avec contenu vide ou trop court
    empty_content = [s for s in sections if len(s.get("content", "")) < 50]
    short_content = [s for s in sections if 50 <= len(s.get("content", "")) < 200]
    
    # Sections sans métadonnées complètes
    missing_metadata = []
    required_fields = ["url", "title", "content", "parent_url", "parent_title", "depth", "section_path", "anchor"]
    for s in sections:
        missing = [field for field in required_fields if field not in s or s[field] is None]
        if missing:
            missing_metadata.append({"url": s.get("url", "N/A"), "missing": missing})
    
    # Distribution par profondeur
    depth_distribution = {}
    for s in sections:
        depth = s.get("depth", 1)
        depth_distribution[depth] = depth_distribution.get(depth, 0) + 1
    
    # Distribution par page parente
    parent_distribution = {}
    for s in sections:
        parent = s.get("parent_title", "Unknown")
        parent_distribution[parent] = parent_distribution.get(parent, 0) + 1
    
    return {
        "total_sections": total_sections,
        "empty_content": len(empty_content),
        "short_content": len(short_content),
        "missing_metadata": len(missing_metadata),
        "depth_distribution": depth_distribution,
        "parent_distribution": parent_distribution,
        "empty_urls": [s["url"] for s in empty_content[:5]] if empty_content else [],
        "missing_metadata_details": missing_metadata[:5] if missing_metadata else []
    }


def print_validation_report(validation: dict[str, Any], execution_time: float) -> None:
    """
    Affiche le rapport de validation.
    
    Args:
        validation: Dictionnaire de validation
        execution_time: Temps d'exécution en secondes
    """
    print("\n" + "=" * 70)
    print("📊 RAPPORT DE VALIDATION")
    print("=" * 70)
    
    print(f"\n📈 Volume global :")
    print(f"   Sections totales          : {validation['total_sections']}")
    print(f"   Temps d'exécution         : {execution_time:.2f}s")
    
    print(f"\n📝 Qualité du contenu :")
    print(f"   Contenu vide (<50 chars)  : {validation['empty_content']}")
    print(f"   Contenu court (50-200c)   : {validation['short_content']}")
    
    print(f"\n🔧 Métadonnées :")
    print(f"   Métadonnées incomplètes   : {validation['missing_metadata']}")
    
    print(f"\n🌲 Distribution par profondeur :")
    for depth, count in sorted(validation['depth_distribution'].items()):
        print(f"   depth={depth} : {count} sections")
    
    print(f"\n📚 Distribution par page parente :")
    for parent, count in sorted(validation['parent_distribution'].items(), key=lambda x: -x[1]):
        print(f"   {parent:<30} : {count} sections")
    
    if validation['empty_urls']:
        print(f"\n⚠️  URLs avec contenu vide (exemples) :")
        for url in validation['empty_urls']:
            print(f"      - {url}")
    
    if validation['missing_metadata_details']:
        print(f"\n⚠️  Sections avec métadonnées manquantes (exemples) :")
        for item in validation['missing_metadata_details']:
            print(f"      - {item['url']}: {item['missing']}")
    
    print("\n" + "=" * 70)


def save_sections(sections: list[dict[str, Any]], output_path: Path) -> None:
    """
    Sauvegarde les sections dans un fichier JSON.
    
    Args:
        sections: Liste des sections à sauvegarder
        output_path: Chemin du fichier de sortie
    """
    try:
        # Créer le répertoire si nécessaire
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder en JSON (format tableau)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sections, f, ensure_ascii=False, indent=2)
        
        print(f"\n[SUCCESS] {len(sections)} sections sauvegardées dans {output_path}")
    except IOError as e:
        print(f"\n[ERROR] Erreur lors de l'écriture du fichier {output_path}: {e}")
        sys.exit(1)


async def main() -> int:
    """
    Point d'entrée principal.
    
    Returns:
        Code de retour (0 pour succès, 1 pour erreur)
    """
    print("\n" + "=" * 70)
    print("=== SCRAPING HAPROXY DOCS AVEC CRAWL4AI POUR AGENTIC_RAG ===")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Scraper les URLs
        sections = await scrape_all_async()
        
        if not sections:
            print("\n[ERROR] Aucune section n'a été scrapée. Vérifiez les URLs et la connexion.")
            return 1
        
        # Valider les sections
        validation = validate_sections(sections)
        
        # Sauvegarder les sections
        save_sections(sections, OUTPUT_FILE)
        
        # Afficher le rapport de validation
        execution_time = time.time() - start_time
        print_validation_report(validation, execution_time)
        
        # Vérifier s'il y a des problèmes critiques
        if validation['empty_content'] > validation['total_sections'] * 0.1:
            print("\n⚠️  ATTENTION: Plus de 10% des sections ont un contenu vide.")
            print("   Vérifiez les URLs et le parsing avant de continuer.")
        
        if validation['missing_metadata'] > 0:
            print("\n⚠️  ATTENTION: Certaines sections ont des métadonnées incomplètes.")
            print("   Cela pourrait affecter le chunking parent/child.")
        
        print("\n✅ Scraping terminé avec succès.")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Erreur lors du scraping: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
