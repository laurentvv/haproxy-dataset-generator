#!/usr/bin/env python3
"""
Comparaison détaillée entre les données du projet RAG principal et agentic_rag.

Ce script compare :
1. Le volume de données (nombre de documents, taille totale)
2. La validité du contenu HAProxy (mots-clés, directives)
3. La couverture des sections
"""

import json
import re
import sys
import io
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────

# Projet principal
MAIN_PROJECT_DATA = Path(__file__).parent / 'data' / 'sections_enriched.jsonl'

# Projet agentic
AGENTIC_DATA = Path(__file__).parent / 'agentic_rag' / 'data_agentic' / 'scraped_pages' / 'scraped_3.2.json'

# Fichier de comparaison (à supprimer après usage)
COMPARISON_REPORT_PATH = Path(__file__).parent / 'agentic_rag' / 'data_agentic' / 'comparison_report.json'

# Mots-clés HAProxy pour validation
HAPROXY_KEYWORDS = {
    # Sections principales
    'global', 'defaults', 'frontend', 'backend', 'listen', 'userlist',
    # Directives communes
    'bind', 'server', 'balance', 'mode', 'option', 'timeout',
    'acl', 'use_backend', 'default_backend',
    # Balance algorithms
    'roundrobin', 'leastconn', 'source', 'uri', 'first', 'random',
    # Modes
    'http', 'tcp', 'health',
    # Timeouts
    'connect', 'client', 'server', 'http-keep-alive', 'queue',
    # Options courantes
    'httpchk', 'httplog', 'forwardfor', 'redispatch', 'dontlognull',
    # SSL
    'ssl', 'crt', 'verify', 'ca-file',
    # Health checks
    'check', 'inter', 'fall', 'rise',
    # Stats
    'stats', 'enable', 'uri', 'auth',
    # Logging
    'log', 'stdout', 'stderr', 'local0',
    # Performance
    'maxconn', 'nbproc', 'nbthread',
    # HTTP
    'http-request', 'http-response', 'redirect',
    # Stick tables
    'stick-table', 'stick', 'track-sc',
    # Compression
    'compression', 'gzip',
}

