#!/usr/bin/env python3
"""
05_bench_agentic.py - Benchmark SIMPLIFIÉ pour le système RAG agentic.

Utilise un retriever direct au lieu du graphe LangGraph complet pour être plus rapide.
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path

# Fix encoding Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importer les questions depuis le module racine
import importlib.util

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from agentic_rag.config_agentic import LLM_CONFIG
from agentic_rag.db.chroma_manager import ChromaManager

# Charger bench_questions.py depuis le répertoire parent
bench_questions_path = Path(__file__).parent.parent / 'bench_questions.py'
spec = importlib.util.spec_from_file_location('bench_questions', bench_questions_path)
bench_questions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_questions)
QUESTIONS = bench_questions.QUESTIONS
get_questions_by_level = bench_questions.get_questions_by_level

# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_MODEL = LLM_CONFIG['model']

# SECTION_HINTS pour améliorer le retrieval sur sujets critiques
SECTION_HINTS = {
    "stick-table": ["11.1", "11.2", "7.3", "7.4", "7.5"],
    "stick": ["11.1", "11.2", "7.3"],
    "track-sc": ["11.1", "11.2"],
    "conn_rate": ["11.1", "11.2"],
    "http_req_rate": ["11.1", "11.2"],
    "deny": ["7.3", "7.4", "7.5"],
    "backend": ["5.1", "5.2", "5.3", "4.1", "4.3"],
    "balance": ["5.1", "5.2"],
    "acl": ["7.1", "7.2", "7.3", "7.4", "7.5"],
    "ssl": ["4.2", "12.1", "12.2"],
    "timeout": ["4.2", "4.3"],
}

SYSTEM_PROMPT = """Tu es un expert HAProxy 3.2. Réponds uniquement à partir du contexte fourni.

EXEMPLE DE RÉPONSE PARFAITE :
Q: Comment configurer un health check HTTP ?
R: 
**Configuration :**
1. Définir la méthode : `option httpchk GET /health`
2. Activer les checks : `server web1 192.168.1.1:80 check`
3. Paramètres avancés : `http-check send meth GET uri /health`

**Sources :** (configuration.html section 5.2)

RÈGLES ABSOLUES :
- Si l'information n'est pas dans le contexte, dis-le clairement
- Cite tes sources entre parenthèses
- Structure : 1) Réponse directe, 2) Détails techniques, 3) Exemple
- Utilise des blocs de code pour la syntaxe HAProxy"""


def evaluate_answer(answer: str, expected_keywords: list[str], min_length: int) -> dict:
    """Évalue la qualité d'une réponse."""
    answer_lower = answer.lower()
    found_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    keyword_score = len(found_keywords) / len(expected_keywords)
    length_ok = len(answer) >= min_length

    quality_score = (
        keyword_score * 0.6 + (0.2 if length_ok else 0) + (0.2 if len(answer) > 50 else 0)
    )

    return {
        'keyword_score': round(keyword_score, 2),
        'length_ok': length_ok,
        'quality_score': round(quality_score, 2),
        'found_keywords': found_keywords,
        'answer_length': len(answer),
    }


def retrieve_context(query: str, k: int = 10) -> tuple[str, list[str]]:
    """Récupère le contexte depuis ChromaDB avec metadata filtering."""
    from langchain_ollama import OllamaEmbeddings
    
    # Générer embedding
    embeddings = OllamaEmbeddings(model='qwen3-embedding:8b')
    query_embedding = embeddings.embed_query(query)
    
    # Recherche ChromaDB avec TOP_K augmenté
    chroma = ChromaManager()
    results = chroma.query_with_embedding(query_embedding, n_results=k)
    
    # Construire le contexte avec metadata filtering
    contexts = []
    sources = []
    
    # Déterminer les sections cibles basées sur la query
    target_sections = []
    query_lower = query.lower()
    for keyword, sections in SECTION_HINTS.items():
        if keyword in query_lower:
            target_sections.extend(sections)
    
    # Filtrer et scorer les résultats
    for r in results:
        score = 1.0 - r.get('score', 1.0)
        content = r.get('content', '')
        metadata = r.get('metadata', {})
        source = metadata.get('source', 'unknown')
        
        # Boost score si section cible
        section_path = metadata.get('section_path', [])
        section_boost = 0.0
        for section in section_path:
            for target in target_sections:
                if target in section:
                    section_boost = 0.2
                    break
        
        # Threshold dynamique avec boost
        if score + section_boost >= 0.25:
            contexts.append(content)
            if source not in sources:
                sources.append(source)
    
    return '\n\n'.join(contexts), sources


