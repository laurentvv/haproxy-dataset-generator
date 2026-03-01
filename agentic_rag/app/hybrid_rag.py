#!/usr/bin/env python3
"""
Hybrid RAG - Combinaison de Simple RAG + Fallback LangGraph.

Architecture :
1. Simple RAG (retrieval direct) - rapide (~18s)
2. Évaluation de la réponse
3. Si qualité < 80% → Fallback LangGraph (qualité max)
4. Retourne la meilleure réponse
"""

import logging
import time
from pathlib import Path

# Imports relatifs pour le package agentic_rag.app
try:
    from .evaluator import ResponseEvaluator
    from .simple_rag import SimpleRAG
except ImportError:
    from evaluator import ResponseEvaluator
    from simple_rag import SimpleRAG

logger = logging.getLogger(__name__)


class HybridRAG:
    """Système RAG hybride avec fallback automatique."""

    def __init__(
        self,
        simple_model: str = 'qwen3:latest',
        langgraph_enabled: bool = True,
        min_quality: float = 0.8,
    ):
        """
        Initialise le système hybride.
        
        Args:
            simple_model: Modèle pour Simple RAG
            langgraph_enabled: Activer fallback LangGraph
            min_quality: Qualité minimale pour éviter fallback
        """
        self.simple_rag = SimpleRAG(model=simple_model)
        self.evaluator = ResponseEvaluator(min_quality=min_quality)
        self.langgraph_enabled = langgraph_enabled
        self.min_quality = min_quality

        # Initialiser LangGraph si enabled
        self.langgraph_rag = None
        if langgraph_enabled:
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent))
                print(f"   → Import rag_system...", flush=True)
                from rag_system import AgenticRAGSystem
                print(f"   → Création AgenticRAGSystem...", flush=True)
                self.langgraph_rag = AgenticRAGSystem()
                print(f"   ✅ LangGraph fallback initialisé", flush=True)
            except Exception as e:
                print(f"   ⚠️  LangGraph non disponible: {e}", flush=True)
                logger.warning(f"⚠️  LangGraph non disponible: {e}")
                self.langgraph_enabled = False

    def query(self, question: str, expected_keywords: list[str] | None = None) -> dict:
        """
        Exécute une requête avec fallback automatique.
        
        Args:
            question: Question utilisateur
            expected_keywords: Keywords attendus (pour évaluation)
            
        Returns:
            Dict avec réponse, source, timings, et used_fallback
        """
        result = {
            'question': question,
            'used_fallback': False,
            'simple_result': None,
            'langgraph_result': None,
            'final_result': None,
        }

        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 1 : Simple RAG (rapide)
        # ─────────────────────────────────────────────────────────────
        logger.info("🚀 Étape 1: Simple RAG...")
        simple_start = time.time()

        simple_result = self.simple_rag.query(question)
        simple_time = time.time() - simple_start

        result['simple_result'] = {
            **simple_result,
            'time': simple_time,
        }

        logger.info(f"   ✅ Simple RAG: {simple_time:.2f}s, {len(simple_result['response'])} chars")

        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 2 : Évaluation
        # ─────────────────────────────────────────────────────────────
        logger.info("📊 Étape 2: Évaluation...")

        evaluator = ResponseEvaluator(
            min_quality=self.min_quality,
            expected_keywords=expected_keywords,
        )
        eval_result = evaluator.evaluate(simple_result['response'])

        result['evaluation'] = eval_result

        logger.info(f"   Qualité: {eval_result['quality_score']:.0%}, "
                   f"Keywords: {len(eval_result['found_keywords'])}/{len(eval_result['missing_keywords']) + len(eval_result['found_keywords'])}")
        logger.info(f"   Passed: {eval_result['passed']}")
        print(f"DEBUG: eval_result['passed'] = {eval_result['passed']}", flush=True)
        print(f"DEBUG: found = {eval_result['found_keywords']}", flush=True)
        print(f"DEBUG: missing = {eval_result['missing_keywords']}", flush=True)

        # ─────────────────────────────────────────────────────────────
        # ÉTAPE 3 : Fallback LangGraph si nécessaire
        # ─────────────────────────────────────────────────────────────
        print(f"DEBUG2: Checking fallback... passed={eval_result['passed']}", flush=True)
        
        if eval_result['passed']:
            logger.info("✅ Qualité suffisante - pas de fallback nécessaire")
            result['final_result'] = simple_result
            result['used_fallback'] = False
            result['total_time'] = simple_time
            print("DEBUG2: passed=True, no fallback", flush=True)
        else:
            print("DEBUG2: passed=False, SHOULD FALLBACK", flush=True)
            # Qualité insuffisante - essayer LangGraph
            logger.info(f"❌ Qualité insuffisante ({eval_result['quality_score']:.0%} < {self.min_quality:.0%})")
            if self.langgraph_rag is None:
                print("DEBUG2: langgraph_rag is None, trying to reinit...", flush=True)
                logger.info("⚠️  LangGraph non initialisé - tentative de réinitialisation...")
                try:
                    import sys
                    from pathlib import Path
                    sys.path.insert(0, str(Path(__file__).parent))
                    from rag_system import AgenticRAGSystem
                    print("   → Création AgenticRAGSystem...", flush=True)
                    self.langgraph_rag = AgenticRAGSystem()
                    print("   ✅ LangGraph réinitialisé", flush=True)
                    logger.info("✅ LangGraph réinitialisé")
                except Exception as e:
                    print(f"   ❌ Échec réinitialisation LangGraph: {e}", flush=True)
                    logger.warning(f"❌ Échec réinitialisation LangGraph: {e}")
            
            print(f"DEBUG2: langgraph_rag = {self.langgraph_rag}", flush=True)
            if self.langgraph_rag:
                logger.info("⚠️  Qualité insuffisante - fallback LangGraph...")
                lg_start = time.time()

                # Exécuter LangGraph
                session = self.langgraph_rag.create_session()
                response_chunks = []
                for chunk in self.langgraph_rag.query(session, question):
                    response_chunks.append(chunk)

                lg_response = ''.join(response_chunks)
                lg_time = time.time() - lg_start

                result['langgraph_result'] = {
                    'response': lg_response,
                    'time': lg_time,
                }

                logger.info(f"   ✅ LangGraph: {lg_time:.2f}s, {len(lg_response)} chars")

                # Comparer et choisir le meilleur
                simple_eval = evaluator.evaluate(simple_result['response'])
                lg_eval = evaluator.evaluate(lg_response)

                if lg_eval['quality_score'] > simple_eval['quality_score']:
                    logger.info(f"   🏆 LangGraph meilleur ({lg_eval['quality_score']:.0%} > {simple_eval['quality_score']:.0%})")
                    result['final_result'] = result['langgraph_result']
                    result['used_fallback'] = True
                    result['total_time'] = simple_time + lg_time
                else:
                    logger.info(f"   🏆 Simple RAG gardé ({simple_eval['quality_score']:.0%} >= {lg_eval['quality_score']:.0%})")
                    result['final_result'] = simple_result
                    result['used_fallback'] = False
                    result['total_time'] = simple_time
            else:
                logger.info("⚠️  Qualité insuffisante mais LangGraph non disponible")
                result['final_result'] = simple_result
                result['used_fallback'] = False
                result['total_time'] = simple_time

        return result
