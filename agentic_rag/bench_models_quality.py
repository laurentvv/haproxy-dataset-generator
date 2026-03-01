#!/usr/bin/env python3
"""
Benchmark complet : Vitesse + Qualité des réponses pour les modèles Ollama.
"""

import time
import sys
import json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, newline=None)

# Questions de test avec keywords attendus (2 questions rapides)
TEST_QUESTIONS = [
    {
        "id": "healthcheck",
        "question": "Comment configurer un health check HTTP dans HAProxy ?",
        "keywords": ["option httpchk", "check", "GET", "http-check", "server"]
    },
    {
        "id": "backend",
        "question": "Comment ajouter un serveur dans un backend HAProxy ?",
        "keywords": ["server", "backend", "address", "port", "check"]
    },
]

MODELS = [
    "gemma3:12b",
    "granite4:7b-a1b-h",
    "qwen3:latest",
]

print("=" * 80)
print("🚀 BENCHMARK QUALITÉ + VITESSE MODÈLES OLLAMA")
print("=" * 80)

results = {}

for model in MODELS:
    print(f"\n📊 Test du modèle: {model}")
    print("-" * 80)
    
    try:
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(
            model=model,
            temperature=0.1,
            num_ctx=4096,
        )
        
        model_results = []
        total_time = 0
        total_quality = 0
        
        for test in TEST_QUESTIONS:
            t0 = time.time()
            
            # Prompt avec contexte HAProxy
            prompt = f"""Tu es un expert HAProxy 3.2. Réponds de manière technique et précise.
Donne un exemple de configuration si possible.

Question : {test['question']}"""
            
            response = llm.invoke(prompt)
            elapsed = time.time() - t0
            total_time += elapsed
            
            # Analyser la qualité
            response_text = response.content.lower()
            found_keywords = [kw for kw in test['keywords'] if kw.lower() in response_text]
            quality = len(found_keywords) / len(test['keywords'])
            total_quality += quality
            
            model_results.append({
                'id': test['id'],
                'time': round(elapsed, 1),
                'quality': round(quality * 100),
                'keywords_found': f"{len(found_keywords)}/{len(test['keywords'])}",
                'response_length': len(response.content),
            })
            
            # Affichage
            status = "✅" if quality >= 0.8 else "⚠️" if quality >= 0.5 else "❌"
            print(f"   {status} {test['id']}: {quality:.0%} | {elapsed:.1f}s | {len(found_keywords)}/{len(test['keywords'])} keywords")
        
        avg_time = total_time / len(TEST_QUESTIONS)
        avg_quality = total_quality / len(TEST_QUESTIONS) * 100
        
        results[model] = {
            'avg_time': round(avg_time, 1),
            'avg_quality': round(avg_quality, 1),
            'total_time': round(total_time, 1),
            'details': model_results,
        }
        
        print(f"\n   ⏱️  Moyenne: {avg_time:.1f}s/question")
        print(f"   🎯 Qualité moyenne: {avg_quality:.1f}%")
        print(f"   📊 Score: {avg_quality:.0f}/100")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        results[model] = {'error': str(e)}

# Résumé comparatif
print("\n" + "=" * 80)
print("📊 RÉSUMÉ COMPARATIF")
print("=" * 80)
print(f"{'Modèle':<25} | {'Temps moyen':<12} | {'Qualité':<10} | {'Score'}")
print("-" * 80)

for model, data in results.items():
    if 'error' in data:
        print(f"{model:<25} | {'ERREUR':<12} | {'-':<10} | {data['error'][:30]}")
    else:
        score = f"{data['avg_quality']:.0f}/100"
        print(f"{model:<25} | {data['avg_time']:<12.1f}s | {data['avg_quality']:<10.1f}% | {score}")

print("-" * 80)

# Trouver le meilleur compromis vitesse/qualité
valid_models = [(m, d) for m, d in results.items() if 'error' not in d]
if valid_models:
    # Score = qualité - (temps/10) pour pénaliser la lenteur
    best = max(valid_models, key=lambda x: x[1]['avg_quality'] - x[1]['avg_time']/10)
    print(f"\n🏆 Meilleur compromis: {best[0]}")
    print(f"   Qualité: {best[1]['avg_quality']:.1f}% | Temps: {best[1]['avg_time']:.1f}s")

print("\n" + "=" * 80)

# Sauvegarder les résultats
output_path = Path(__file__).parent / 'benchmark_models_quality.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump({'models': results, 'questions': [q['id'] for q in TEST_QUESTIONS]}, f, indent=2, ensure_ascii=False)
print(f"💾 Résultats sauvegardés : {output_path}")
print("=" * 80)
