"""
Analyseur de structure HTML pour la documentation HAProxy.

Ce module analyse la hiérarchie HTML de la documentation.
"""

import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


class HTMLStructureAnalyzer:
    """
    Analyseur de structure HTML.

    Cette classe analyse la hiérarchie HTML de la documentation
    pour identifier les sections et sous-sections.
    """

    def __init__(self, scraped_data_path: Path | None = None) -> None:
        """
        Initialise l'analyseur.

        Args:
            scraped_data_path: Chemin vers le fichier de données scrapées.
        """
        self.heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        self.scraped_data_path = scraped_data_path

    def analyze_structure(
        self,
        html_content: str,
    ) -> dict[str, Any]:
        """
        Analyse la structure HTML.

        Args:
            html_content: Contenu HTML.

        Returns:
            Structure hiérarchique analysée.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        structure = {
            'title': self._extract_title(soup),
            'sections': self._extract_sections(soup),
            'depth': self._calculate_max_depth(soup),
        }

        return structure

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extrait le titre de la page.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Titre de la page.
        """
        title_tag = soup.find('title')
        return title_tag.text.strip() if title_tag else ''

    def _extract_sections(
        self,
        soup: BeautifulSoup,
    ) -> list[dict[str, Any]]:
        """
        Extrait les sections de la page.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Liste des sections avec leur hiérarchie.
        """
        sections = []

        for heading in soup.find_all(self.heading_tags):
            section = {
                'level': int(heading.name[1]),
                'title': heading.text.strip(),
                'id': heading.get('id', ''),
            }
            sections.append(section)

        return sections

    def _calculate_max_depth(self, soup: BeautifulSoup) -> int:
        """
        Calcule la profondeur maximale de la hiérarchie.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Profondeur maximale.
        """
        max_depth = 0

        for heading in soup.find_all(self.heading_tags):
            depth = int(heading.name[1])
            if depth > max_depth:
                max_depth = depth

        return max_depth

    def extract_text_content(
        self,
        html_content: str,
    ) -> str:
        """
        Extrait le contenu textuel.

        Args:
            html_content: Contenu HTML.

        Returns:
            Contenu textuel.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Supprimer les scripts et styles
        for script in soup(['script', 'style']):
            script.decompose()

        return soup.get_text(separator=' ', strip=True)

    def analyze_hierarchy(self) -> dict[str, Any]:
        """
        Analyse la hiérarchie parent/child des documents scrapés.

        Returns:
            Rapport de hiérarchie.
        """
        if self.scraped_data_path is None or not self.scraped_data_path.exists():
            return {
                'error': 'Fichier de données scrapées non trouvé',
                'total_documents': 0,
                'hierarchy': {},
                'parent_coverage': 0.0,
                'orphan_children': 0,
                'avg_children_per_parent': 0,
            }

        with open(self.scraped_data_path, encoding='utf-8') as f:
            documents = json.load(f)

        # Construire la hiérarchie
        hierarchy: dict[str, Any] = {}

        for doc in documents:
            url = doc.get('url', '')
            parent_url = doc.get('parent_url')

            if url not in hierarchy:
                hierarchy[url] = {
                    'title': doc.get('title', ''),
                    'children': [],
                    'parent': None,
                }

            if parent_url and parent_url in hierarchy:
                hierarchy[url]['parent'] = parent_url
                if url not in hierarchy[parent_url]['children']:
                    hierarchy[parent_url]['children'].append(url)
            elif parent_url:
                # Créer le parent s'il n'existe pas
                if parent_url not in hierarchy:
                    hierarchy[parent_url] = {
                        'title': '',
                        'children': [],
                        'parent': None,
                    }
                hierarchy[url]['parent'] = parent_url
                if url not in hierarchy[parent_url]['children']:
                    hierarchy[parent_url]['children'].append(url)

        # Calculer les statistiques
        total_docs = len(documents)
        parents_with_children = [url for url, data in hierarchy.items() if data['children']]
        orphans = [url for url, data in hierarchy.items() if not data['parent']]
        orphan_children = sum(1 for url, data in hierarchy.items() if data['parent'] and data['parent'] not in hierarchy)
        
        # Calculer parent_coverage : % de documents qui ont un parent valide dans le dataset
        docs_with_valid_parent = sum(1 for url, data in hierarchy.items() if data['parent'] and data['parent'] in hierarchy)
        parent_coverage = docs_with_valid_parent / total_docs if total_docs > 0 else 0.0
        
        # Calculer avg_children_per_parent
        avg_children = len(parents_with_children) > 0 and sum(len(data['children']) for data in hierarchy.values()) / len(parents_with_children) or 0

        return {
            'total_documents': total_docs,
            'hierarchy': hierarchy,
            'orphans': orphans,
            'parent_coverage': parent_coverage,
            'orphan_children': orphan_children,
            'avg_children_per_parent': avg_children,
        }

    def generate_hierarchy_report(self) -> dict[str, Any]:
        """
        Génère le rapport de hiérarchie.

        Returns:
            Rapport détaillé de la hiérarchie.
        """
        hierarchy_data = self.analyze_hierarchy()

        if 'error' in hierarchy_data:
            return hierarchy_data

        hierarchy = hierarchy_data['hierarchy']
        orphans = hierarchy_data['orphans']

        # Calculer les statistiques
        total_docs = len(hierarchy)
        total_orphans = len(orphans)
        total_parents = sum(1 for data in hierarchy.values() if data['children'])

        # Profondeur maximale
        max_depth = 0
        for url in hierarchy:
            depth = self._calculate_document_depth(url, hierarchy)
            if depth > max_depth:
                max_depth = depth

        return {
            'total_documents': total_docs,
            'total_orphans': total_orphans,
            'total_parents': total_parents,
            'max_depth': max_depth,
            'orphans': orphans,
            'hierarchy': hierarchy,
        }

    def _calculate_document_depth(
        self,
        url: str,
        hierarchy: dict[str, Any],
    ) -> int:
        """
        Calcule la profondeur d'un document dans la hiérarchie.

        Args:
            url: URL du document.
            hierarchy: Dictionnaire de hiérarchie.

        Returns:
            Profondeur du document.
        """
        if url not in hierarchy:
            return 0

        parent = hierarchy[url]['parent']
        if parent is None:
            return 0

        return 1 + self._calculate_document_depth(parent, hierarchy)

    def save_hierarchy_report(
        self,
        report: dict[str, Any],
        output_path: Path | None = None,
    ) -> None:
        """
        Sauvegarde le rapport de hiérarchie.

        Args:
            report: Rapport de hiérarchie.
            output_path: Chemin de sortie (optionnel).
        """
        if output_path is None:
            output_path = Path(__file__).parent.parent / 'data_agentic' / 'hierarchy_report.json'

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


def main() -> None:
    """
    Point d'entrée principal pour tester l'analyseur.
    """
    analyzer = HTMLStructureAnalyzer()
    html = '<html><body><h1>Test</h1><p>Content</p></body></html>'
    structure = analyzer.analyze_structure(html)
    print(f'Structure: {structure}')


if __name__ == '__main__':
    main()
