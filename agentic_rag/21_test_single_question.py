#!/usr/bin/env python3
"""Test single question with fixed index"""
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from app.rag_system import AgenticRAGSystem

QUESTION = "Comment configurer l'URI pour la page de stats ?"
EXPECTED_KEYWORDS = ["stats", "uri", "enable", "listen"]

print("=" * 80)
print(f"TEST QUESTION: full_stats_uri")
print(f"Question: {QUESTION}")
print(f"Keywords expected: {EXPECTED_KEYWORDS}")
print("=" * 80)

rag = AgenticRAGSystem()
session = rag.create_session()

print("\nQuerying...")
chunks = []
step_count = 0
max_steps = 15

for chunk in rag.query(session, QUESTION):
    chunks.append(chunk)
    step_count += 1
    print(f"  Step {step_count}: {len(chunk)} chars")
    if step_count > max_steps:
        print(f"  [MAX STEPS reached]")
        break

response = ''.join(chunks)
print(f"\n{'='*60}")
print(f"RESPONSE ({len(response)} chars):")
print(f"{'='*60}")
print(response[:2000])
if len(response) > 2000:
    print(f"... ({len(response) - 2000} more chars)")

# Check keywords
found = [kw for kw in EXPECTED_KEYWORDS if kw.lower() in response.lower()]
quality = len(found) / len(EXPECTED_KEYWORDS)
print(f"\n{'='*60}")
print(f"Keywords found: {found}/{EXPECTED_KEYWORDS}")
print(f"Quality: {quality:.0%}")
print(f"{'='*60}")
