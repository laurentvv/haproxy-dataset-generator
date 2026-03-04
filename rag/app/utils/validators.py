"""Input validation for HAProxy Chatbot."""

import re

from app.utils.errors import ValidationError
from app.utils.logging import setup_logging

logger = setup_logging(__name__)


class InputValidator:
    """Validateur des entrées utilisateur.

    Responsabilités:
    - Validation de la longueur
    - Sanitisation des entrées
    - Détection de patterns dangereux
    """

    # Patterns dangereux à détecter
    DANGEROUS_PATTERNS = [
        (r"<script[^>]*>.*?</script>", "script tags"),
        (r"javascript:", "javascript protocol"),
        (r"{{.*}}", "template injection"),
        (r"<[^>]*>", "HTML tags"),
    ]

    def __init__(self, max_length: int = 2000, min_length: int = 1):
        """Initialise le validateur.

        Args:
            max_length: Longueur maximale d'une requête
            min_length: Longueur minimale d'une requête
        """
        self.max_length = max_length
        self.min_length = min_length

    def validate(self, query: str) -> str:
        """Valide et nettoie une requête utilisateur.

        Args:
            query: Requête à valider

        Returns:
            Requête validée et nettoyée

        Raises:
            ValidationError: Si la requête est invalide
        """
        # Type check
        if not isinstance(query, str):
            raise ValidationError("Query must be a string")

        # Strip whitespace
        query = query.strip()

        # Length check
        if len(query) < self.min_length:
            raise ValidationError("Query is too short")

        if len(query) > self.max_length:
            logger.warning("Query too long, truncating: %d chars", len(query))
            query = query[: self.max_length]

        # Remove dangerous patterns
        for pattern, description in self.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE | re.DOTALL):
                logger.warning("Query contains %s, removing", description)
                query = re.sub(pattern, "", query, flags=re.IGNORECASE | re.DOTALL)

        # Remove control characters
        query = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", query)

        # Final check
        if not query.strip():
            raise ValidationError("Query contains no valid content after sanitization")

        return query
