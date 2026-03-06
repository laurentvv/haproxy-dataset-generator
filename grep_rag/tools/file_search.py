import json
import os
import re
import sys
from pathlib import Path

from langchain_core.tools import tool

# Fix pour config
sys.path.append(str(Path(__file__).parent.parent))
from config_grep import FLAT_FILES_DIR, INDEX_MAP_FILE, MAX_GREP_RESULTS


def _load_index():
    if INDEX_MAP_FILE.exists():
        with open(INDEX_MAP_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

@tool
def grep_docs(pattern: str, case_sensitive: bool = False, max_results: int = MAX_GREP_RESULTS) -> list[dict]:
    r"""
    Recherche par regex dans tous les fichiers de la documentation HAProxy.

    Utiliser pour : noms de paramètres exacts, directives, valeurs numériques,
    mots-clés techniques (maxconn, timeout, option, acl, frontend, backend...).

    Args:
        pattern     : regex ou mot exact. Exemples : "maxconn", "timeout\s+connect",
                      "option\s+forwardfor", "^\s*server\s"
        case_sensitive : False par défaut (recommandé pour HAProxy)
        max_results : cap sur le nombre de résultats (défaut 20)

    Returns:
        [{file, line_number, line_content, section_path, url}]
    """
    results = []
    index_map = _load_index()

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return [{"error": f"Regex invalide: {str(e)}"}]

    if not FLAT_FILES_DIR.exists():
        return [{"error": "Répertoire des fichiers plats non trouvé."}]

    for filename in sorted(os.listdir(FLAT_FILES_DIR)):
        if not filename.endswith(".md"):
            continue

        filepath = FLAT_FILES_DIR / filename
        metadata = index_map.get(filename, {})

        with open(filepath, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if regex.search(line):
                    results.append({
                        "file": filename,
                        "line_number": i,
                        "line_content": line.strip(),
                        "section_path": metadata.get("title", filename),
                        "url": metadata.get("url", "")
                    })
                    if len(results) >= max_results:
                        return results

    return results

@tool
def read_section(filename: str) -> dict:
    """
    Lit le contenu complet d'une section identifiée par grep_docs.

    Args:
        filename : nom du fichier (champ 'file' dans les résultats de grep_docs)

    Returns:
        {filename, content, metadata}
    """
    filepath = FLAT_FILES_DIR / filename
    if not filepath.exists():
        return {"error": f"Fichier {filename} non trouvé."}

    index_map = _load_index()
    metadata = index_map.get(filename, {})

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    return {
        "filename": filename,
        "content": content,
        "metadata": metadata
    }

@tool
def list_sections(query: str = "") -> list[dict]:
    """
    Liste les sections disponibles, avec filtrage optionnel par mot-clé dans le titre.
    Utile pour naviguer la structure avant de grep.

    Args:
        query : filtre optionnel sur le nom de section (ex: "backend", "acl")

    Returns:
        [{filename, section_path, url, char_count}]
    """
    index_map = _load_index()
    results = []

    q = query.lower()
    for filename, meta in index_map.items():
        if not q or q in meta.get("title", "").lower():
            results.append({
                "filename": filename,
                "section_path": meta.get("title", ""),
                "url": meta.get("url", ""),
                "char_count": meta.get("char_count", 0)
            })

    return sorted(results, key=lambda x: x['section_path'])
