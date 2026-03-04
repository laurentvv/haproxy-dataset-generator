"""
Comparaison avec le projet principal.

Ce module compare les résultats du scraping avec le projet principal.
"""

import json
from pathlib import Path
from typing import Any

# Ajouter le répertoire parent au path pour les imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_agentic import DATA_DIR, SCRAPED_PAGES_PATH


class ReferenceComparator:
    """
    Comparateur avec le projet principal.

    Cette classe compare les résultats du scraping agentic
    avec ceux du projet principal.
    """

    def __init__(
        self,
        reference_data_path: Path | None = None,
        scraped_data_path: Path | None = None,
    ) -> None:
        """
        Initialise le comparateur.

        Args:
            reference_data_path: Chemin vers les données de référence.
            scraped_data_path: Chemin vers les données scrapées.
        """
        self.reference_data_path = (
            reference_data_path
            or Path(__file__).parent.parent.parent / 'data' / 'sections_enriched.jsonl'
        )
        self.scraped_data_path = scraped_data_path or SCRAPED_PAGES_PATH

    def compare_documents(self) -> dict[str, Any]:
        """
        Compare les documents des deux projets.

        Returns:
            Résultats de la comparaison.
        """
        reference_docs = self._load_documents(self.reference_data_path)
        agentic_docs = self._load_documents(self.scraped_data_path)

        comparison = {
            'reference_count': len(reference_docs),
            'agentic_count': len(agentic_docs),
            'overlap': self._calculate_overlap(reference_docs, agentic_docs),
            'missing': self._find_missing(reference_docs, agentic_docs),
            'coverage_percentage': 0.0,
        }

        # Calculer le pourcentage de couverture
        if comparison['reference_count'] > 0:
            comparison['coverage_percentage'] = (
                comparison['overlap'] / comparison['reference_count']
            ) * 100

        return comparison

    def compare_coverage(self) -> dict[str, Any]:
        """
        Compare la couverture des documents.

        Returns:
            Résultats de la comparaison de couverture.
        """
        reference_docs = self._load_documents(self.reference_data_path)
        agentic_docs = self._load_documents(self.scraped_data_path)
        
        # Extraire les URLs et sections
        ref_urls = self._extract_urls(reference_docs)
        agt_urls = self._extract_urls(agentic_docs)
        ref_sections = self._extract_sections(reference_docs)
        agt_sections = self._extract_sections(agentic_docs)
        ref_volume = self._extract_content_volume(reference_docs)
        agt_volume = self._extract_content_volume(agentic_docs)
        
        # URLs manquantes et supplémentaires
        missing_urls = sorted(ref_urls - agt_urls)
        extra_urls = sorted(agt_urls - ref_urls)
        missing_sections = sorted(ref_sections - agt_sections)
        
        # Calculer la couverture
        coverage_percentage = (agt_volume['total_chars'] / ref_volume['total_chars'] * 100) if ref_volume['total_chars'] else 0
        
        return {
            'reference_entries': ref_volume['entries'],
            'agentic_entries': agt_volume['entries'],
            'content_coverage_pct': round(coverage_percentage, 2),
            'coverage_percentage': round(coverage_percentage, 2),  # Alias pour compatibilité
            'missing_urls': missing_urls,
            'missing_sections': missing_sections,
            'extra_urls_count': len(extra_urls),
            'meets_threshold': coverage_percentage >= 95.0,
            'threshold': 95.0,
        }
    
    def _extract_urls(self, data: list[dict[str, Any]]) -> set[str]:
        """
        Extrait toutes les URLs ou identifiants uniques d'un dataset.
        
        Args:
            data: Liste de documents.
            
        Returns:
            Set d' URLs normalisées (sans ancres)
        """
        urls = set()
        for entry in data:
            if isinstance(entry, dict):
                url = entry.get("url") or entry.get("source") or entry.get("id", "")
                if url:
                    urls.add(url.split("#")[0])  # normaliser : ignorer les ancres
        return urls
    
    def _extract_sections(self, data: list[dict[str, Any]]) -> set[str]:
        """
        Extrait les titres de sections uniques.
        
        Args:
            data: Liste de documents.
            
        Returns:
            Set de titres de sections
        """
        sections = set()
        for entry in data:
            if isinstance(entry, dict):
                title = entry.get("title") or entry.get("section") or ""
                if title:
                    sections.add(title.strip())
        return sections
    
    def _extract_content_volume(self, data: list[dict[str, Any]]) -> dict[str, int]:
        """
        Calcule le volume de contenu total et par section.
        
        Args:
            data: Liste de documents.
            
        Returns:
            Dict avec total_chars et entries
        """
        total_chars = sum(
            len(e.get("content", "") or e.get("text", "")) 
            for e in data if isinstance(e, dict)
        )
        return {"total_chars": total_chars, "entries": len(data)}

    def _load_documents(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Charge les documents depuis un fichier.

        Args:
            file_path: Chemin du fichier.

        Returns:
            Liste de documents.
        """
        if not file_path.exists():
            return []

        documents = []

        # Charger JSONL ou JSON
        if file_path.suffix == '.jsonl':
            with open(file_path, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            documents.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Ignorer les lignes corrompues et continuer
                            continue
        elif file_path.suffix == '.json':
            with open(file_path, encoding='utf-8') as f:
                documents = json.load(f)

        return documents

    def _calculate_overlap(
        self,
        docs1: list[dict[str, Any]],
        docs2: list[dict[str, Any]],
    ) -> int:
        """
        Calcule le chevauchement entre deux listes de documents.

        Args:
            docs1: Première liste de documents.
            docs2: Deuxième liste de documents.

        Returns:
            Nombre de documents en commun.
        """

        # Extraire les URLs et les ancres pour comparer
        # Format: url + "#" + anchor (si présent)
        def get_doc_key(doc: dict[str, Any]) -> str:
            url = doc.get('url', '')
            anchor = doc.get('anchor', '')
            if anchor:
                return f'{url}#{anchor}'
            return url

        keys1 = {get_doc_key(doc) for doc in docs1}
        keys2 = {get_doc_key(doc) for doc in docs2}

        # Calculer l'intersection
        overlap = keys1 & keys2
        return len(overlap)

    def _find_missing(
        self,
        reference_docs: list[dict[str, Any]],
        agentic_docs: list[dict[str, Any]],
    ) -> list[str]:
        """
        Trouve les documents manquants.

        Args:
            reference_docs: Documents de référence.
            agentic_docs: Documents agentic.

        Returns:
            Liste des documents manquants.
        """
        # Extraire les URLs ou identifiants uniques
        reference_urls = {doc.get('url', doc.get('id', '')) for doc in reference_docs}
        agentic_urls = {doc.get('url', doc.get('id', '')) for doc in agentic_docs}

        # Trouver les URLs manquantes
        missing = reference_urls - agentic_urls
        return list(missing)

    def generate_diff_report(self) -> dict[str, Any]:
        """
        Génère le rapport de différences.

        Returns:
            Rapport détaillé des différences.
        """
        comparison = self.compare_coverage()

        return {
            'reference_count': comparison['reference_count'],
            'agentic_count': comparison['agentic_count'],
            'overlap': comparison['overlap'],
            'missing': comparison['missing'],
            'coverage_percentage': comparison['coverage_percentage'],
            'meets_threshold': comparison['meets_threshold'],
            'threshold': comparison['threshold'],
            'summary': self._generate_summary(comparison),
        }

    def _generate_summary(self, comparison: dict[str, Any]) -> str:
        """
        Génère un résumé de la comparaison.

        Args:
            comparison: Résultats de la comparaison.

        Returns:
            Résumé textuel.
        """
        if comparison['meets_threshold']:
            return (
                f'La couverture est de {comparison["coverage_percentage"]:.2f}%, '
                f'ce qui dépasse le seuil de {comparison["threshold"]}%. '
                f'{len(comparison["missing"])} documents manquants.'
            )
        else:
            return (
                f'La couverture est de {comparison["coverage_percentage"]:.2f}%, '
                f'ce qui est en dessous du seuil de {comparison["threshold"]}%. '
                f'{len(comparison["missing"])} documents manquants.'
            )

    def save_diff_report(
        self,
        report: dict[str, Any],
        output_path: Path | None = None,
    ) -> None:
        """
        Sauvegarde le rapport de différences.

        Args:
            report: Rapport de différences.
            output_path: Chemin de sortie (optionnel).
        """
        if output_path is None:
            output_path = DATA_DIR / 'diff_report.json'

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


def main() -> None:
    """
    Point d'entrée principal.
    """
    comparator = ReferenceComparator()
    comparison = comparator.compare_documents()
    print(f'Comparaison: {comparison}')


if __name__ == '__main__':
    main()
