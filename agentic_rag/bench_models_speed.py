#!/usr/bin/env python3
"""
Benchmark rapide pour comparer la vitesse des modèles Ollama.
"""

import time
import sys
import requests
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, newline=None)

def unload_ollama_model():
    """Force Ollama à décharger le modèle actuel de la mémoire."""
    try:
        # Appel à l'API Ollama pour générer un token vide avec keep_alive=0
        # Ça force le déchargement du modèle en mémoire
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'gemma3:12b',  # N'importe quel modèle
                'prompt': '',
                'stream': False,
                'keep_alive': 0  # Décharge immédiatement
            },
            timeout=5
        )
        print(f"   🧹 Ollama memory cleared (status: {response.status_code})")
    except Exception as e:
        print(f"   ⚠️  Could not clear Ollama memory: {e}")

# Questions de test (5 questions représentatives)
TEST_QUESTIONS = [
    "Comment configurer un health check HTTP dans HAProxy ?",
    "Comment limiter les connexions par IP avec stick-table ?",
    "Comment créer une ACL basée sur le chemin URL ?",
    "Comment configurer SSL/TLS sur un frontend ?",
    "Comment ajouter un serveur dans un backend HAProxy ?",
]

MODELS = [
    "gemma3:12b",
    "granite4:7b-a1b-h",
    "qwen3:latest"
]

print("=" * 80)
print("🚀 BENCHMARK VITESSE MODÈLES OLLAMA")
print("=" * 80)

for i, model in enumerate(MODELS):
    print(f"\n📊 Test du modèle: {model}")
    print("-" * 60)
    
    # Nettoyer la mémoire avant chaque test (sauf le premier)
    if i > 0:
        unload_ollama_model()
    
    try:
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(
            model=model,
            temperature=0.1,
            num_ctx=2048,
        )
        
        # Test simple (sans tools, juste génération)
        total_time = 0
        results = []
        
        for j, question in enumerate(TEST_QUESTIONS, 1):
            t0 = time.time()
            response = llm.invoke(f"Réponds en 2-3 phrases: {question}")
            elapsed = time.time() - t0
            total_time += elapsed
            results.append(elapsed)
            print(f"   Q{j}: {elapsed:.1f}s | {len(response.content)} chars")
        
        avg_time = total_time / len(TEST_QUESTIONS)
        print(f"\n   ⏱️  Moyenne: {avg_time:.1f}s/question")
        print(f"   ⏱️  Total: {total_time:.1f}s pour 5 questions")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        print(f"   Le modèle '{model}' est-il disponible ? (ollama pull {model})")

# Nettoyer la mémoire à la fin
print("\n🧹 Nettoyage final...")
unload_ollama_model()

print("\n" + "=" * 80)
print("💡 Conseil: Le modèle le plus rapide est idéal pour le RAG")
print("=" * 80)
