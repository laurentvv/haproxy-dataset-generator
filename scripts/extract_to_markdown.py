import requests
import json
from bs4 import BeautifulSoup, NavigableString
import re
from urllib.parse import urljoin
from pathlib import Path

def fetch_url(url):
    """Télécharge le contenu HTML d'une URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la requête HTTP vers {url}: {e}")
        return None

def html_to_markdown(element):
    """Convertit un élément BeautifulSoup en format Markdown simplifié."""
    if isinstance(element, NavigableString):
        # Nettoyer et retourner le texte
        text = str(element).strip()
        # Remplacer les doubles espaces ou tabulations par un espace simple
        text = re.sub(r'\s+', ' ', text)
        return text

    if element.name == 'p':
        # Paragraphe : ajouter une nouvelle ligne après
        content = ''.join(html_to_markdown(child) for child in element.children)
        return content + '\n\n'

    if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        # Titres : les convertir en format Markdown
        level = int(element.name[1])
        content = ''.join(html_to_markdown(child) for child in element.children)
        return '#' * level + ' ' + content + '\n\n'

    if element.name == 'code':
        # Code inline : le mettre entre backticks
        content = ''.join(html_to_markdown(child) for child in element.children)
        return f'`{content}`'

    if element.name == 'pre':
        # Blocs de code : les préserver
        code_content = element.get_text()
        return f'```\n{code_content}\n```\n\n'

    if element.name == 'a':
        # Liens : les convertir en format Markdown
        href = element.get('href', '')
        content = ''.join(html_to_markdown(child) for child in element.children)
        if href:
            return f'[{content}]({href})'
        else:
            return content

    if element.name in ['ul', 'ol']:
        # Listes : les convertir en Markdown
        items = []
        for child in element.children:
            if child.name == 'li':
                item_content = ''.join(html_to_markdown(grandchild) for grandchild in child.children)
                items.append(item_content)

        markdown_items = []
        for i, item in enumerate(items):
            if element.name == 'ul':
                markdown_items.append(f'- {item}')
            else:  # ol
                markdown_items.append(f'{i+1}. {item}')

        return '\n'.join(markdown_items) + '\n\n'

    if element.name in ['strong', 'b']:
        # Gras : le convertir en format Markdown
        content = ''.join(html_to_markdown(child) for child in element.children)
        return f'**{content}**'

    if element.name in ['em', 'i']:
        # Italique : le convertir en format Markdown
        content = ''.join(html_to_markdown(child) for child in element.children)
        return f'*{content}*'

    # Pour tous les autres éléments, récursivement traiter les enfants
    if element.name:
        # Si c'est une balise HTML, traiter récursivement les enfants
        return ''.join(html_to_markdown(child) for child in element.children)

    # Retourner le texte tel quel
    return str(element)

def extract_markdown_sections(soup, base_url):
    """Extrait les sections (séparées par des H1 ou H2) en Markdown."""
    sections = []

    # Gestion spécifique pour la page de management qui utilise des ancres pour les chapitres
    if "management.html" in base_url:
        # Pour management.html, les chapitres sont organisés autour des ancres <a class="anchor" id="X">
        # Mais seules les ancres avec des IDs numériques simples correspondent aux chapitres principaux
        all_anchors = soup.find_all('a', class_='anchor')

        # Extraire toutes les ancres numériques (y compris les sous-sections comme "9.1", "9.4.1", "13.1")
        all_numbered_anchors = []
        for anchor in all_anchors:
            anchor_id = anchor.get('id', '')
            if anchor_id:
                parts = anchor_id.split('.')
                # Conserver les ancres avec ID numérique comme "1", "2", "9.1", "9.4.1", "13.1", etc.
                if all(part.isdigit() for part in parts):
                    all_numbered_anchors.append(anchor)

        if all_numbered_anchors:
            # Get all direct children of the body
            all_body_contents = list(soup.body.children) if soup.body else []

            # Process each numbered anchor and the content that follows it until the next numbered anchor
            for i, anchor in enumerate(all_numbered_anchors):
                anchor_id = anchor.get('id', '')

                # Find the heading associated with this anchor
                # Look for the heading based on the pattern: anchor -> potentially some elements -> heading
                next_h1 = None
                sibling = anchor.next_sibling

                # Look for the associated heading after the anchor (might be a few elements away)
                while sibling:
                    if hasattr(sibling, 'name'):
                        if sibling.name == 'h1':
                            next_h1 = sibling
                            break
                        elif sibling.name == 'div' and sibling.get('class', []) and 'page-header' in sibling.get('class', []):
                            # Check if this div contains the heading we're looking for
                            inner_h1 = sibling.find('h1')
                            if inner_h1:
                                next_h1 = inner_h1
                                break
                    sibling = sibling.next_sibling

                # Extract title from the H1
                title = ""
                if next_h1:
                    # Get the text content but try to exclude the small section number link
                    # For structures like <h1><small>9.1.</small> CSV format</h1>
                    title = ""

                    # Extract text after any "small" elements or similar that might contain the section number
                    if next_h1.find('small'):
                        # If there's a small element, get text after it
                        small_elem = next_h1.find('small')
                        # Get text that comes after the small element
                        text_after_small = ""
                        next_node = small_elem.next_sibling
                        while next_node:
                            if isinstance(next_node, str):
                                text_after_small += next_node
                            elif hasattr(next_node, 'get_text'):
                                text_after_small += next_node.get_text()
                            next_node = next_node.next_sibling
                        title = text_after_small.strip()
                    else:
                        # If no small element, get all text and try to split by the section number from anchor_id
                        full_text = next_h1.get_text().strip()
                        if anchor_id and full_text.startswith(anchor_id):
                            title = full_text[len(anchor_id):].strip()
                            if title.startswith('.'):
                                title = title[1:].strip()
                        else:
                            title = full_text

                    # Clean up any extra whitespace
                    title = title.strip()

                    # Add the section number back
                    if title:
                        title = f"{anchor_id}. {title}"
                    else:
                        title = anchor_id
                else:
                    # If no heading found, use the anchor ID as the title
                    title = anchor_id

                # Find the content between this anchor and the next numbered anchor
                content_elements = []

                # Find position of the anchor in the body
                try:
                    anchor_pos = all_body_contents.index(anchor)

                    # Collect elements after this anchor until the next numbered anchor
                    next_anchor = None
                    for j in range(i + 1, len(all_numbered_anchors)):
                        if all_numbered_anchors[j] in all_body_contents:
                            next_anchor = all_numbered_anchors[j]
                            break

                    if next_anchor and next_anchor in all_body_contents:
                        next_anchor_pos = all_body_contents.index(next_anchor)
                        content_elements = all_body_contents[anchor_pos + 1:next_anchor_pos]
                    else:
                        # No more numbered anchors, get content until the end of main content
                        for j in range(anchor_pos + 1, len(all_body_contents)):
                            element = all_body_contents[j]
                            # Stop if we reach the next numbered anchor
                            if element in all_numbered_anchors:
                                break
                            content_elements.append(element)
                except ValueError:
                    # Anchor not in body children, fallback to previous sibling method
                    next_element = anchor.next_sibling
                    while next_element:
                        if next_element in all_numbered_anchors:
                            break
                        content_elements.append(next_element)
                        next_element = next_element.next_sibling

                # Convertir le contenu en Markdown
                content = ''.join(html_to_markdown(element) for element in content_elements if element and (hasattr(element, 'name') or (isinstance(element, str) and element.strip())))

                sections.append({
                    "title": title,
                    "content": content,
                    "url": base_url
                })

            # Handle content before the first numbered anchor if it exists
            if all_body_contents and all_numbered_anchors and all_numbered_anchors[0] in all_body_contents:
                first_anchor = all_numbered_anchors[0]
                first_anchor_pos = all_body_contents.index(first_anchor)
                header_content = all_body_contents[:first_anchor_pos]

                if header_content:
                    content = ''.join(html_to_markdown(element) for element in header_content if element and (hasattr(element, 'name') or (isinstance(element, str) and element.strip())))
                    if content.strip():
                        sections.insert(0, {
                            "title": "",  # Empty title for content before first anchor
                            "content": content,
                            "url": base_url
                        })
        else:
            # Si aucune ancre trouvée, on traite comme avant
            h1_tags = soup.find_all(['h1'])
            all_body_contents = list(soup.body.children) if soup.body else []

            if h1_tags:
                # Handle content before the first H1
                first_h1 = h1_tags[0]
                elements_before_first = []
                for child in all_body_contents:
                    if child == first_h1:
                        break
                    elements_before_first.append(child)

                if elements_before_first:
                    content = ''.join(html_to_markdown(element) for element in elements_before_first if element)
                    if content.strip():
                        sections.append({
                            "title": "",  # Empty title for content before first heading
                            "content": content,
                            "url": base_url
                        })

                # Process each H1 tag and content following it
                for i, h1_tag in enumerate(h1_tags):
                    title = h1_tag.get_text().strip()

                    # Find the position of this H1 in the body
                    h1_idx = all_body_contents.index(h1_tag) if h1_tag in all_body_contents else -1

                    if h1_idx != -1:
                        # Get content between this H1 and the next H1 (or end of body)
                        content_elements = []

                        # Start from the element right after this H1
                        for j in range(h1_idx + 1, len(all_body_contents)):
                            element = all_body_contents[j]
                            # Stop if we reach the next H1
                            if element in h1_tags:
                                break
                            content_elements.append(element)
                    else:
                        # Fallback if H1 not found in body children
                        content_elements = []
                        next_element = h1_tag.next_sibling
                        while next_element:
                            if hasattr(next_element, 'name') and next_element.name == 'h1':
                                break
                            content_elements.append(next_element)
                            next_element = next_element.next_sibling

                    # Convertir le contenu en Markdown
                    content = ''.join(html_to_markdown(element) for element in content_elements if element and (hasattr(element, 'name') or (isinstance(element, str) and element.strip())))

                    sections.append({
                        "title": title,
                        "content": content,
                        "url": base_url
                    })
    else:
        # Pour les autres pages, utiliser la logique originale avec H2
        h2_tags = soup.find_all(['h2'])

        if not h2_tags:
            # Si pas de H2, prendre tout le contenu comme une seule section
            content = ''.join(html_to_markdown(child) for child in soup.body.children if child.name not in ['h1', 'h2'])
            title = soup.find('h1').get_text().strip() if soup.find('h1') else 'Documentation HAProxy'
            sections.append({
                "title": title,
                "content": content,
                "url": base_url
            })
        else:
            # Extraire les sections entre les H2
            for i, h2_tag in enumerate(h2_tags):
                title = h2_tag.get_text().strip()

                # Récupérer le contenu jusqu'au prochain H2 ou la fin
                content_elements = []
                next_element = h2_tag.next_sibling

                while next_element:
                    if hasattr(next_element, 'name') and next_element.name in ['h2', 'h1']:
                        # Arrêter si on atteint un autre H2 ou H1
                        break
                    content_elements.append(next_element)
                    next_element = next_element.next_sibling

                # Convertir le contenu en Markdown
                content = ''.join(html_to_markdown(element) for element in content_elements)

                sections.append({
                    "title": title,
                    "content": content,
                    "url": base_url
                })

    return sections


def main():
    urls = [
        "https://docs.haproxy.org/3.2/intro.html",
        "https://docs.haproxy.org/3.2/configuration.html",
        "https://docs.haproxy.org/3.2/management.html",
    ]
    
    all_sections = []
    
    for url in urls:
        html_content = fetch_url(url)
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            sections = extract_markdown_sections(soup, url)
            all_sections.extend(sections)
            print(f"[INFO] Extrait {len(sections)} sections depuis {url}")

    # Utilisation de pathlib pour gérer les chemins de fichiers
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "sections.jsonl"

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for section in all_sections:
                f.write(json.dumps(section, ensure_ascii=False) + '\n')
        
        print(f"\n[SUCCESS] {len(all_sections)} sections Markdown sauvegardées dans {output_path}")

    except IOError as e:
        print(f"\n[ERROR] Erreur lors de l'écriture du fichier {output_path}: {e}")

if __name__ == "__main__":
    main()