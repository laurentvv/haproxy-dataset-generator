#!/usr/bin/env python3
"""
Analyze benchmark failures to identify patterns and missing keywords.
"""

import json
import sys
import io
from collections import defaultdict
from pathlib import Path
from charset_normalizer import detect

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load results
results_file = Path(__file__).parent / 'BENCHMARK_LANGGRAPH_92.json'

# Detect encoding
with open(results_file, 'rb') as f:
    raw_data = f.read()
    detected = detect(raw_data)
    encoding = detected['encoding'] or 'utf-8'

data = json.loads(raw_data.decode(encoding))

# Separate passing and failing
passed = [r for r in data['results'] if r['passed']]
failed = [r for r in data['results'] if not r['passed']]

print("=" * 80)
print("ANALYSE DES ÉCHECS - BENCHMARK LANGGRAPH 92")
print("=" * 80)
print(f"Total: {data['total']} | OK: {len(passed)} | Échoués: {len(failed)}")
print(f"Pass rate: {data['pass_rate']:.1f}%")
print(f"Temps moyen: {data['avg_time']:.1f}s/question")
print("=" * 80)

# Categorize failures by missing keywords
print("\n📋 QUESTIONS ÉCHOUÉES DÉTAILLÉES\n")

# Group by category based on question ID prefix and topic
categories = defaultdict(list)
for r in failed:
    qid = r['id']
    # Determine category
    if 'stick' in qid or 'track' in qid or 'rate' in qid or 'conn_rate' in qid or 'http_req' in qid:
        categories['stick-table/rate-limiting'].append(r)
    elif 'tcp_check' in qid or 'tcp_request' in qid or 'tcp_response' in qid:
        categories['tcp-check'].append(r)
    elif 'timeout' in qid:
        categories['timeout'].append(r)
    elif 'stats' in qid:
        categories['stats'].append(r)
    elif 'log' in qid:
        categories['logs'].append(r)
    elif 'acl' in qid:
        categories['acl'].append(r)
    elif 'bind' in qid or 'ssl' in qid:
        categories['ssl/bind'].append(r)
    elif 'balance' in qid:
        categories['balance'].append(r)
    elif 'server' in qid:
        categories['server'].append(r)
    elif 'mode' in qid or 'tcp' in qid or 'http' in qid:
        categories['mode'].append(r)
    elif 'map' in qid or 'var' in qid:
        categories['maps/vars'].append(r)
    elif 'deny' in qid:
        categories['deny/rate'].append(r)
    elif 'httpchk' in qid:
        categories['httpchk'].append(r)
    elif 'frontend' in qid or 'backend' in qid or 'listen' in qid:
        categories['sections'].append(r)
    else:
        categories['other'].append(r)

# Print analysis by category
for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
    print(f"\n{'='*60}")
    print(f"📁 CATÉGORIE: {cat} ({len(items)} questions)")
    print('='*60)
    
    # Aggregate missing keywords
    all_missing = defaultdict(int)
    for r in items:
        missing = set(r['keywords_expected']) - set(r['keywords_found'])
        for kw in missing:
            all_missing[kw] += 1
    
    print(f"\n❌ Questions:")
    for r in items:
        missing = set(r['keywords_expected']) - set(r['keywords_found'])
        print(f"   - {r['id']}: {r['quality']:.0%} | manquants: {', '.join(missing)}")
    
    print(f"\n🔑 Mots-clés manquants les plus fréquents:")
    for kw, count in sorted(all_missing.items(), key=lambda x: -x[1])[:10]:
        print(f"   - {kw}: manquant dans {count} questions")

# Summary of top missing keywords across ALL failures
print("\n" + "=" * 80)
print("🔍 TOP 30 MOTS-CLÉS MANQUANTS (TOUS ÉCHECS)")
print("=" * 80)

all_missing_global = defaultdict(int)
for r in failed:
    missing = set(r['keywords_expected']) - set(r['keywords_found'])
    for kw in missing:
        all_missing_global[kw] += 1

for i, (kw, count) in enumerate(sorted(all_missing_global.items(), key=lambda x: -x[1])[:30], 1):
    print(f"{i:2}. {kw}: {count} questions")

print("\n" + "=" * 80)
print("💡 RECOMMANDATIONS")
print("=" * 80)
print("""
1. SECTION_HINTS: Ajouter les mots-clés les plus fréquents manquants
2. Prompt: Renforcer l'obligation d'utiliser les mots-clés anglais
3. Retrieval: Vérifier que les sections ciblées contiennent bien ces keywords
4. Envisager: Abaisser le threshold de 0.20 à 0.15 pour plus de résultats
""")
