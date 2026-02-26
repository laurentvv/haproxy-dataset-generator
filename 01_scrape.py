import requests
import json
from bs4 import BeautifulSoup, NavigableString
import re
from pathlib import Path


def fetch_url(url, timeout=30):
    """Télécharge le contenu HTML d'une URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête HTTP vers {url}: {e}")
        return None


def html_to_markdown(element):
    """Convertit un élément BeautifulSoup en format Markdown simplifié."""
    if isinstance(element, NavigableString):
        text = str(element).strip()
        text = re.sub(r"\s+", " ", text)
        return text

    if element.name == "p":
        content = "".join(html_to_markdown(child) for child in element.children)
        return content + "\n\n"

    if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        level = int(element.name[1])
        content = "".join(html_to_markdown(child) for child in element.children)
        return "#" * level + " " + content + "\n\n"

    if element.name == "code":
        content = "".join(html_to_markdown(child) for child in element.children)
        return f"`{content}`"

    if element.name == "pre":
        code_content = element.get_text()
        return f"```\n{code_content}\n```\n\n"

    if element.name == "a":
        href = element.get("href", "")
        content = "".join(html_to_markdown(child) for child in element.children)
        if href:
            return f"[{content}]({href})"
        else:
            return content

    if element.name in ["ul", "ol"]:
        items = []
        for child in element.children:
            if child.name == "li":
                item_content = "".join(
                    html_to_markdown(grandchild) for grandchild in child.children
                )
                items.append(item_content)
        markdown_items = []
        for i, item in enumerate(items):
            if element.name == "ul":
                markdown_items.append(f"- {item}")
            else:
                markdown_items.append(f"{i + 1}. {item}")
        return "\n".join(markdown_items) + "\n\n"

    if element.name in ["strong", "b"]:
        content = "".join(html_to_markdown(child) for child in element.children)
        return f"**{content}**"

    if element.name in ["em", "i"]:
        content = "".join(html_to_markdown(child) for child in element.children)
        return f"*{content}*"

    if element.name:
        return "".join(html_to_markdown(child) for child in element.children)

    return str(element)


def extract_markdown_sections(soup, base_url):
    """Extrait les sections (séparées par des H1 ou H2) en Markdown."""
    sections = []

    if "management.html" in base_url:
        all_anchors = soup.find_all("a", class_="anchor")
        all_numbered_anchors = []
        for anchor in all_anchors:
            anchor_id = anchor.get("id", "")
            if anchor_id:
                parts = anchor_id.split(".")
                if all(part.isdigit() for part in parts):
                    all_numbered_anchors.append(anchor)

        if all_numbered_anchors:
            all_body_contents = list(soup.body.children) if soup.body else []

            for i, anchor in enumerate(all_numbered_anchors):
                anchor_id = anchor.get("id", "")
                next_h1 = None
                sibling = anchor.next_sibling

                while sibling:
                    if hasattr(sibling, "name"):
                        if sibling.name == "h1":
                            next_h1 = sibling
                            break
                        elif (
                            sibling.name == "div"
                            and sibling.get("class", [])
                            and "page-header" in sibling.get("class", [])
                        ):
                            inner_h1 = sibling.find("h1")
                            if inner_h1:
                                next_h1 = inner_h1
                                break
                    sibling = sibling.next_sibling

                title = ""
                if next_h1:
                    title = ""
                    if next_h1.find("small"):
                        small_elem = next_h1.find("small")
                        text_after_small = ""
                        next_node = small_elem.next_sibling
                        while next_node:
                            if isinstance(next_node, str):
                                text_after_small += next_node
                            elif hasattr(next_node, "get_text"):
                                text_after_small += next_node.get_text()
                            next_node = next_node.next_sibling
                        title = text_after_small.strip()
                    else:
                        full_text = next_h1.get_text().strip()
                        if anchor_id and full_text.startswith(anchor_id):
                            title = full_text[len(anchor_id) :].strip()
                            if title.startswith("."):
                                title = title[1:].strip()
                        else:
                            title = full_text
                    title = title.strip()
                    if title:
                        title = f"{anchor_id}. {title}"
                    else:
                        title = anchor_id
                else:
                    title = anchor_id

                content_elements = []
                try:
                    anchor_pos = all_body_contents.index(anchor)
                    next_anchor = None
                    for j in range(i + 1, len(all_numbered_anchors)):
                        if all_numbered_anchors[j] in all_body_contents:
                            next_anchor = all_numbered_anchors[j]
                            break

                    if next_anchor and next_anchor in all_body_contents:
                        next_anchor_pos = all_body_contents.index(next_anchor)
                        content_elements = all_body_contents[
                            anchor_pos + 1 : next_anchor_pos
                        ]
                    else:
                        for j in range(anchor_pos + 1, len(all_body_contents)):
                            element = all_body_contents[j]
                            if element in all_numbered_anchors:
                                break
                            content_elements.append(element)
                except ValueError:
                    next_element = anchor.next_sibling
                    while next_element:
                        if next_element in all_numbered_anchors:
                            break
                        content_elements.append(next_element)
                        next_element = next_element.next_sibling

                content = "".join(
                    html_to_markdown(element)
                    for element in content_elements
                    if element
                    and (
                        hasattr(element, "name")
                        or (isinstance(element, str) and element.strip())
                    )
                )
                sections.append({"title": title, "content": content, "url": base_url})

            if (
                all_body_contents
                and all_numbered_anchors
                and all_numbered_anchors[0] in all_body_contents
            ):
                first_anchor = all_numbered_anchors[0]
                first_anchor_pos = all_body_contents.index(first_anchor)
                header_content = all_body_contents[:first_anchor_pos]
                if header_content:
                    content = "".join(
                        html_to_markdown(element)
                        for element in header_content
                        if element
                        and (
                            hasattr(element, "name")
                            or (isinstance(element, str) and element.strip())
                        )
                    )
                    if content.strip():
                        sections.insert(
                            0, {"title": "", "content": content, "url": base_url}
                        )
        else:
            h1_tags = soup.find_all(["h1"])
            all_body_contents = list(soup.body.children) if soup.body else []
            if h1_tags:
                first_h1 = h1_tags[0]
                elements_before_first = []
                for child in all_body_contents:
                    if child == first_h1:
                        break
                    elements_before_first.append(child)
                if elements_before_first:
                    content = "".join(
                        html_to_markdown(element)
                        for element in elements_before_first
                        if element
                    )
                    if content.strip():
                        sections.append(
                            {"title": "", "content": content, "url": base_url}
                        )
                for i, h1_tag in enumerate(h1_tags):
                    title = h1_tag.get_text().strip()
                    h1_idx = (
                        all_body_contents.index(h1_tag)
                        if h1_tag in all_body_contents
                        else -1
                    )
                    if h1_idx != -1:
                        content_elements = []
                        for j in range(h1_idx + 1, len(all_body_contents)):
                            element = all_body_contents[j]
                            if element in h1_tags:
                                break
                            content_elements.append(element)
                    else:
                        content_elements = []
                        next_element = h1_tag.next_sibling
                        while next_element:
                            if (
                                hasattr(next_element, "name")
                                and next_element.name == "h1"
                            ):
                                break
                            content_elements.append(next_element)
                            next_element = next_element.next_sibling
                    content = "".join(
                        html_to_markdown(element)
                        for element in content_elements
                        if element
                        and (
                            hasattr(element, "name")
                            or (isinstance(element, str) and element.strip())
                        )
                    )
                    sections.append(
                        {"title": title, "content": content, "url": base_url}
                    )

    elif "configuration.html" in base_url:
        # Configuration page: use numbered anchors (section IDs like "1", "2.1", "5.2", etc.)
        all_anchors = soup.find_all("a", class_="anchor")
        all_numbered_anchors = []
        for anchor in all_anchors:
            anchor_id = anchor.get("id", "")
            if anchor_id:
                # Match section IDs: "1", "2.1", "5.2.3", etc.
                parts = anchor_id.split(".")
                if all(part.isdigit() for part in parts):
                    all_numbered_anchors.append(anchor)

        if all_numbered_anchors:
            all_body_contents = list(soup.body.children) if soup.body else []

            for i, anchor in enumerate(all_numbered_anchors):
                anchor_id = anchor.get("id", "")

                # Find the associated heading (h1-h6) after the anchor
                heading = None
                sibling = anchor.next_sibling
                while sibling:
                    if hasattr(sibling, "name"):
                        if sibling.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                            heading = sibling
                            break
                        # Also check for headings inside divs
                        if sibling.name == "div":
                            inner_heading = sibling.find(
                                ["h1", "h2", "h3", "h4", "h5", "h6"]
                            )
                            if inner_heading:
                                heading = inner_heading
                                break
                    sibling = sibling.next_sibling

                title = ""
                if heading:
                    title = heading.get_text().strip()
                    # Avoid duplicating the section number if it's already in the anchor_id
                    if title.startswith(anchor_id):
                        title = title[len(anchor_id) :].strip()
                        if title.startswith("."):
                            title = title[1:].strip()
                    title = f"{anchor_id}. {title}" if title else anchor_id
                else:
                    title = anchor_id

                content_elements = []
                try:
                    anchor_pos = all_body_contents.index(anchor)
                    next_anchor = None
                    for j in range(i + 1, len(all_numbered_anchors)):
                        if all_numbered_anchors[j] in all_body_contents:
                            next_anchor = all_numbered_anchors[j]
                            break

                    if next_anchor and next_anchor in all_body_contents:
                        next_anchor_pos = all_body_contents.index(next_anchor)
                        content_elements = all_body_contents[
                            anchor_pos + 1 : next_anchor_pos
                        ]
                    else:
                        for j in range(anchor_pos + 1, len(all_body_contents)):
                            element = all_body_contents[j]
                            if element in all_numbered_anchors:
                                break
                            content_elements.append(element)
                except ValueError:
                    next_element = anchor.next_sibling
                    while next_element:
                        if next_element in all_numbered_anchors:
                            break
                        content_elements.append(next_element)
                        next_element = next_element.next_sibling

                content = "".join(
                    html_to_markdown(element)
                    for element in content_elements
                    if element
                    and (
                        hasattr(element, "name")
                        or (isinstance(element, str) and element.strip())
                    )
                )

                # Only add if there's meaningful content
                if content.strip():
                    sections.append(
                        {"title": title, "content": content, "url": base_url}
                    )

            # Add header content (before first anchor) if present
            if (
                all_body_contents
                and all_numbered_anchors
                and all_numbered_anchors[0] in all_body_contents
            ):
                first_anchor = all_numbered_anchors[0]
                first_anchor_pos = all_body_contents.index(first_anchor)
                header_content = all_body_contents[:first_anchor_pos]
                if header_content:
                    content = "".join(
                        html_to_markdown(element)
                        for element in header_content
                        if element
                        and (
                            hasattr(element, "name")
                            or (isinstance(element, str) and element.strip())
                        )
                    )
                    if content.strip():
                        sections.insert(
                            0, {"title": "", "content": content, "url": base_url}
                        )

    else:
        # Fallback: generic H2-based extraction
        h2_tags = soup.find_all(["h2"])
        if not h2_tags:
            content = "".join(
                html_to_markdown(child)
                for child in soup.body.children
                if child.name not in ["h1", "h2"]
            )
            title = (
                soup.find("h1").get_text().strip()
                if soup.find("h1")
                else "Documentation HAProxy"
            )
            sections.append({"title": title, "content": content, "url": base_url})
        else:
            for i, h2_tag in enumerate(h2_tags):
                title = h2_tag.get_text().strip()
                content_elements = []
                next_element = h2_tag.next_sibling
                while next_element:
                    if hasattr(next_element, "name") and next_element.name in [
                        "h2",
                        "h1",
                    ]:
                        break
                    content_elements.append(next_element)
                    next_element = next_element.next_sibling
                content = "".join(
                    html_to_markdown(element) for element in content_elements
                )
                sections.append({"title": title, "content": content, "url": base_url})

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
            soup = BeautifulSoup(html_content, "html.parser")
            sections = extract_markdown_sections(soup, url)
            all_sections.extend(sections)
            print(f"[INFO] Extrait {len(sections)} sections depuis {url}")

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    output_path = data_dir / "sections.jsonl"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for section in all_sections:
                f.write(json.dumps(section, ensure_ascii=False) + "\n")
        print(
            f"\n[SUCCESS] {len(all_sections)} sections Markdown sauvegardées dans {output_path}"
        )
    except IOError as e:
        print(f"\n[ERROR] Erreur lors de l'écriture du fichier {output_path}: {e}")


if __name__ == "__main__":
    main()
