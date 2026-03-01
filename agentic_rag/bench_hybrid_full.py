#!/usr/bin/env python3
"""
Benchmark FULL 92 questions - Système Hybride.

Sauvegarde les résultats dans un fichier JSON pour analyse.
"""

import json
import sys
import io
import time
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.hybrid_rag import HybridRAG

# Importer les 92 questions
import importlib.util
bench_questions_path = Path(__file__).parent.parent / 'bench_questions.py'
spec = importlib.util.spec_from_file_location('bench_questions', bench_questions_path)
bench_questions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_questions)
QUESTIONS = bench_questions.QUESTIONS

print("=" * 80)
print("BENCHMARK FULL 92 - Système Hybride")
print("=" * 80)
print(f"Questions: {len(QUESTIONS)}")
print(f"Date: {datetime.now().isoformat()}")
print("=" * 80)

# Initialiser
print("\n⏳ Initialisation...", flush=True)
rag = HybridRAG(
    simple_model='qwen3:latest',
    langgraph_enabled=True,
    min_quality=0.8,
)
print(f"✅ Système prêt (LangGraph: {'✅' if rag.langgraph_rag else '❌'})\n")

# Résultats
all_results = []
passed_count = 0
fallback_count = 0
total_time = 0

# Benchmark
start_all = time.time()

for i, test in enumerate(QUESTIONS, 1):
    progress = i / len(QUESTIONS) * 100
    elapsed = time.time() - start_all
    eta = (elapsed / i) * (len(QUESTIONS) - i) if i > 0 else 0
    
    print(f"\n[{i}/{len(QUESTIONS)}] {test['id']} ({progress:.1f}%) - ETA: {eta/60:.1f}min", flush=True)
    
    # Exécuter
    result = rag.query(test['question'], expected_keywords=test['keywords'])
    final = result['final_result']
    
    # Évaluation
    found = [kw for kw in test['keywords'] if kw.lower() in final['response'].lower()]
    quality = len(found) / len(test['keywords'])
    time_ok = result['total_time'] < 30  # Objectif < 30s
    quality_ok = quality >= 0.8
    passed = quality_ok and time_ok
    
    if passed:
        passed_count += 1
    if result['used_fallback']:
        fallback_count += 1
    total_time += result['total_time']
    
    # Sauvegarder
    all_results.append({
        'id': test['id'],
        'question': test['question'],
        'keywords_expected': test['keywords'],
        'keywords_found': found,
        'quality': round(quality, 2),
        'total_time': round(result['total_time'], 2),
        'used_fallback': result['used_fallback'],
        'passed': passed,
        'simple_time': round(result['simple_result']['time'], 2),
        'langgraph_time': round(result['langgraph_result']['time'], 2) if result['langgraph_result'] else None,
    })
    
    # Status
    status = "✅" if passed else "⚠️"
    fb = "FB" if result['used_fallback'] else "  "
    print(f"   {status} {quality:.0%} | {result['total_time']:.1f}s | {fb}")

# Résumé
total_elapsed = time.time() - start_all
avg_time = total_time / len(QUESTIONS)
pass_rate = passed_count / len(QUESTIONS) * 100

print("\n" + "=" * 80)
print("📊 RÉSULTATS FINAUX")
print("=" * 80)
print(f"Questions        : {len(QUESTIONS)}")
print(f"Passées          : {passed_count}/{len(QUESTIONS)} ({pass_rate:.1f}%)")
print(f"Fallbacks        : {fallback_count}/{len(QUESTIONS)} ({fallback_count/len(QUESTIONS)*100:.1f}%)")
print(f"Temps total      : {total_elapsed/60:.1f}min ({total_elapsed:.1f}s)")
print(f"Temps moyen      : {avg_time:.2f}s/question")
print("=" * 80)

# Sauvegarder
output_file = Path(__file__).parent / 'bench_hybrid_full_report.json'
report = {
    'date': datetime.now().isoformat(),
    'system': 'Hybrid RAG (Simple + LangGraph fallback)',
    'total_questions': len(QUESTIONS),
    'passed': passed_count,
    'pass_rate': round(pass_rate, 2),
    'fallback_count': fallback_count,
    'total_time': round(total_elapsed, 2),
    'avg_time': round(avg_time, 2),
    'results': all_results,
}
output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(f"\n💾 Rapport sauvegardé : {output_file}")

# Questions échouées
failed = [r for r in all_results if not r['passed']]
if failed:
    print(f"\n⚠️  Questions échouées ({len(failed)}) :")
    for r in failed[:10]:
        print(f"   - {r['id']}: {r['quality']:.0%} | {r['total_time']:.1f}s | FB:{r['used_fallback']}")
    if len(failed) > 10:
        print(f"   ... et {len(failed)-10} autres")

print("\n" + "=" * 80)
if pass_rate >= 80:
    print("✅ BENCHMARK RÉUSSI - Prêt pour production !")
else:
    print(f"⚠️  BENCHMARK PARTIEL - {pass_rate:.1f}% < 80%")
print("=" * 80)
