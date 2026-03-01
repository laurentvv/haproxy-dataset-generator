#!/usr/bin/env python3
"""
Évaluateur de qualité de réponse.

Évalue si une réponse est suffisante ou si un fallback est nécessaire.
"""

import logging

logger = logging.getLogger(__name__)


class ResponseEvaluator:
    """Évalue la qualité d'une réponse RAG."""

    def __init__(
        self,
        min_quality: float = 0.8,
        min_length: int = 200,
        expected_keywords: list[str] | None = None,
    ):
        """
        Initialise l'évaluateur.
        
        Args:
            min_quality: Qualité minimale requise (0.0 - 1.0)
            min_length: Longueur minimale de réponse (chars)
            expected_keywords: Keywords attendus (optionnel, pour évaluation)
        """
        self.min_quality = min_quality
        self.min_length = min_length
        self.expected_keywords = expected_keywords or []

    def evaluate(self, response: str) -> dict:
        """
        Évalue une réponse.
        
        Args:
            response: Réponse à évaluer
            
        Returns:
            Dict avec score, passed, et détails
        """
        # 1. Score de longueur
        length_ok = len(response) >= self.min_length
        length_score = 1.0 if length_ok else len(response) / self.min_length

        # 2. Score de keywords (si fournis)
        keyword_score = 1.0
        found_keywords = []
        missing_keywords = []

        if self.expected_keywords:
            response_lower = response.lower()
            found_keywords = [
                kw for kw in self.expected_keywords
                if kw.lower() in response_lower
            ]
            missing_keywords = [
                kw for kw in self.expected_keywords
                if kw.lower() not in response_lower
            ]
            keyword_score = len(found_keywords) / len(self.expected_keywords)
        else:
            # Pas de keywords - on check juste la présence de termes HAProxy
            haproxy_terms = ['haproxy', 'backend', 'frontend', 'server', 'bind',
                           'config', 'section', 'directive', 'option', 'check']
            found_terms = [t for t in haproxy_terms if t in response.lower()]
            keyword_score = min(1.0, len(found_terms) / 3)  # Au moins 3 termes

        # 3. Score global
        quality_score = (keyword_score * 0.7) + (length_score * 0.3)

        # 4. Détection de réponses "je ne sais pas"
        fallback_phrases = [
            "je ne sais pas",
            "je n'ai pas trouvé",
            "information non disponible",
            "pas d'information",
            "désolé",
            "i don't know",
            "i couldn't find",
            "not available",
        ]
        response_lower = response.lower()
        is_fallback = any(phrase in response_lower for phrase in fallback_phrases)

        # 5. Décision finale
        passed = (
            quality_score >= self.min_quality and
            length_ok and
            not is_fallback
        )

        return {
            'passed': passed,
            'quality_score': round(quality_score, 2),
            'length_score': round(length_score, 2),
            'keyword_score': round(keyword_score, 2),
            'length': len(response),
            'found_keywords': found_keywords,
            'missing_keywords': missing_keywords,
            'is_fallback': is_fallback,
        }

    def needs_fallback(self, response: str) -> bool:
        """
        Vérifie si un fallback est nécessaire.
        
        Args:
            response: Réponse à vérifier
            
        Returns:
            True si fallback nécessaire
        """
        result = self.evaluate(response)
        return not result['passed']
