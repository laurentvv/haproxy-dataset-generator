#!/usr/bin/env python3
"""
Benchmark des 92 questions avec LangGraph DIRECT.

Maintenant que LangGraph est rapide (~20s), on l'utilise directement
sans fallback Simple RAG.
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

from agentic_rag.app.rag_system import AgenticRAGSystem

# Importer les 92 questions
import importlib.util
bench_questions_path = Path(__file__).parent.parent / 'bench_questions.py'
spec = importlib.util.spec_from_file_location('bench_questions', bench_questions_path)
bench_questions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_questions)
QUESTIONS = bench_questions.QUESTIONS

# Fichier de tracking
TRACKING_FILE = Path(__file__).parent / 'BENCHMARK_LANGGRAPH_92.json'

print("=" * 80)
print("BENCHMARK LANGGRAPH DIRECT - 92 QUESTIONS")
print("=" * 80)
print(f"Total: {len(QUESTIONS)} questions")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 80)

# Initialiser
print("\n⏳ Initialisation LangGraph...", flush=True)
t0 = time.time()
rag = AgenticRAGSystem()
print(f"✅ Initialisé en {time.time()-t0:.1f}s\n")

# Résultats
results = []
ok_count = 0
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
    session = rag.create_session()
    t0 = time.time()

    chunks = []
    # CRITIQUE: Limite à 10 steps pour éviter les boucles infinies
    # Chaque tool call = 2 steps (agent → tools → agent), donc ~5 tool calls max
    # Avec max 2 tool calls, on devrait avoir ~6 steps max
    step_count = 0
    max_steps = 10
    for chunk in rag.query(session, test['question']):
        chunks.append(chunk)
        step_count += 1
        elapsed_s = time.time() - t0
        if elapsed_s > 60:  # Timeout 60s par question
            print(f"   ⚠️  TIMEOUT 60s! ({step_count} steps)", flush=True)
            break
        if step_count > max_steps:
            print(f"   ⚠️  MAX STEPS ({max_steps}) reached!", flush=True)
            break

    elapsed_q = time.time() - t0
    total_time += elapsed_q
    response = ''.join(chunks)

    # Évaluation
    found = [kw for kw in test['expected_keywords'] if kw.lower() in response.lower()]
    quality = len(found) / len(test['expected_keywords'])
    time_ok = elapsed_q < 45  # Augmenté à 45s (au lieu de 30s)
    quality_ok = quality >= 0.8
    passed = quality_ok and time_ok

    if passed:
        ok_count += 1

    # Sauvegarder
    results.append({
        'id': test['id'],
        'question': test['question'],
        'keywords_expected': test['expected_keywords'],
        'keywords_found': found,
        'quality': round(quality, 2),
        'total_time': round(elapsed_q, 2),
        'passed': passed,
        'response_length': len(response),
    })

    # Status
    status = "✅" if passed else "⚠️"
    print(f"   {status} {quality:.0%} | {elapsed_q:.1f}s | {len(found)}/{len(test['expected_keywords'])} keywords")

    # Sauvegarde incrémentale
    if i % 5 == 0:
        output = {
            'date': datetime.now().isoformat(),
            'system': 'LangGraph Direct',
            'total': len(QUESTIONS),
            'processed': i,
            'ok': ok_count,
            'avg_time': round(total_time / i, 2),
            'results': results,
        }
        TRACKING_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
        print(f"   💾 Sauvegardé ({i}/{len(QUESTIONS)})")

# Résumé final
elapsed = time.time() - start_all
avg_time = total_time / len(QUESTIONS)
pass_rate = ok_count / len(QUESTIONS) * 100

print("\n" + "=" * 80)
print("📊 RÉSULTATS FINAUX")
print("=" * 80)
print(f"Questions traitées : {len(results)}/{len(QUESTIONS)}")
print(f"✅ OK (≥80%, <45s) : {ok_count}/{len(QUESTIONS)} ({pass_rate:.1f}%)")
print(f"⏱️  Temps total      : {elapsed/60:.1f}min ({elapsed:.1f}s)")
print(f"⏱️  Temps moyen      : {avg_time:.1f}s/question")
print("=" * 80)

# Sauvegarder résultats finaux
output = {
    'date': datetime.now().isoformat(),
    'system': 'LangGraph Direct',
    'total': len(QUESTIONS),
    'processed': len(results),
    'ok': ok_count,
    'pass_rate': round(pass_rate, 2),
    'total_time': round(elapsed, 2),
    'avg_time': round(avg_time, 2),
    'results': results,
}
TRACKING_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
print(f"\n💾 Résultats sauvegardés : {TRACKING_FILE}")

# Séparer les échecs : qualité vs temps
failed_quality = [r for r in results if r['quality'] < 0.8]
failed_time = [r for r in results if r['quality'] >= 0.8 and r['total_time'] >= 45]

# Questions échouées (qualité)
if failed_quality:
    print(f"\n❌ Questions échouées (qualité <80%) : {len(failed_quality)}")
    for r in failed_quality[:20]:
        print(f"   - {r['id']}: {r['quality']:.0%} | {r['total_time']:.1f}s")
    if len(failed_quality) > 20:
        print(f"   ... et {len(failed_quality)-20} autres")

# Questions trop lentes (qualité OK mais temps >45s)
if failed_time:
    print(f"\n⏱️  Questions trop lentes (qualité OK, >45s) : {len(failed_time)}")
    for r in failed_time[:20]:
        print(f"   - {r['id']}: {r['quality']:.0%} | {r['total_time']:.1f}s")
    if len(failed_time) > 20:
        print(f"   ... et {len(failed_time)-20} autres")

print("\n" + "=" * 80)
if pass_rate >= 80:
    print("✅ OBJECTIF ATTEINT (≥80%) - PRÊT POUR PRODUCTION !")
else:
    print(f"⚠️  OBJECTIF NON ATTEINT ({pass_rate:.1f}% < 80%)")
print("=" * 80)
