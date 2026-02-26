#!/usr/bin/env python3
"""
00_rebuild_all.py - Reconstruire tout le pipeline RAG V3

Usage:
    uv run python 00_rebuild_all.py

Ce script :
1. Scraper la documentation HAProxy
2. Chunker les documents
3. Construire les index V3
4. Tester avec le benchmark
"""
import subprocess
import sys
import io

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def run_script(script_name, description):
    """Exécute un script et affiche la progression."""
    print("\n" + "="*70)
    print(f"  {description}")
    print("="*70)
    print(f"Execution: uv run python {script_name}\n")
    
    result = subprocess.run(
        ["uv", "run", "python", script_name],
        capture_output=True,
        text=True
    )
    
    # Afficher la sortie
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


def main():
    print("="*70)
    print("  RECONSTRUCTION COMPLETE - PIPELINE RAG V3")
    print("="*70)
    print()
    print("Ce script va :")
    print("  1. Scraper docs.haproxy.org (~5-10 min)")
    print("  2. Chunker les documents (~5-10 min)")
    print("  3. Construire les index V3 (~2h)")
    print("  4. Tester avec le benchmark Full (~45 min)")
    print()
    print("Temps total estime : ~3h")
    print()
    
    # Étape 1 : Scraper
    if not run_script("01_scrape.py", "ETAPE 1/4 - SCRAPPING"):
        print("\n❌ Erreur lors du scrapping")
        return
    
    # Étape 2 : Chunker
    if not run_script("02_chunking.py", "ETAPE 2/4 - CHUNKING"):
        print("\n❌ Erreur lors du chunking")
        return
    
    # Étape 3 : Indexer
    if not run_script("03_indexing.py", "ETAPE 3/4 - INDEXING"):
        print("\n❌ Erreur lors de l'indexing")
        return
    
    # Étape 4 : Benchmark
    print("\n" + "="*70)
    print("  ETAPE 4/4 - BENCHMARK")
    print("="*70)
    print()
    print("Lancement du benchmark Full (100 questions, ~45 min)...")
    print("Ou lancez manuellement : uv run python 06_bench_v3.py --level full")
    print()
    
    # Demander à l'utilisateur s'il veut lancer le benchmark
    response = input("Voulez-vous lancer le benchmark maintenant ? (o/n) : ")
    
    if response.lower() in ['o', 'oui', 'y', 'yes']:
        if not run_script("06_bench_v3.py --level full", "BENCHMARK FULL"):
            print("\n❌ Erreur lors du benchmark")
            return
    
    # Résumé final
    print("\n" + "="*70)
    print("  RECONSTRUCTION TERMINEE")
    print("="*70)
    print()
    print("Fichiers generes :")
    print("  - data/sections.jsonl")
    print("  - data/chunks.jsonl")
    print("  - index_v3/chroma/")
    print("  - index_v3/bm25.pkl")
    print("  - index_v3/chunks.pkl")
    print()
    print("Pour lancer le chatbot :")
    print("  uv run python 04_chatbot.py")
    print()
    print("Pour lancer un benchmark :")
    print("  uv run python 06_bench_v3.py --level quick    # 7 questions, 3 min")
    print("  uv run python 06_bench_v3.py --level standard # 20 questions, 8 min")
    print("  uv run python 06_bench_v3.py --level full     # 100 questions, 45 min")
    print()


if __name__ == "__main__":
    main()
