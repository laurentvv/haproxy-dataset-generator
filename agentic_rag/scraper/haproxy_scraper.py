"""
Scraper pour la documentation HAProxy.

Ce module extrait la documentation HAProxy depuis le site officiel.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from agentic_rag.config_agentic import DATA_DIR, SCRAPER_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Seuils de qualité de contenu
MIN_CONTENT_LENGTH = 50  # Contenu trop court = ignoré
SHORT_CONTENT_LENGTH = 200  # Contenu court = warning


class HAProxyScraper:
    """
    Scraper pour la documentation HAProxy.

    Cette classe extrait la documentation HAProxy depuis le site officiel
    et la valide.
    """

    def __init__(
        self,
        base_url: str | None = None,
        version: str | None = None,
        output_dir: Path | None = None,
    ) -> None:
        """
        Initialise le scraper.

        Args:
            base_url: URL de base de la documentation.
            version: Version de HAProxy.
            output_dir: Répertoire de sortie.
        """
        self.base_url = base_url or SCRAPER_CONFIG['base_url']
        self.version = version or SCRAPER_CONFIG['version']
        self.output_dir = output_dir or DATA_DIR

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                'User-Agent': SCRAPER_CONFIG['user_agent'],
            }
        )

    def scrape_all_pages(self) -> list[dict[str, Any]]:
        """
        Scrape toutes les pages de la documentation HAProxy de manière récursive.

        Returns:
            Liste de documents scrapés.
        """
        logger.info(f'Début du scraping pour HAProxy {self.version}')

        documents = []
        visited_urls: set[str] = set()
        url_queue: list[str] = []

        # Récupérer la page d'index
        index_url = f'{self.base_url}{self.version}/intro.html'
        logger.info(f"Récupération de la page d'index: {index_url}")

        try:
            index_html = self._fetch_page(index_url)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la page d'index: {e}")
            return documents

        # Parser la page d'index
        soup = BeautifulSoup(index_html, 'html.parser')
        # Passer l'URL de base du répertoire (sans le nom du fichier)
        base_dir_url = index_url.rsplit('/', 1)[0] + '/'
        links = self._extract_links(soup, base_dir_url)

        logger.info(f'Trouvé {len(links)} liens initiaux')
        for link in links:
            logger.debug(f'  - {link}')

        # Scraper la page d'index (intro.html)
        index_docs = self.scrape_page_with_sections(index_url)
        if index_docs:
            documents.extend(index_docs)
            logger.info(f"  - {len(index_docs)} sections extraites de la page d'index")

        # Initialiser la file d'attente avec les liens de la page d'index
        url_queue.extend(links)
        visited_urls.add(index_url)

        # Scraper chaque page de manière récursive (BFS)
        while url_queue and len(documents) < SCRAPER_CONFIG['max_pages']:
            url = url_queue.pop(0)

            # Normaliser l'URL (supprimer l'ancre pour la déduplication)
            url_normalized = self._normalize_url(url)

            # Ignorer si déjà visité
            if url_normalized in visited_urls:
                logger.debug(f'URL déjà visitée: {url}')
                continue

            # Marquer comme visité
            visited_urls.add(url_normalized)

            logger.info(f'Scraping de la page {len(documents) + 1}: {url}')

            # Scraper la page et extraire les sections avec ancres
            page_docs = self.scrape_page_with_sections(url)
            if page_docs:
                documents.extend(page_docs)

                # Extraire les liens de cette page et les ajouter à la file d'attente
                try:
                    page_html = self._fetch_page(url)
                    page_soup = BeautifulSoup(page_html, 'html.parser')
                    page_base_url = url.rsplit('/', 1)[0] + '/'
                    page_links = self._extract_links(page_soup, page_base_url)

                    # Ajouter les nouveaux liens à la file d'attente
                    for link in page_links:
                        link_normalized = self._normalize_url(link)
                        if link_normalized not in visited_urls and link not in url_queue:
                            url_queue.append(link)

                    logger.debug(f'  - {len(page_links)} liens trouvés sur cette page')
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction des liens de {url}: {e}")

        # Sauvegarder les documents
        if documents:
            self.save_scraped_data(documents)

        logger.info(f'Scraping terminé: {len(documents)} documents')
        return documents

    def _normalize_url(self, url: str) -> str:
        """
        Normalise une URL en supprimant l'ancre.

        Args:
            url: URL à normaliser.

        Returns:
            URL normalisée.
        """
        if '#' in url:
            return url.split('#')[0]
        return url

    def _fetch_page(self, url: str) -> str:
        """
        Récupère le contenu d'une page.

        Args:
            url: URL de la page.

        Returns:
            Contenu HTML de la page.
        """
        response = self.session.get(url, timeout=SCRAPER_CONFIG['timeout'])
        response.raise_for_status()
        return response.text

    def _extract_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
    ) -> list[str]:
        """
        Extrait les liens de la page.

        Args:
            soup: Objet BeautifulSoup.
            base_url: URL de base.

        Returns:
            Liste des liens.
        """
        links = []

        # Chercher tous les liens avec href
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Filtrer les liens internes à la documentation
            # Accepter les liens relatifs (sans / au début) et les liens avec ./
            if (
                not href.startswith('#')  # Ignorer les ancres
                and not href.startswith('http')  # Ignorer les liens externes
                and not href.startswith('mailto')  # Ignorer les liens mailto
                and not href.startswith('ftp')  # Ignorer les liens ftp
                and not href.startswith('javascript')  # Ignorer les liens javascript
            ):
                # Construire l'URL complète
                if href.startswith('./'):
                    full_url = f'{base_url}{href[2:]}'
                elif href.startswith('/'):
                    full_url = f'{self.base_url}{href}'
                elif href.startswith('../'):
                    # Résoudre les liens relatifs vers le répertoire parent
                    # Ex: ../configuration.html -> https://docs.haproxy.org/3.2/configuration.html
                    full_url = self._resolve_relative_url(href, base_url)
                    if not full_url:
                        continue
                else:
                    # Lien relatif simple (ex: configuration.html)
                    full_url = f'{base_url}{href}'

                # Filtrer pour ne garder que les liens .html et les liens vers des répertoires
                if not (full_url.endswith('.html') or full_url.endswith('/')):
                    continue

                # Filtrer pour ne garder que les liens de la version spécifiée
                # Ex: https://docs.haproxy.org/3.2/... est OK
                # Ex: https://docs.haproxy.org/3.3/... n'est PAS OK
                version_pattern = f'/{self.version}/'
                if version_pattern not in full_url:
                    continue

                # Éviter les doublons
                if full_url not in links:
                    links.append(full_url)

        logger.debug(f'  Liens extraits: {len(links)} liens')
        for link in links:
            logger.debug(f'    - {link}')
        return links

    def _resolve_relative_url(self, href: str, base_url: str) -> str | None:
        """
        Résout les URLs relatives avec ../

        Args:
            href: URL relative (ex: "../configuration.html")
            base_url: URL de base

        Returns:
            URL résolue ou None
        """
        try:
            # Compter le nombre de ../
            level_up = href.count('../')
            if level_up == 0:
                return None

            # Extraire le chemin relatif sans les ../
            relative_path = href.replace('../', '')

            # Construire l'URL de base en remontant de level_up niveaux
            parts = base_url.rstrip('/').split('/')
            # Garder au moins le domaine et le chemin de base
            if len(parts) > level_up:
                resolved_parts = parts[:-level_up]
                resolved_url = '/'.join(resolved_parts) + '/' + relative_path
                return resolved_url

            return None
        except Exception:
            return None

    def scrape_page_with_sections(self, url: str) -> list[dict[str, Any]]:
        """
        Scrape une page spécifique et extrait toutes les sections avec ancres.

        Args:
            url: URL de la page.

        Returns:
            Liste de documents scrapés (un par section).
        """
        try:
            html = self._fetch_page(url)
        except Exception as e:
            logger.error(f'Erreur lors du scraping de {url}: {e}')
            return []

        soup = BeautifulSoup(html, 'html.parser')

        # Extraire toutes les ancres de la page
        anchors = self._extract_anchors(soup)

        if not anchors:
            # Si pas d'ancres, créer un seul document pour la page entière
            doc = {
                'url': url,
                'title': self._extract_title(soup),
                'content': self._extract_content(soup),
                'parent_url': self._extract_parent_url(url),
                'parent_title': self._extract_parent_title(soup),
                'depth': self._calculate_depth(url),
                'section_path': self._extract_section_path(soup),
                'anchor': None,
                'source_file': self._extract_source_file(soup),
            }
            # Vérifier la qualité du contenu
            if len(doc['content']) >= MIN_CONTENT_LENGTH:
                return [doc]
            else:
                logger.warning(f"  ⚠️  Contenu trop court (< {MIN_CONTENT_LENGTH} chars) pour {url}")
                return []

        # Créer un document pour chaque ancre/section
        documents = []
        empty_count = 0
        short_count = 0
        
        for anchor in anchors:
            anchor_id = anchor['id']
            anchor_text = anchor['text']

            # Extraire le contenu de cette section
            section_content = self._extract_section_content(soup, anchor_id)

            # Nettoyer et valider le contenu
            if section_content:
                section_content = self._clean_content(section_content)
            
            if not section_content or len(section_content) < MIN_CONTENT_LENGTH:
                empty_count += 1
                logger.debug(f"  ⚠️  Section ignorée (vide/trop courte): {anchor_id}")
                continue
            
            # Warning pour contenu court
            if len(section_content) < SHORT_CONTENT_LENGTH:
                short_count += 1
                logger.debug(f"  ⚠️  Section courte ({len(section_content)} chars): {anchor_id}")
            
            # Nettoyer le titre
            clean_title = self._clean_title(anchor_text)
            
            doc = {
                'url': url,  # URL sans ancre pour correspondre au format de référence
                'title': clean_title,
                'content': section_content,
                'parent_url': url,
                'parent_title': self._extract_title(soup),
                'depth': self._calculate_depth(url),
                'section_path': [clean_title],
                'anchor': anchor_id,  # Stocker l'ancre séparément
                'source_file': self._extract_source_file(soup),
            }
            documents.append(doc)

        logger.info(f'  - {len(documents)} sections valides extraites ({empty_count} vides, {short_count} courtes)')
        return documents

    def _extract_anchors(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """
        Extrait toutes les ancres de la page.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Liste des ancres avec leur texte.
        """
        anchors = []

        # Chercher tous les éléments avec un attribut id
        for element in soup.find_all(attrs={'id': True}):
            element_id = element['id']

            # Ignorer les ancres spéciales (tab-summary, etc.)
            if element_id.startswith('tab-'):
                continue

            # Essayer d'extraire le texte de l'élément
            # Chercher d'abord un heading (h1-h6) dans l'élément
            heading = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading:
                text = heading.get_text(strip=True)
            else:
                # Sinon, utiliser le texte de l'élément lui-même
                text = element.get_text(strip=True)

            if text:
                anchors.append({'id': element_id, 'text': text})

        return anchors

    def _clean_title(self, title: str) -> str:
        """
        Nettoie un titre en supprimant les caractères spéciaux et normalisant.
        
        Args:
            title: Titre brut.
            
        Returns:
            Titre nettoyé.
        """
        # Supprimer les espaces multiples
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Supprimer les caractères spéciaux indésirables
        title = title.replace('\n', ' ').replace('\r', '')
        
        # Limiter la longueur
        if len(title) > 200:
            title = title[:200].strip()
        
        return title

    def _clean_content(self, content: str) -> str:
        """
        Nettoie le contenu d'une section.
        
        Args:
            content: Contenu brut.
            
        Returns:
            Contenu nettoyé.
        """
        # Supprimer les espaces multiples (mais garder les sauts de ligne)
        content = re.sub(r'[ \t]+', ' ', content).strip()
        
        # Supprimer les sauts de ligne multiples (garder les sauts simples)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Supprimer les caractères spéciaux indésirables
        content = content.replace('\r', '')
        
        return content

    def _extract_section_content(
        self,
        soup: BeautifulSoup,
        anchor_id: str,
    ) -> str | None:
        """
        Extrait le contenu d'une section spécifique.

        Args:
            soup: Objet BeautifulSoup.
            anchor_id: ID de l'ancre.

        Returns:
            Contenu de la section ou None.
        """
        # Trouver l'élément avec l'ID spécifié
        section = soup.find(id=anchor_id)
        if not section:
            return None

        # Extraire le contenu de la section jusqu'à la prochaine section de même niveau
        content_parts = [section.get_text(separator='\n', strip=True)]

        # Chercher les éléments frères jusqu'à la prochaine section de même niveau
        current = section.find_next_sibling()
        while current:
            # Si on trouve un élément avec un ID, on s'arrête
            if current.get('id'):
                break

            # Ajouter le texte de l'élément
            text = current.get_text(separator='\n', strip=True)
            if text:
                content_parts.append(text)

            current = current.find_next_sibling()

        return '\n'.join(content_parts)

    def scrape_page(self, url: str) -> dict[str, Any] | None:
        """
        Scrape une page spécifique.

        Args:
            url: URL de la page.

        Returns:
            Document scrapé ou None.
        """
        try:
            html = self._fetch_page(url)
        except Exception as e:
            logger.error(f'Erreur lors du scraping de {url}: {e}')
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extraire les métadonnées
        doc = {
            'url': url,
            'title': self._extract_title(soup),
            'content': self._extract_content(soup),
            'parent_url': self._extract_parent_url(url),
            'parent_title': self._extract_parent_title(soup),
            'depth': self._calculate_depth(url),
            'section_path': self._extract_section_path(soup),
            'anchor': self._extract_anchor(url),
            'source_file': self._extract_source_file(soup),
        }

        return doc

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extrait le titre de la page.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Titre de la page.
        """
        # Chercher le titre h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        # Sinon, utiliser le titre de la page
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else ''

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extrait le contenu principal de la page.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Contenu textuel de la page.
        """
        # Chercher le contenu principal
        main_content = soup.find('main') or soup.find('article') or soup.find('body')

        if main_content:
            # Supprimer les scripts et styles
            for element in main_content(['script', 'style', 'nav', 'footer']):
                element.decompose()

            return main_content.get_text(separator='\n', strip=True)

        return soup.get_text(separator='\n', strip=True)

    def _extract_parent_url(self, url: str) -> str | None:
        """
        Extrait l'URL parente.

        Args:
            url: URL de la page.

        Returns:
            URL parente ou None.
        """
        # Supprimer le dernier segment de l'URL
        parts = url.rstrip('/').split('/')
        if len(parts) > 1:
            parent_url = '/'.join(parts[:-1])
            return parent_url if parent_url != self.base_url else None
        return None

    def _extract_parent_title(self, soup: BeautifulSoup) -> str | None:
        """
        Extrait le titre parent.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Titre parent ou None.
        """
        # Chercher un lien de navigation vers le parent
        breadcrumb = soup.find('nav', class_='breadcrumb')
        if breadcrumb:
            links = breadcrumb.find_all('a')
            if len(links) > 1:
                return links[-2].get_text(strip=True)
        return None

    def _calculate_depth(self, url: str) -> int:
        """
        Calcule la profondeur de la page dans la hiérarchie.

        Args:
            url: URL de la page.

        Returns:
            Profondeur de la page.
        """
        # Compter les segments de l'URL après la version
        version_part = f'/{self.version}/'
        if version_part in url:
            parts = url.split(version_part)[1].split('/')
            return len(parts) - 1
        return 0

    def _extract_section_path(self, soup: BeautifulSoup) -> list[str]:
        """
        Extrait le chemin de section.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Liste des sections (limité à 5 pour éviter la concaténation excessive).
        """
        path = []

        # Chercher les headings (limité à 5 pour éviter la concaténation)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], limit=5)
        for heading in headings:
            text = heading.get_text(strip=True)
            if text and len(text) < 100:  # Ignorer les titres trop longs
                path.append(text)

        return path

    def _extract_anchor(self, url: str) -> str | None:
        """
        Extrait l'ancre de l'URL.

        Args:
            url: URL de la page.

        Returns:
            Ancre ou None.
        """
        if '#' in url:
            return url.split('#')[-1]
        return None

    def _extract_source_file(self, soup: BeautifulSoup) -> str | None:
        """
        Extrait le fichier source.

        Args:
            soup: Objet BeautifulSoup.

        Returns:
            Fichier source ou None.
        """
        # Chercher un lien vers le source
        source_link = soup.find('a', href=lambda x: x and 'source' in x.lower())
        if source_link:
            return source_link['href']
        return None

    def save_scraped_data(self, data: list[dict[str, Any]]) -> None:
        """
        Sauvegarde les données scrapées dans un fichier.

        Args:
            data: Liste de documents scrapés.
        """
        output_file = self.output_dir / f'scraped_{self.version}.json'

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f'Données sauvegardées dans {output_file}')

    def load_scraped_data(self) -> list[dict[str, Any]]:
        """
        Charge les données scrapées depuis un fichier.

        Returns:
            Liste de documents scrapés ou liste vide si le fichier n'existe pas.
        """
        output_file = self.output_dir / f'scraped_{self.version}.json'

        if not output_file.exists():
            logger.warning(f'Fichier {output_file} non trouvé')
            return []

        with open(output_file, encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f'Données chargées depuis {output_file}: {len(data)} documents')
        return data


def main() -> None:
    """
    Point d'entrée principal.
    """
    scraper = HAProxyScraper()
    documents = scraper.scrape()
    print(f'Documents scrapés: {len(documents)}')


if __name__ == '__main__':
    main()
