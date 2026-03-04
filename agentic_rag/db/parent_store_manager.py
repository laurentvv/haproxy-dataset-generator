"""
Gestionnaire du stockage JSON des chunks parents.

Ce module gère le stockage et la récupération des chunks parents.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_agentic import PARENT_STORE_DIR


class ParentStoreManager:
    """
    Gestionnaire du stockage des chunks parents.

    Cette classe gère le stockage JSON des chunks parents
    pour le système RAG agentic.
    
    OPTIMISÉ : Cache en mémoire pour éviter de recharger le fichier JSON à chaque appel.
    """

    def __init__(self, store_dir: Path | None = None) -> None:
        """
        Initialise le gestionnaire de stockage.

        Args:
            store_dir: Répertoire de stockage.
        """
        self.store_dir = store_dir or PARENT_STORE_DIR
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.store_file = self.store_dir / 'parent_chunks.json'
        
        # Cache en mémoire (chargé une seule fois)
        self._cache: dict[str, Any] | None = None
        self._cache_loaded: bool = False

    def save_parent(
        self,
        parent_id: str,
        parent_data: dict[str, Any],
    ) -> None:
        """
        Sauvegarde un chunk parent.

        Args:
            parent_id: Identifiant du chunk parent.
            parent_data: Données du chunk parent.
        """
        # Charger les données existantes
        parents = self._load_parents()

        # Ajouter ou mettre à jour le parent
        parents[parent_id] = parent_data

        # Sauvegarder
        self._save_parents(parents)

    def get_parent(self, parent_id: str) -> dict[str, Any] | None:
        """
        Récupère un chunk parent.

        Args:
            parent_id: Identifiant du chunk parent.

        Returns:
            Données du chunk parent ou None si non trouvé.
        """
        parents = self._load_parents()
        return parents.get(parent_id)

    def get_parents(
        self,
        parent_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        Récupère plusieurs chunks parents.

        Args:
            parent_ids: Liste des identifiants des chunks parents.

        Returns:
            Liste des données des chunks parents trouvés.
        """
        parents = self._load_parents()
        return [parents.get(pid) for pid in parent_ids if pid in parents]

    def get_children(
        self,
        parent_id: str,
    ) -> list[str]:
        """
        Récupère les identifiants des chunks enfants d'un parent.

        Args:
            parent_id: Identifiant du chunk parent.

        Returns:
            Liste des identifiants des chunks enfants.
        """
        parent = self.get_parent(parent_id)
        if parent is None:
            return []
        return parent.get('children', [])

    def delete_parent(self, parent_id: str) -> None:
        """
        Supprime un chunk parent.

        Args:
            parent_id: Identifiant du chunk parent.
        """
        parents = self._load_parents()
        if parent_id in parents:
            del parents[parent_id]
            self._save_parents(parents)

    def clear_store(self) -> None:
        """
        Vide le stockage.
        """
        if self.store_file.exists():
            self.store_file.unlink()

    def get_all_parents(self) -> dict[str, Any]:
        """
        Récupère tous les chunks parents.

        Returns:
            Dictionnaire de tous les chunks parents.
        """
        return self._load_parents()

    def _load_parents(self) -> dict[str, Any]:
        """
        Charge les chunks parents depuis le fichier JSON.
        
        OPTIMISÉ : Utilise un cache en mémoire pour éviter de recharger
        le fichier à chaque appel.

        Returns:
            Dictionnaire des chunks parents.
        """
        # Retourner le cache s'il est déjà chargé
        if self._cache_loaded and self._cache is not None:
            return self._cache
        
        # Premier chargement
        if not self.store_file.exists():
            self._cache = {}
        else:
            with open(self.store_file, encoding='utf-8') as f:
                self._cache = json.load(f)
        
        self._cache_loaded = True
        return self._cache

    def _save_parents(self, parents: dict[str, Any]) -> None:
        """
        Sauvegarde les chunks parents dans le fichier JSON.
        
        NOTE : Le cache est invalidé après sauvegarde pour forcer
        un rechargement lors du prochain appel.

        Args:
            parents: Dictionnaire des chunks parents.
        """
        with open(self.store_file, 'w', encoding='utf-8') as f:
            json.dump(parents, f, indent=2, ensure_ascii=False)
        
        # Invalider le cache après sauvegarde
        self._cache_loaded = False

    def get_store_stats(self) -> dict[str, Any]:
        """
        Retourne les statistiques du stockage.

        Returns:
            Statistiques du stockage.
        """
        parents = self._load_parents()
        total_children = sum(len(p.get('children', [])) for p in parents.values())
        return {
            'store_file': str(self.store_file),
            'parent_count': len(parents),
            'total_children': total_children,
        }

    def load_parent(self, parent_id: str) -> dict[str, Any] | None:
        """
        Charge un chunk parent par son identifiant.

        Args:
            parent_id: Identifiant du chunk parent.

        Returns:
            Données du chunk parent ou None si non trouvé.
        """
        return self.get_parent(parent_id)

    def load_all_parents(self) -> dict[str, Any]:
        """
        Charge tous les chunks parents.

        Returns:
            Dictionnaire de tous les chunks parents.
        """
        return self.get_all_parents()

    def get_parent_ids(self) -> list[str]:
        """
        Récupère tous les identifiants de parents.

        Returns:
            Liste des identifiants de parents.
        """
        parents = self._load_parents()
        return list(parents.keys())


def main() -> None:
    """
    Point d'entrée principal pour tester le gestionnaire.
    """
    manager = ParentStoreManager()
    stats = manager.get_store_stats()
    print(f'Store stats: {stats}')


if __name__ == '__main__':
    main()
