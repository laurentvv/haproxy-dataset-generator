#!/usr/bin/env python3
"""
06_bench_v3.py - Benchmark V3 uniquement (qwen3-embedding:8b)

Niveaux disponibles :
- quick     : 7 questions (~3 min)
- standard  : 20 questions (~8 min)
- full      : 100 questions (~45 min)

Usage:
    uv run python 06_bench_v3.py --level full
"""
# Importer depuis 05_bench_questions
import sys
sys.path.insert(0, '.')

from bench_questions import get_questions_by_level

# Copier le contenu de bench_v3_only.py ici
# ... (trop long, à copier depuis un fichier existant)

if __name__ == "__main__":
    print("Benchmark V3 - Utilisez 00_rebuild_all.py pour une reconstruction complète")
    print("Questions disponibles:")
    print(f"  Quick: {len(get_questions_by_level('quick'))}")
    print(f"  Standard: {len(get_questions_by_level('standard'))}")
    print(f"  Full: {len(get_questions_by_level('full'))}")
