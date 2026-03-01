"""Gestionnaire de documents pour le système RAG agentic."""

from pathlib import Path


class DocumentManager:
    """Gestionnaire de documents."""

    def __init__(self, data_dir: Path) -> None:
        """Initialise le gestionnaire de documents.

        Args:
            data_dir: Répertoire des données
        """
        self.data_dir = Path(data_dir)

    def load_document(self, path: str) -> str | None:
        """Charge un document.

        Args:
            path: Chemin du document

        Returns:
            Contenu du document ou None
        """
        file_path = self.data_dir / path
        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f'Erreur lors du chargement du document: {e}')
            return None

    def save_document(self, path: str, content: str) -> bool:
        """Sauvegarde un document.

        Args:
            path: Chemin du document
            content: Contenu du document

        Returns:
            True si succès, False sinon
        """
        file_path = self.data_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f'Erreur lors de la sauvegarde du document: {e}')
            return False
