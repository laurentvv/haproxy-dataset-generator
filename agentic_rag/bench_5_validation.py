#!/usr/bin/env python3
"""Benchmark 5 questions avant FULL 92."""

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

# Import avec chemin absolu
from agentic_rag.app.hybrid_rag import HybridRAG

# 5 questions représentatives
TEST_QUESTIONS = [
    {'id': 'Q1', 'question': "How to configure health check in HAProxy?", 'keywords': ["check", "http-check", "inter", "fall", "rise"]},
    {'id': 'Q2', 'question': "How to define a backend with servers in HAProxy?", 'keywords': ["backend", "server", "balance", "port", "check"]},
    {'id': 'Q3', 'question': "How to configure bind with SSL certificate in HAProxy?", 'keywords': ["bind", "ssl", "crt", "cert", "pem"]},
    {'id': 'Q4', 'question': "How to create ACL based on URL path in HAProxy?", 'keywords': ["acl", "path", "url", "if"]},
    {'id': 'Q5', 'question': "How to limit connections per IP with stick-table in HAProxy?", 'keywords': ["stick-table", "conn_rate", "deny", "ip", "track-sc"]},
]

print("=" * 80)
print("BENCHMARK 5 QUESTIONS - Validation avant FULL 92")
print("=" * 80)

# Initialiser
print("\n⏳ Initialisation...", flush=True)
rag = HybridRAG(
    simple_model='qwen3:latest',
    langgraph_enabled=True,
    min_quality=0.8,
)
print(f"✅ Système prêt\n")

# Benchmark
results = []
passed = 0
total_time = 0
fallbacks = 0

start = time.time()

for i, test in enumerate(TEST_QUESTIONS, 1):
    print(f"[{i}/5] {test['id']}...", flush=True)
    
    result = rag.query(test['question'], expected_keywords=test['keywords'])
    final = result['final_result']
    
    found = [kw for kw in test['keywords'] if kw.lower() in final['response'].lower()]
    quality = len(found) / len(test['keywords'])
    
    if quality >= 0.8:
        passed += 1
    if result['used_fallback']:
        fallbacks += 1
    total_time += result['total_time']
    
    results.append({
        'id': test['id'],
        'quality': round(quality, 2),
        'time': round(result['total_time'], 2),
        'fallback': result['used_fallback'],
        'passed': quality >= 0.8,
    })
    
    status = "✅" if quality >= 0.8 else "❌"
    fb = "FB" if result['used_fallback'] else ""
    print(f"   {status} {quality:.0%} | {result['total_time']:.1f}s | {fb}")

elapsed = time.time() - start
avg = total_time / len(TEST_QUESTIONS)
pass_rate = passed / len(TEST_QUESTIONS) * 100

print("\n" + "=" * 80)
print("RÉSULTATS :")
print(f"  Passées : {passed}/5 ({pass_rate:.0f}%)")
print(f"  Fallbacks : {fallbacks}/5 ({fallbacks/5*100:.0f}%)")
print(f"  Temps moyen : {avg:.1f}s/question")
print(f"  Temps total : {elapsed/60:.1f}min")
print("=" * 80)

if pass_rate >= 80:
    print("\n✅ VALIDÉ - Prêt pour FULL 92 !")
    print(f"   Estimation FULL 92 : {92 * avg / 60:.1f}min")
else:
    print(f"\n⚠️  NON VALIDÉ - {pass_rate:.0f}% < 80%")

print("=" * 80)
