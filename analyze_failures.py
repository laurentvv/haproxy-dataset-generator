#!/usr/bin/env python3
"""Analyse des questions avec score < 0.70"""

from retriever_v3 import retrieve

# Questions problématiques avec leur question complète
QUESTIONS = {
    "full_balance_source": "Comment configurer l'algorithme source pour la persistance ?",
    "full_server_disabled": "Comment désactiver temporairement un serveur ?",
    "full_backend_name": "Comment nommer un backend dans HAProxy ?",
    "full_acl_negation": "Comment négativer une condition ACL avec ! ?",
}

print("=" * 70)
print("ANALYSE RETRIEVAL - QUESTIONS EN ÉCHEC")
print("=" * 70)

for qid, question in QUESTIONS.items():
    print(f"\n{'=' * 70}")
    print(f"ID: {qid}")
    print(f"Question: {question}")
    print(f"{'=' * 70}")

    result = retrieve(question, verbose=True)

    print("\n[RETRIEVAL] Results:")
    print(f"   Chunks: {len(result['chunks'])}")
    print(f"   Best score: {result['best_score']:.3f}")
    print(f"   Low confidence: {result['low_confidence']}")

    if result["chunks"]:
        print("\n[CHUNKS] Top 3:")
        for i, chunk in enumerate(result["chunks"][:3]):
            print(f"\n   [{i + 1}] Score: {chunk.get('rerank_score', 0):.3f}")
            print(f"       Title: {chunk['title']}")
            print(f"       URL: {chunk['url']}")
            print(f"       Section: {chunk.get('current_section', 'N/A')}")
            print(f"       Content (200 chars): {chunk['content'][:200]}...")
    else:
        print("\n   [ERROR] NO CHUNKS RETURNED")

    print("\n" + "-" * 70)
