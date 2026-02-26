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
import time
from datetime import datetime

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def run_script(script_name, description, extra_args=None):
    """Exécute un script et affiche la progression en temps réel."""
    print("\n" + "="*70)
    print(f"  {description}")
    print("="*70)
    
    cmd = ["uv", "run", "python", script_name]
    if extra_args:
        cmd.extend(extra_args)
    
    print(f"Execution: {' '.join(cmd)}")
    print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 70)

    # Exécution avec affichage en temps réel
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Afficher la sortie ligne par ligne avec timestamp
    line_count = 0
    if process.stdout:
        for line in process.stdout:
            line_count += 1
            # Afficher uniquement les lignes importantes ou toutes les 10 lignes
            if line_count % 1 == 0:  # Afficher chaque ligne
                print(line, end='')
    
    process.wait()
    elapsed_time = time.time() - start_time
    
    print("-" * 70)
    duration = time.strftime('%H:%M:%S', time.gmtime(elapsed_time))
    status = "✅ SUCCES" if process.returncode == 0 else "❌ ECHEC"
    print(f"{status} | Duration: {duration} | Exit code: {process.returncode}")
    print()
    
    return process.returncode == 0


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
    
    total_start = time.time()
    steps = [
        ("01_scrape.py", "ETAPE 1/4 - SCRAPPING"),
        ("02_chunking.py", "ETAPE 2/4 - CHUNKING"),
        ("03_indexing.py", "ETAPE 3/4 - INDEXING"),
    ]
    
    # Ajouter le benchmark si l'utilisateur le souhaite
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
        steps.append(("06_bench_v3.py", "BENCHMARK FULL", ["--level", "full"]))
    
    # Exécuter toutes les étapes
    print("\n" + "="*70)
    print("  PROGRESSION GLOBALE")
    print("="*70)
    
    failed_step = None
    for i, step in enumerate(steps, 1):
        # Afficher la progression
        progress = (i - 1) / len(steps) * 100
        bar_length = 40
        filled_length = int(bar_length * (i - 1) / len(steps))
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"\n[{bar}] {i-1}/{len(steps)} étapes complétées")
        
        if len(step) == 3:
            script_name, description, extra_args = step
            if not run_script(script_name, description, extra_args=extra_args):
                failed_step = description
                break
        else:
            script_name, description = step
            if not run_script(script_name, description):
                failed_step = description
                break
    
    total_elapsed = time.time() - total_start
    total_duration = time.strftime('%H:%M:%S', time.gmtime(total_elapsed))
    
    # Afficher la progression finale
    bar_length = 40
    bar = "█" * bar_length
    print(f"\n[{bar}] {len(steps)}/{len(steps)} étapes complétées")
    
    # Résumé final
    print("\n" + "="*70)
    if failed_step:
        print("  RECONSTRUCTION ECHECUEE")
        print("="*70)
        print(f"\n❌ Echec à l'étape: {failed_step}")
        print(f"\nTemps total: {total_duration}")
        print("\nVous pouvez relancer le script pour reprendre depuis le début.")
    else:
        print("  RECONSTRUCTION TERMINEE")
        print("="*70)
        print(f"\n✅ Toutes les étapes sont complétées avec succès!")
        print(f"\nTemps total: {total_duration}")
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