# Directives HAProxy typiques (regex) - version permissive
HAPROXY_DIRECTIVE_PATTERN = re.compile(
    r'\b(global|defaults|frontend|backend|listen|bind|server|balance|mode|'
    r'timeout|acl|use_backend|default_backend|option|log|stats|http-request|'
    r'http-response|stick-table|stick|track-sc|cookie|http-check)\b',
    re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────
# Fonctions de chargement
# ─────────────────────────────────────────────────────────────

def load_main_project() -> list[dict]:
    """Charge les données du projet principal (JSONL)."""
    if not MAIN_PROJECT_DATA.exists():
        print(f"❌ Fichier principal non trouvé: {MAIN_PROJECT_DATA}")
        return []
    
    data = []
    with open(MAIN_PROJECT_DATA, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    return data


def load_agentic_project() -> list[dict]:
    """Charge les données du projet agentic (JSON)."""
    if not AGENTIC_DATA.exists():
        print(f"❌ Fichier agentic non trouvé: {AGENTIC_DATA}")
        return []
    
    with open(AGENTIC_DATA, encoding='utf-8') as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────
# Analyses
# ─────────────────────────────────────────────────────────────

def analyze_volume(data: list[dict], name: str) -> dict:
    """Analyse le volume de données."""
    if not data:
        return {'name': name, 'error': 'No data'}
    
    total_chars = sum(len(doc.get('content', '')) for doc in data)
    total_titles = sum(len(doc.get('title', '')) for doc in data)
    
    # Contenu vide ou court
    empty = sum(1 for doc in data if len(doc.get('content', '')) < 50)
    short = sum(1 for doc in data if 50 <= len(doc.get('content', '')) < 200)
    medium = sum(1 for doc in data if 200 <= len(doc.get('content', '')) < 1000)
    long = sum(1 for doc in data if len(doc.get('content', '')) >= 1000)
    
    # URLs uniques
    urls = set(doc.get('url', '') for doc in data)
    
    return {
        'name': name,
        'total_documents': len(data),
        'total_chars': total_chars,
        'total_titles': total_titles,
        'avg_chars_per_doc': total_chars / len(data) if data else 0,
        'empty_content': empty,
        'short_content': short,
        'medium_content': medium,
        'long_content': long,
        'unique_urls': len(urls),
    }


def analyze_haproxy_validity(data: list[dict], name: str) -> dict:
    """Analyse la validité du contenu HAProxy."""
    if not data:
        return {'name': name, 'error': 'No data'}
    
    docs_with_keywords = 0
    docs_with_directives = 0
    total_keywords_found = 0
    keywords_found = set()
    
    for doc in data:
        content = doc.get('content', '').lower()
        title = doc.get('title', '').lower()
        text = f"{content} {title}"
        
        # Vérifier les mots-clés
        doc_has_keyword = False
        for keyword in HAPROXY_KEYWORDS:
            if keyword in text:
                doc_has_keyword = True
                total_keywords_found += 1
                keywords_found.add(keyword)
        
        if doc_has_keyword:
            docs_with_keywords += 1
        
        # Vérifier les directives
        if HAPROXY_DIRECTIVE_PATTERN.search(content):
            docs_with_directives += 1
    
    return {
        'name': name,
        'docs_with_keywords': docs_with_keywords,
        'docs_with_keywords_pct': docs_with_keywords / len(data) * 100 if data else 0,
        'docs_with_directives': docs_with_directives,
        'docs_with_directives_pct': docs_with_directives / len(data) * 100 if data else 0,
        'total_keywords_found': total_keywords_found,
        'unique_keywords': len(keywords_found),
        'keywords_found': sorted(keywords_found),
    }


def analyze_sections(data: list[dict], name: str) -> dict:
    """Analyse les sections."""
    if not data:
        return {'name': name, 'error': 'No data'}
    
    sections = set()
    urls_by_section = {}
    
    for doc in data:
        title = doc.get('title', '').strip()
        url = doc.get('url', '')
        
        if title:
            # Extraire la section principale (premier élément avant un point ou chiffre)
            section = title.split('.')[0].strip() if '.' in title else title.split(':')[0].strip()
            if len(section) > 30:
                section = title[:30].strip()
            sections.add(section)
            
            if section not in urls_by_section:
                urls_by_section[section] = []
            urls_by_section[section].append(url)
    
    return {
        'name': name,
        'total_sections': len(sections),
        'top_sections': sorted(sections)[:20],
    }


def compare_content_samples(main_data: list[dict], agentic_data: list[dict]) -> None:
    """Compare des échantillons de contenu."""
    print("\n" + "=" * 80)
    print("📄 ÉCHANTILLONS DE CONTENU")
    print("=" * 80)
    
    # Premier document de chaque dataset
    if main_data:
        print("\n📌 PROJET PRINCIPAL - Document 1:")
        doc = main_data[0]
        print(f"   Title: {doc.get('title', 'N/A')[:80]}")
        print(f"   URL: {doc.get('url', 'N/A')[:80]}")
        print(f"   Content (200 chars): {doc.get('content', 'N/A')[:200]}...")
    
    if agentic_data:
        print("\n📌 AGENTIC - Document 1:")
        doc = agentic_data[0]
        print(f"   Title: {doc.get('title', 'N/A')[:80]}")
        print(f"   URL: {doc.get('url', 'N/A')[:80]}")
        print(f"   Content (200 chars): {doc.get('content', 'N/A')[:200]}...")


# ─────────────────────────────────────────────────────────────
# Rapport
# ─────────────────────────────────────────────────────────────

def print_report(main_vol: dict, agentic_vol: dict, 
                 main_valid: dict, agentic_valid: dict,
                 main_sec: dict, agentic_sec: dict) -> None:
    """Affiche le rapport de comparaison."""
    
    print("\n" + "=" * 80)
    print("📊 COMPARAISON PROJET RAG vs AGENTIC_RAG")
    print("=" * 80)
    
    # Volume
    print("\n📈 VOLUME DE DONNÉES")
    print("-" * 80)
    print(f"{'Métrique':<40} | {'Principal':<18} | {'Agentic':<18}")
    print("-" * 80)
    print(f"{'Documents totaux':<40} | {main_vol['total_documents']:<18} | {agentic_vol['total_documents']:<18}")
    print(f"{'Caractères totaux':<40} | {main_vol['total_chars']:<18,} | {agentic_vol['total_chars']:<18,}")
    print(f"{'Moyenne chars/doc':<40} | {main_vol['avg_chars_per_doc']:<18,.0f} | {agentic_vol['avg_chars_per_doc']:<18,.0f}")
    print(f"{'URLs uniques':<40} | {main_vol['unique_urls']:<18} | {agentic_vol['unique_urls']:<18}")
    
    print(f"\n{'Qualité contenu':<40} | {'Principal':<18} | {'Agentic':<18}")
    print("-" * 80)
    print(f"{'Contenu vide (<50c)':<40} | {main_vol['empty_content']:<18} | {agentic_vol['empty_content']:<18}")
    print(f"{'Contenu court (50-200c)':<40} | {main_vol['short_content']:<18} | {agentic_vol['short_content']:<18}")
    print(f"{'Contenu moyen (200-1000c)':<40} | {main_vol['medium_content']:<18} | {agentic_vol['medium_content']:<18}")
    print(f"{'Contenu long (>=1000c)':<40} | {main_vol['long_content']:<18} | {agentic_vol['long_content']:<18}")
    
    # Validité HAProxy
    print("\n✅ VALIDITÉ CONTENU HAPROXY")
    print("-" * 80)
    print(f"{'Métrique':<40} | {'Principal':<18} | {'Agentic':<18}")
    print("-" * 80)
    print(f"{'Docs avec keywords HAProxy':<40} | {main_valid['docs_with_keywords']:<18} | {agentic_valid['docs_with_keywords']:<18}")
    print(f"{'% Docs avec keywords':<40} | {main_valid['docs_with_keywords_pct']:<18,.1f}% | {agentic_valid['docs_with_keywords_pct']:<18,.1f}%")
    print(f"{'Docs avec directives HAProxy':<40} | {main_valid['docs_with_directives']:<18} | {agentic_valid['docs_with_directives']:<18}")
    print(f"{'% Docs avec directives':<40} | {main_valid['docs_with_directives_pct']:<18,.1f}% | {agentic_valid['docs_with_directives_pct']:<18,.1f}%")
    print(f"{'Keywords uniques trouvés':<40} | {main_valid['unique_keywords']:<18} | {agentic_valid['unique_keywords']:<18}")
    
    # Sections
    print("\n📚 SECTIONS")
    print("-" * 80)
    print(f"{'Métrique':<40} | {'Principal':<18} | {'Agentic':<18}")
    print("-" * 80)
    print(f"{'Total sections':<40} | {main_sec['total_sections']:<18} | {agentic_sec['total_sections']:<18}")
    
    # Verdict
    print("\n" + "=" * 80)
    print("🎯 VERDICT")
    print("=" * 80)
    
    # Calculer un score de qualité
    agentic_quality_score = (
        agentic_valid['docs_with_keywords_pct'] * 0.4 +
        agentic_valid['docs_with_directives_pct'] * 0.4 +
        (100 - (agentic_vol['empty_content'] / agentic_vol['total_documents'] * 100)) * 0.2
    )
    
    print(f"\nScore de qualité agentic : {agentic_quality_score:.1f}/100")
    
    if agentic_quality_score >= 80:
        print("✅ DONNÉES AGENCYC VALIDES - Qualité excellente")
    elif agentic_quality_score >= 60:
        print("⚠️  DONNÉES AGENCYC ACCEPTABLES - Qualité moyenne")
    else:
        print("❌ DONNÉES AGENCYC PROBLÉMATIQUES - Qualité insuffisante")
    
    # Recommandations
    print("\n📋 RECOMMANDATIONS:")
    if agentic_vol['empty_content'] > main_vol['empty_content'] * 2:
        print("   ⚠️  Trop de contenus vides → Nettoyer le scraping")
    if agentic_valid['docs_with_keywords_pct'] < 80:
        print("   ⚠️  Peu de keywords HAProxy → Vérifier le contenu scrapé")
    if agentic_vol['total_documents'] > main_vol['total_documents'] * 1.5:
        print("   ⚠️  Trop de documents → Peut-être trop de sections découpées")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    """Point d'entrée principal."""
    print("\n" + "=" * 80)
    print("🔍 COMPARAISON PROJET RAG vs AGENTIC_RAG")
    print("   Analyse de volume et validité du contenu HAProxy")
    print("=" * 80)
    
    # Chargement
    print("\n📥 Chargement des données...")
    main_data = load_main_project()
    print(f"   ✓ Projet principal: {len(main_data)} documents")
    
    agentic_data = load_agentic_project()
    print(f"   ✓ Projet agentic: {len(agentic_data)} documents")
    
    if not main_data or not agentic_data:
        print("\n❌ Impossible de charger les données. Arrêt.")
        return
    
    # Analyses
    print("\n📊 Analyses en cours...")
    
    main_vol = analyze_volume(main_data, 'Principal')
    agentic_vol = analyze_volume(agentic_data, 'Agentic')
    
    main_valid = analyze_haproxy_validity(main_data, 'Principal')
    agentic_valid = analyze_haproxy_validity(agentic_data, 'Agentic')
    
    main_sec = analyze_sections(main_data, 'Principal')
    agentic_sec = analyze_sections(agentic_data, 'Agentic')
    
    # Rapport
    print_report(main_vol, agentic_vol, main_valid, agentic_valid, main_sec, agentic_sec)
    
    # Échantillons
    compare_content_samples(main_data, agentic_data)
    
    # Sauvegarde du rapport
    report = {
        'volume': {
            'main': main_vol,
            'agentic': agentic_vol,
        },
        'validity': {
            'main': main_valid,
            'agentic': agentic_valid,
        },
        'sections': {
            'main': main_sec,
            'agentic': agentic_sec,
        },
    }
    
    report_path = COMPARISON_REPORT_PATH
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Rapport sauvegardé: {report_path}")
    print(f"   (peut être supprimé après analyse)")


if __name__ == '__main__':
    main()
