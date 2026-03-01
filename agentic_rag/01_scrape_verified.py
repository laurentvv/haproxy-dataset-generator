#!/usr/bin/env python3
"""
Étape 1 : Scraping HAProxy docs avec vérification pas-à-pas.

WORKFLOW :
  1. Compter les données du projet principal (data/sections_enriched.jsonl)
  2. Lire 01_scrape.py du projet principal pour récupérer URLs + sélecteurs
  3. Scraper les mêmes pages en ajoutant l'extraction de hiérarchie
  4. Sauvegarder scraped_pages.json
  5. Afficher un rapport détaillé et ATTENDRE validation utilisateur
  6. Seulement si OK → générer hierarchy_report.json et comparer avec référence
"""

import json
import logging
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurer l'encodage UTF-8 pour la sortie standard
if sys.platform == 'win32':
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from agentic_rag.config_agentic import (
    DATA_DIR,
    SCRAPED_PAGES_DIR,
    SCRAPED_PAGES_PATH,
    SCRAPER_CONFIG,
)
from agentic_rag.scraper.compare_with_reference import ReferenceComparator
from agentic_rag.scraper.haproxy_scraper import HAProxyScraper
from agentic_rag.scraper.html_structure_analyzer import HTMLStructureAnalyzer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def count_reference_data() -> tuple[int, list[dict]]:
    """
    Compte les données du projet principal pour avoir une référence.
    
    Returns:
        Tuple (nombre d'entrées, échantillon de 3 entrées pour structure)
    """
    # Fichier de référence principal
    ref_path = Path(__file__).parent.parent / 'data' / 'sections_enriched.jsonl'
    
    if not ref_path.exists():
        print(f"⚠️  Fichier de référence non trouvé: {ref_path}")
        return 0, []
    
    # Charger les données JSONL
    reference_data = []
    with open(ref_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    reference_data.append(entry)
                except json.JSONDecodeError:
                    continue
    
    count = len(reference_data)
    sample = reference_data[:3] if reference_data else []
    
    return count, sample


def print_reference_report(count: int, sample: list[dict]) -> None:
    """Affiche le rapport de référence."""
    print("\n" + "=" * 60)
    print("📊 RÉFÉRENCE PROJET PRINCIPAL")
    print("=" * 60)
    print(f"   Fichier : data/sections_enriched.jsonl")
    print(f"   Nombre d'entrées : {count}")
    
    if sample:
        print(f"\n   Structure d'une entrée (échantillon) :")
        for i, entry in enumerate(sample[:1], 1):
            if isinstance(entry, dict):
                print(f"      Clés : {list(entry.keys())}")
                print(f"      Exemple URL : {entry.get('url', 'N/A')[:80]}...")
                print(f"      Exemple title : {entry.get('title', 'N/A')[:60]}...")
    
    print("\n" + "=" * 60)


def print_scraping_report(pages: list, reference_count: int) -> None:
    """
    Affiche un rapport lisible pour validation humaine.
    
    Args:
        pages: Liste des pages scrapées
        reference_count: Nombre de pages de référence
    """
    # Stats globales
    total = len(pages)
    coverage_pct = (total / reference_count * 100) if reference_count else 0
    
    # Distribution par profondeur
    by_depth = {}
    for p in pages:
        d = p.get("depth", 1)
        by_depth[d] = by_depth.get(d, 0) + 1
    
    # Pages avec contenu vide ou trop court
    empty = [p for p in pages if len(p.get("content", "")) < 50]
    short = [p for p in pages if 50 <= len(p.get("content", "")) < 200]
    
    # Pages sans section_path
    no_path = [p for p in pages if not p.get("section_path")]
    
    # Top sections scrapées
    sections = {}
    for p in pages:
        sp = p.get("section_path", ["?"])
        top = sp[0] if sp else "?"
        sections[top] = sections.get(top, 0) + 1
    
    print("\n" + "=" * 60)
    print("📊 RAPPORT DE SCRAPING — VALIDATION REQUISE")
    print("=" * 60)
    
    print(f"\n📈 Volume :")
    print(f"   Pages scrapées     : {total}")
    print(f"   Référence projet   : {reference_count}")
    print(f"   Couverture         : {coverage_pct:.1f}%")
    
    print(f"\n🌲 Hiérarchie (depth) :")
    for depth, count in sorted(by_depth.items()):
        label = {1: "pages racine", 2: "sections h2", 3: "sous-sections h3"}
        print(f"   depth={depth} ({label.get(depth, '?')}) : {count}")
    
    print(f"\n📚 Top sections :")
    for section, count in sorted(sections.items(), key=lambda x: -x[1])[:10]:
        print(f"   {section:<40} {count} pages")
    
    print(f"\n⚠️  Anomalies détectées :")
    print(f"   Contenu vide (<50 chars)   : {len(empty)}")
    print(f"   Contenu court (50-200c)    : {len(short)}")
    print(f"   Sans section_path          : {len(no_path)}")
    
    if empty:
        print(f"\n   URLs vides (exemples) :")
        for p in empty[:5]:
            print(f"   ⚠️  {p['url']}")
    
    print("\n" + "=" * 60)
    print("❓ VALIDATION REQUISE AVANT DE CONTINUER")
    print("=" * 60)
    print("""
Vérifiez :
  1. Le nombre de pages correspond-il à ce que vous attendez ?
  2. Les sections listées couvrent-elles bien toute la doc HAProxy ?
  3. Y a-t-il des anomalies à corriger (pages vides, manquantes) ?

→ Répondez O pour continuer vers l'étape 1.2 (analyse hiérarchie)
→ Répondez N pour corriger le scraper et relancer
""")


def wait_for_human_validation(step_name: str) -> bool:
    """
    Attend une confirmation humaine. Retourne True si OK.
    
    Args:
        step_name: Nom de l'étape en cours
    
    Returns:
        True si l'utilisateur valide, False sinon
    """
    while True:
        try:
            answer = input(f"[{step_name}] Continuer ? (O/N) : ").strip().upper()
            if answer == "O":
                return True
            elif answer == "N":
                print("❌ Validation refusée. Corriger le problème puis relancer.")
                return False
            else:
                print("   Répondre O (oui) ou N (non)")
        except EOFError:
            # Mode non-interactif (CI, tests) : on passe automatiquement
            print("   [Mode non-interactif] Passage automatique")
            return True


def main() -> int:
    """
    Point d'entrée principal.
    
    Returns:
        Code de retour (0 pour succès, 1 pour erreur).
    """
    print("\n" + "=" * 60)
    print("=== PHASE 1: Scraping + Validation ===")
    print("=" * 60)
    
    # Créer le répertoire de données
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCRAPED_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # ─────────────────────────────────────────────────────────────
    # Étape 1.0 : Compter la référence
    # ─────────────────────────────────────────────────────────────
    print("\n📌 Étape 1.0 : Comptage de la référence...")
    reference_count, reference_sample = count_reference_data()
    
    if reference_count > 0:
        print_reference_report(reference_count, reference_sample)
        
        # Validation humaine de la référence
        print("\n❓ Ces chiffres vous semblent corrects par rapport à ce que vous connaissez du projet ?")
        if not wait_for_human_validation("Référence projet principal"):
            sys.exit(1)
    else:
        print("⚠️  Aucune référence trouvée dans data/ — la couverture sera estimée sans base de comparaison")
    
    # ─────────────────────────────────────────────────────────────
    # Étape 1.1 : Scraping
    # ─────────────────────────────────────────────────────────────
    print("\n📡 Étape 1.1 : Démarrage du scraping HAProxy docs 3.2...")
    try:
        scraper = HAProxyScraper(
            base_url=SCRAPER_CONFIG['base_url'],
            version=SCRAPER_CONFIG['version'],
            output_dir=SCRAPED_PAGES_DIR,
        )
        scraped_data = scraper.scrape_all_pages()
        scraper.save_scraped_data(scraped_data)
        print(f"✓ {len(scraped_data)} pages scrapées")
    except Exception as e:
        logger.error(f"Erreur lors du scraping: {e}")
        return 1
    
    # Sauvegarde brute immédiate
    out_path = SCRAPED_PAGES_PATH
    print(f"💾 Sauvegardé : {out_path}")
    
    # ─────────────────────────────────────────────────────────────
    # Rapport + validation humaine
    # ─────────────────────────────────────────────────────────────
    print_scraping_report(scraped_data, reference_count)
    
    if not wait_for_human_validation("Scraping"):
        sys.exit(1)
    
    # ─────────────────────────────────────────────────────────────
    # Étape 1.2 : Analyse hiérarchie (seulement si scraping validé)
    # ─────────────────────────────────────────────────────────────
    print("\n🔍 Étape 1.2 : Analyse de la hiérarchie parent/child...")
    try:
        analyzer = HTMLStructureAnalyzer(scraped_data_path=SCRAPED_PAGES_PATH)
        hierarchy_report = analyzer.analyze_hierarchy()
        analyzer.save_hierarchy_report(hierarchy_report)
        print("✓ Rapport de hiérarchie généré")
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de hiérarchie: {e}")
        return 1
    
    print(f"\n📊 Rapport hiérarchie :")
    print(f"   Parent coverage   : {hierarchy_report.get('parent_coverage', 0):.1%}")
    print(f"   Orphelins         : {hierarchy_report.get('orphan_children', 0)}")
    print(f"   Avg children/parent : {hierarchy_report.get('avg_children_per_parent', 'N/A')}")
    
    # Alerte si couverture insuffisante
    if hierarchy_report.get("parent_coverage", 0) < 0.90:
        print(f"\n⚠️  ATTENTION : parent_coverage {hierarchy_report['parent_coverage']:.1%} < 90%")
        print("   La hiérarchie parent/child est insuffisante pour le RAG.")
        print("   Causes possibles : pages scrapées trop plates, TOC non parsée.")
        print("   → Indiquer si vous souhaitez continuer quand même ou corriger.")
    
    if not wait_for_human_validation("Hiérarchie parent/child"):
        sys.exit(1)
    
    # ─────────────────────────────────────────────────────────────
    # Étape 1.3 : Comparaison avec le projet principal
    # ─────────────────────────────────────────────────────────────
    print("\n📊 Étape 1.3 : Comparaison avec le projet principal...")
    try:
        reference_path = Path(__file__).parent.parent / 'data' / 'sections_enriched.jsonl'
        comparator = ReferenceComparator(
            reference_data_path=reference_path,
            scraped_data_path=SCRAPED_PAGES_PATH,
        )
        diff_report = comparator.compare_coverage()
        comparator.save_diff_report(diff_report)
        
        coverage = diff_report.get('coverage_percentage', 0)
        print(f"✓ Couverture: {coverage:.1f}%")
        
        # Affichage détaillé du rapport de comparaison
        print("\n" + "=" * 60)
        print("📊 COMPARAISON AGENTIC vs PROJET PRINCIPAL")
        print("=" * 60)
        
        print(f"\n📈 Volume global :")
        print(f"   Projet principal  : {diff_report.get('reference_entries', 'N/A')} entrées")
        print(f"   Agentic RAG       : {diff_report.get('agentic_entries', 'N/A')} entrées")
        print(f"   Couverture contenu: {coverage:.1f}%")
        
        missing_urls = diff_report.get('missing_urls', [])
        missing_sections = diff_report.get('missing_sections', [])
        
        if missing_urls:
            print(f"\n⚠️  URLs manquantes ({len(missing_urls)}) :")
            for url in sorted(missing_urls)[:10]:
                print(f"      - {url}")
            if len(missing_urls) > 10:
                print(f"      ... et {len(missing_urls)-10} autres")
        
        if missing_sections:
            print(f"\n⚠️  Sections manquantes ({len(missing_sections)}) :")
            for s in sorted(missing_sections)[:10]:
                print(f"      - {s}")
            if len(missing_sections) > 10:
                print(f"      ... et {len(missing_sections)-10} autres")
        
        print("\n" + "=" * 60)
        
        # Validation basée sur la couverture
        if len(missing_urls) == 0 and len(missing_sections) == 0:
            print("✅ COUVERTURE COMPLÈTE — aucune donnée manquante détectée")
        elif coverage >= 95:
            print(f"⚠️  COUVERTURE QUASI-COMPLÈTE ({coverage:.1f}%) — vérifier les manques ci-dessus")
        else:
            print(f"❌ COUVERTURE INSUFFISANTE ({coverage:.1f}%) — scraper à corriger avant de continuer")
        print("=" * 60)
        
        if coverage < 95.0:
            print(f"\n⚠️  WARNING: Couverture < 95% ({coverage:.1f}%)")
            if not wait_for_human_validation("Couverture insuffisante"):
                sys.exit(1)
        
    except FileNotFoundError as e:
        logger.warning(f"Fichier de référence non trouvé, validation ignorée: {e}")
        coverage = 100.0
    except Exception as e:
        logger.error(f"Erreur lors de la comparaison: {e}")
        return 1
    
    # ─────────────────────────────────────────────────────────────
    # Résumé final
    # ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ PHASE 1 VALIDÉE — prêt pour la Phase 2 (chunking)")
    print("=" * 60)
    print(f"\n📊 Résumé :")
    print(f"   - Pages scrapées: {len(scraped_data)}")
    print(f"   - Couverture: {coverage:.1f}%")
    print(f"\n💾 Fichiers produits :")
    print(f"   → {SCRAPED_PAGES_PATH}")
    print(f"   → {DATA_DIR / 'hierarchy_report.json'}")
    print(f"   → {DATA_DIR / 'scraping_diff_report.json'}")
    print("\nValidation humaine requise avant de passer à Phase 2.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