def benchmark_agentic(
    model: str,
    questions: list[dict],
    verbose: bool = False,
) -> dict:
    """Benchmark avec retriever direct + LLM."""
    print(f'\n{"=" * 70}')
    print('🎯 Benchmark RAG AGENTIC (mode simplifié)')
    print(f'{"=" * 70}')
    print(f'   Modèle LLM: {model}')
    print(f'   Questions: {len(questions)}')

    # Initialiser LLM
    llm = ChatOllama(model=model, temperature=0.1)

    results = []
    total_time = 0

    for i, test in enumerate(questions, 1):
        question_id = test['id']
        question = test['question']
        expected = test['expected_keywords']

        progress_bar = '█' * i + '░' * (len(questions) - i)
        print(f'\n[{progress_bar}] Question {i}/{len(questions)}: {question_id}', flush=True)
        if verbose:
            print(f'   Question: {question}', flush=True)

        # Récupérer le contexte
        start_retrieval = time.time()
        context, sources = retrieve_context(question, k=5)
        retrieval_time = time.time() - start_retrieval

        # Construire le prompt
        prompt = f"""Contexte :
{context}

Question : {question}

Réponse :"""

        # Exécuter la requête LLM
        start_generation = time.time()
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            response = llm.invoke(messages)
            answer = response.content
        except Exception as e:
            print(f'   ❌ Erreur LLM: {e}', flush=True)
            results.append({
                'question_id': question_id,
                'error': str(e),
                'quality_score': 0,
            })
            continue

        elapsed = retrieval_time + (time.time() - start_generation)
        total_time += elapsed

        # Évaluation
        eval_result = evaluate_answer(answer, expected, test['min_length'])
        eval_result['retrieval_time'] = round(retrieval_time, 2)
        eval_result['generation_time'] = round(time.time() - start_generation, 2)

        # Affichage
        status = (
            '✅'
            if eval_result['quality_score'] > 0.7
            else '⚠️'
            if eval_result['quality_score'] > 0.4
            else '❌'
        )
        print(f'   {status} Qualité: {eval_result["quality_score"]:.2f}/1.0', flush=True)
        print(f'   ⏱️  Temps: {elapsed:.2f}s (retrieval: {retrieval_time:.2f}s, generation: {eval_result["generation_time"]:.2f}s)', flush=True)
        print(f'   🎯 Keywords: {len(eval_result["found_keywords"])}/{len(expected)}', flush=True)
        if verbose and eval_result['found_keywords']:
            print(f'   📝 Trouvés: {", ".join(eval_result["found_keywords"])}', flush=True)
        if verbose:
            print(f'   📚 Sources: {", ".join(sources)}', flush=True)

        results.append(
            {
                'question_id': question_id,
                'answer': answer[:200] + '...' if len(answer) > 200 else answer,
                'response_time': round(elapsed, 2),
                'sources': sources,
                **eval_result,
            }
        )

    # Stats
    valid_results = [r for r in results if 'error' not in r]
    avg_quality = (
        sum(r['quality_score'] for r in valid_results) / len(valid_results) if valid_results else 0
    )
    questions_resolues = sum(1 for r in valid_results if r['quality_score'] > 0.7)
    taux_reussite = (questions_resolues / len(valid_results) * 100) if valid_results else 0
    avg_time = total_time / len(valid_results) if valid_results else 0

    return {
        'index': 'Agentic RAG (simplified)',
        'model': model,
        'questions_tested': len(questions),
        'results': results,
        'stats': {
            'avg_quality': round(avg_quality, 3),
            'questions_resolues': questions_resolues,
            'taux_reussite': round(taux_reussite, 1),
            'avg_time': round(avg_time, 2),
            'total_time': round(total_time, 2),
        },
    }


