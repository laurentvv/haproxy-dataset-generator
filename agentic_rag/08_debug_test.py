#!/usr/bin/env python3
"""Quick debug test - 5 questions only"""

import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))
from app.rag_system import AgenticRAGSystem

# 5 failing questions
TEST_QUESTIONS = [
    ("full_stats_uri", "Comment configurer l'URI pour la page de stats ?"),
    ("std_tcp_check", "Comment configurer un health check TCP dans HAProxy ?"),
    ("quick_stick_table", "Comment limiter les connexions par IP avec stick-table ?"),
    ("full_http_req_rate", "Comment mesurer le taux de requêtes HTTP avec http_req_rate ?"),
    ("full_converter_json", "Comment utiliser un converter pour extraire un champ JSON ?"),
]

print("=" * 80)
print("DEBUG TEST - 5 QUESTIONS")
print("=" * 80)

rag = AgenticRAGSystem()

for qid, question in TEST_QUESTIONS:
    print(f"\n{'='*60}")
    print(f"QUESTION: {qid}")
    print(f"  {question}")
    print(f"{'='*60}")
    
    session = rag.create_session()
    chunks = []
    step_count = 0
    max_steps = 10
    
    for chunk in rag.query(session, question):
        chunks.append(chunk)
        step_count += 1
        if step_count > max_steps:
            print(f"  [MAX STEPS reached]")
            break
    
    response = ''.join(chunks)
    print(f"\n  RESPONSE ({len(response)} chars):")
    print(f"  {response[:500]}...")
    print()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
