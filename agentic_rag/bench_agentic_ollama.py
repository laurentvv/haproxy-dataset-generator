#!/usr/bin/env python3
"""
06_bench_agentic_ollama.py - Benchmark de modèles Ollama pour RAG agentic HAProxy

Teste plusieurs modèles avec les mêmes questions et compare :
- Qualité des réponses (keywords trouvés, pertinence)
- Vitesse (tokens/seconde, temps total)
- Utilisation mémoire (taille du modèle)

Usage:
    uv run python 06_bench_agentic_ollama.py
    uv run python 06_bench_agentic_ollama.py --models gemma3:latest,qwen3:latest
    uv run python 06_bench_agentic_ollama.py --all  # Tous les modèles disponibles
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports du système agentic
from agentic_rag.app.rag_system import AgenticRAGSystem
from agentic_rag.config_agentic import LLM_CONFIG

# ── Questions de test ─────────────────────────────────────────────────────────
TEST_QUESTIONS = [
    {
        'id': 'healthcheck',
        'question': 'Comment configurer un health check HTTP dans HAProxy ?',
        'expected_keywords': ['option httpchk', 'check', 'GET', 'http-check', 'server'],
        'min_length': 200,
    },
    {
        'id': 'bind',
        'question': 'Quelle est la syntaxe de la directive bind ?',
        'expected_keywords': ['bind', 'port', 'ssl', 'crt', 'frontend'],
        'min_length': 150,
    },
    {
        'id': 'stick_table',
        'question': 'Comment limiter les connexions par IP avec stick-table ?',
        'expected_keywords': ['stick-table', 'conn_rate', 'track-sc', 'deny', 'ip'],
        'min_length': 200,
    },
]


# ── Modèles à tester ──────────────────────────────────────────────────────────
DEFAULT_MODELS = [
    'gemma3:latest',
    'gemma3n:latest',
    'qwen3:latest',
    'llama3.1:8b',
]

# Modèles à exclure (embedding, OCR, etc.)
EXCLUDED_PATTERNS = ['embed', 'ocr']


def get_ollama_url() -> str:
    return os.getenv('OLLAMA_URL', 'http://localhost:11434')


def list_available_models() -> list[str]:
    """Liste les modèles disponibles dans Ollama (filtre embedding/OCR)."""
    try:
        response = requests.get(f'{get_ollama_url()}/api/tags', timeout=10)
        response.raise_for_status()
        all_models = [m['name'] for m in response.json().get('models', [])]

        # Filtrer les modèles non pertinents
        filtered_models = []
        for model in all_models:
            # Exclure les patterns non pertinents
            if any(pattern in model.lower() for pattern in EXCLUDED_PATTERNS):
                continue

            filtered_models.append(model)

        return filtered_models
    except Exception as e:
        print(f'❌ Erreur liste modèles: {e}')
        return []


def is_gguf_model(model_name: str) -> bool:
    """Vérifie si le modèle est au format GGUF."""
    return 'GGUF' in model_name or 'gguf' in model_name.lower()


def benchmark_agentic_model(
    model_name: str,
    rag_system_factory: callable,
    questions: list[dict],
) -> dict:
    """
    Benchmark d'un modèle avec le système RAG agentic.

    Args:
        model_name: Nom du modèle à tester
        rag_system_factory: Fonction pour créer une instance du système RAG
        questions: Liste des questions à tester

    Returns:
        dict avec stats: temps, qualité, etc.
    """
    print(f'\n{"=" * 60}')
    print(f'🔍 Benchmark: {model_name}')
    print(f'{"=" * 60}')

    # Créer une nouvelle instance du système RAG avec le modèle spécifié
    try:
        rag_system = rag_system_factory(model_name)
    except Exception as e:
        print(f'   ❌ Erreur création système RAG: {e}')
        return {'error': 'Failed to create RAG system'}

    results = []
    total_time = 0

    for i, test in enumerate(questions, 1):
        question_id = test['id']
        question = test['question']
        expected = test['expected_keywords']

        print(f'\n  Question {i}/{len(questions)}: {question_id}')

        # Créer une nouvelle session
        session_id = rag_system.create_session()

        # Benchmark
        start_time = time.time()

        try:
            # Exécuter la requête
            response_chunks = []
            for chunk in rag_system.query(session_id, question):
                response_chunks.append(chunk)
            answer = ''.join(response_chunks)

            elapsed = time.time() - start_time
            total_time += elapsed

            # Qualité
            answer_lower = answer.lower()
            found_keywords = [kw for kw in expected if kw.lower() in answer_lower]
            keyword_score = len(found_keywords) / len(expected)

            # Longueur
            length_ok = len(answer) >= test['min_length']

            # Score global
            quality_score = (
                keyword_score * 0.6 + (0.2 if length_ok else 0) + (0.2 if len(answer) > 50 else 0)
            )

            result = {
                'question_id': question_id,
                'answer': answer[:200] + '...' if len(answer) > 200 else answer,
                'answer_length': len(answer),
                'elapsed': elapsed,
                'keyword_score': round(keyword_score, 2),
                'found_keywords': found_keywords,
                'quality_score': round(quality_score, 2),
            }
            results.append(result)

            # Affichage
            status = '✅' if quality_score > 0.7 else '⚠️' if quality_score > 0.4 else '❌'
            print(f'    {status} Qualité: {quality_score:.2f}')
            print(f'    ⏱️  Temps: {elapsed:.2f}s')
            print(f'    🎯 Keywords: {len(found_keywords)}/{len(expected)}')

        except Exception as e:
            print(f'    ❌ Erreur: {e}')
            results.append(
                {
                    'question_id': question_id,
                    'error': str(e),
                    'quality_score': 0,
                }
            )

    # Stats globales
    avg_quality = sum(r.get('quality_score', 0) for r in results) / len(results)
    avg_time = sum(r.get('elapsed', 0) for r in results if 'elapsed' in r) / max(
        1, len([r for r in results if 'elapsed' in r])
    )

    return {
        'model': model_name,
        'results': results,
        'stats': {
            'avg_quality': round(avg_quality, 2),
            'avg_time': round(avg_time, 2),
            'total_time': round(total_time, 2),
        },
    }


def generate_report(benchmarks: list[dict], output_file: str = 'bench_agentic_ollama_report.json'):
    """Génère un rapport JSON et texte."""

    # Filtrer les erreurs
    valid_benchmarks = [b for b in benchmarks if 'error' not in b]

    if not valid_benchmarks:
        print('\n❌ Aucun benchmark valide')
        return

    # Classement par qualité
    ranking_quality = sorted(
        valid_benchmarks,
        key=lambda x: x['stats']['avg_quality'],
        reverse=True,
    )

    # Classement par vitesse
    ranking_speed = sorted(
        valid_benchmarks,
        key=lambda x: x['stats']['avg_time'],
    )

    # Rapport JSON
    report_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'models_tested': len(valid_benchmarks),
        'ranking_quality': [
            {
                'model': b['model'],
                'avg_quality': b['stats']['avg_quality'],
                'avg_time': b['stats']['avg_time'],
            }
            for b in ranking_quality
        ],
        'ranking_speed': [
            {
                'model': b['model'],
                'avg_time': b['stats']['avg_time'],
                'avg_quality': b['stats']['avg_quality'],
            }
            for b in ranking_speed
        ],
        'all_results': benchmarks,
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print(f'\n📊 Rapport sauvegardé: {output_file}')

    # Rapport texte
    print('\n' + '=' * 70)
    print('📈 CLASSEMENT PAR QUALITÉ')
    print('=' * 70)

    for i, entry in enumerate(ranking_quality, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else '  '
        print(f'{medal} {i}. {entry["model"]}')
        print(f'     Qualité: {entry["avg_quality"]:.2f}/1.0 | Temps: {entry["avg_time"]:.2f}s')

    print('\n' + '=' * 70)
    print('⚡ CLASSEMENT PAR VITESSE')
    print('=' * 70)

    for i, entry in enumerate(ranking_speed, 1):
        medal = '🚀' if i == 1 else '  '
        print(f'{medal} {i}. {entry["model"]}')
        print(f'     Vitesse: {entry["avg_time"]:.2f}s | Qualité: {entry["avg_quality"]:.2f}/1.0')

    # Recommandations
    print('\n' + '=' * 70)
    print('💡 RECOMMANDATIONS')
    print('=' * 70)

    best_quality = ranking_quality[0]
    best_speed = ranking_speed[0]

    print(f'✅ Meilleure qualité: {best_quality["model"]}')
    print(f'⚡ Plus rapide: {best_speed["model"]}')

    # Compromis qualité/vitesse
    best_compromise = max(
        valid_benchmarks,
        key=lambda x: (
            x['stats']['avg_quality'] / x['stats']['avg_time'] if x['stats']['avg_time'] > 0 else 0
        ),
    )
    print(f'🎯 Meilleur compromis: {best_compromise["model"]}')

    if best_quality['avg_quality'] < 0.6:
        print('\n⚠️  Tous les modèles ont des scores < 0.6')
        print('   → Essayez un modèle plus grand ou fine-tunez')


def create_rag_system_factory():
    """Crée une factory pour le système RAG agentic."""

    def factory(model_name: str) -> AgenticRAGSystem:
        """Crée une instance du système RAG avec le modèle spécifié."""
        from langchain_ollama import ChatOllama
        from langgraph.checkpoint.memory import InMemorySaver

        from agentic_rag.rag_agent.graph import build_agentic_graph

        # Créer le LLM avec le modèle spécifié
        llm = ChatOllama(
            model=model_name,
            temperature=LLM_CONFIG['temperature'],
            top_p=LLM_CONFIG['top_p'],
            num_ctx=LLM_CONFIG['num_ctx'],
        )

        # Créer le checkpointer
        checkpointer = InMemorySaver()

        # Construire le graphe
        graph = build_agentic_graph(llm=llm, checkpointer=checkpointer)

        # Créer et retourner le système RAG
        rag_system = AgenticRAGSystem.__new__(AgenticRAGSystem)
        rag_system.llm = llm
        rag_system.checkpointer = checkpointer
        rag_system.graph = graph
        rag_system.active_sessions = {}
        return rag_system

    return factory


def main():
    parser = argparse.ArgumentParser(description='Benchmark de modèles Ollama pour RAG agentic')
    parser.add_argument(
        '--models',
        type=str,
        default=','.join(DEFAULT_MODELS),
        help='Modèles à tester (comma-separated)',
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Tester tous les modèles disponibles',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='bench_agentic_ollama_report.json',
        help='Fichier de rapport',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Afficher les réponses complètes',
    )

    args = parser.parse_args()

    # Vérifier Ollama
    print("🔍 Vérification d'Ollama...")
    try:
        response = requests.get(f'{get_ollama_url()}/api/tags', timeout=10)
        response.raise_for_status()
        available_models = [m['name'] for m in response.json().get('models', [])]
        print(f'✅ {len(available_models)} modèles disponibles')
    except Exception as e:
        print(f'❌ Ollama inaccessible: {e}')
        print('   Lancez: ollama serve')
        sys.exit(1)

    # Sélection des modèles
    if args.all:
        models_to_test = available_models
    else:
        models_to_test = [m.strip() for m in args.models.split(',')]
        # Filtrer les modèles indisponibles
        models_to_test = [m for m in models_to_test if m in available_models]

    if not models_to_test:
        print('❌ Aucun modèle à tester')
        sys.exit(1)

    print(f'\n📋 Modèles à tester: {models_to_test}')
    print(f'📝 Questions: {len(TEST_QUESTIONS)}')

    # Créer la factory pour le système RAG
    rag_system_factory = create_rag_system_factory()

    # Benchmarks
    benchmarks = []
    for model in models_to_test:
        try:
            result = benchmark_agentic_model(model, rag_system_factory, TEST_QUESTIONS)
            benchmarks.append(result)
        except Exception as e:
            print(f'\n❌ Erreur pour {model}: {e}')
            benchmarks.append(
                {
                    'model': model,
                    'error': str(e),
                    'results': [],
                    'stats': {'avg_quality': 0, 'avg_time': 0},
                }
            )

    # Rapport
    generate_report(benchmarks, args.output)

    print('\n✅ Benchmark terminé !')


if __name__ == '__main__':
    main()