def generate_report(benchmark: dict, output_file: str = 'bench_agentic_targeted_report.json'):
    """Génère un rapport."""
    stats = benchmark['stats']

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(benchmark, f, indent=2, ensure_ascii=False)

    print(f'\n📊 Rapport sauvegardé: {output_file}\n')

    print('=' * 70)
    print('📈 RÉSULTATS BENCHMARK RAG AGENTIC CIBLÉ')
    print('=' * 70)

    print(f'\n🎯 Modèle LLM: {benchmark["model"]}')
    print(f'📝 Questions: {benchmark["questions_tested"]}')

    print('\n' + '-' * 70)
    print(f'{"Métrique":<30} | {"Valeur":<15}')
    print('-' * 70)
    print(f'{"Qualité moyenne":<30} | {stats["avg_quality"]:<15.3f}/1.0')
    questions_resolved = f'{stats["questions_resolues"]}/{benchmark["questions_tested"]}'
    print(f'{"Questions résolues":<30} | {questions_resolved:<14}')
    print(f'{"Taux de réussite":<30} | {stats["taux_reussite"]:<15.1f}%')
    print(f'{"Temps moyen":<30} | {stats["avg_time"]:<15.2f}s')
    print(f'{"Temps total":<30} | {stats["total_time"]:<15.2f}s')
    print('-' * 70)

    # Interprétation
    print('\n' + '=' * 70)
    print('💡 INTERPRÉTATION')
    print('=' * 70)

    if stats['avg_quality'] >= 0.90:
        print('✅ EXCELLENT - Qualité >= 0.90/1.0')
    elif stats['avg_quality'] >= 0.80:
        print('✅ TRÈS BON - Qualité >= 0.80/1.0')
    elif stats['avg_quality'] >= 0.70:
        print('⚠️  BON - Qualité >= 0.70/1.0')
    else:
        print('❌ MOYEN - Qualité < 0.70/1.0')

    if stats['taux_reussite'] >= 80:
        print(f'✅ {stats["taux_reussite"]:.1f}% des questions résolues (objectif >= 80%)')
    else:
        print(f'⚠️  {stats["taux_reussite"]:.1f}% des questions résolues (objectif >= 80%)')

    # Questions ratées
    failed = [r for r in benchmark['results'] if r.get('quality_score', 0) <= 0.7]
    if failed:
        print(f'\n⚠️  Questions à améliorer ({len(failed)}/{benchmark["questions_tested"]}):')
        for r in failed:
            print(f'   - {r["question_id"]}: {r.get("quality_score", 0):.2f}/1.0')


def main():
    parser = argparse.ArgumentParser(description='Benchmark RAG agentic ciblé')
    parser.add_argument(
        '--model',
        type=str,
        default=DEFAULT_MODEL,
        help=f'Modèle LLM (défaut: {DEFAULT_MODEL})',
    )
    parser.add_argument(
        '--questions',
        type=str,
        default='',
        help='Questions à tester (comma-separated)',
    )
    parser.add_argument(
        '--level',
        type=str,
        choices=['quick', 'standard', 'full'],
        default='',
        help='Niveau de benchmark (quick=7, standard=20, full=92 questions)',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='bench_agentic_targeted_report.json',
        help='Fichier de rapport',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Afficher plus de détails',
    )

    args = parser.parse_args()

    # Sélectionner les questions
    questions_to_test = []

    if args.level:
        # Utiliser un niveau prédéfini
        questions_to_test = get_questions_by_level(args.level)
        print(
            f'📋 Niveau: {args.level.upper()} ({len(questions_to_test)} questions)',
            flush=True,
        )
    elif args.questions:
        # Questions spécifiques
        question_ids = [q.strip() for q in args.questions.split(',')]
        questions_to_test = [q for q in QUESTIONS if q['id'] in question_ids]
        print(f'📋 Questions ciblées: {len(questions_to_test)}', flush=True)
        for q in questions_to_test:
            print(f'   - {q["id"]} ({q["category"]})', flush=True)
    else:
        print('❌ Spécifiez --level (quick/standard/full) ou --questions', flush=True)
        print('\nExemples:')
        print('  uv run python 05_bench_agentic.py --level quick')
        print('  uv run python 05_bench_agentic.py --level full')
        print(
            '  uv run python 05_bench_agentic.py --questions quick_healthcheck,quick_bind'
        )
        sys.exit(1)

    print(f'📋 Modèle LLM: {args.model}', flush=True)
    print(f'⏱️  Temps estimé: ~{len(questions_to_test) * 15:.0f}s\n', flush=True)

    # Benchmark
    try:
        result = benchmark_agentic(args.model, questions_to_test, args.verbose)
    except Exception as e:
        print(f'\n❌ Erreur benchmark: {e}', flush=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Rapport
    generate_report(result, args.output)

    print('\n✅ Benchmark RAG agentic ciblé terminé !\n', flush=True)


if __name__ == '__main__':
    main()
