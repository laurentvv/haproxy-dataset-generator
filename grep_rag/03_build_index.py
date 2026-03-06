import json
from pathlib import Path


def build_index():
    flat_files_dir = Path("grep_rag/data/flat_files")
    output_map = Path("grep_rag/data/index_map.json")
    output_corpus = Path("grep_rag/data/full_corpus.txt")

    index_map = {}
    full_corpus = []

    print(f"[INFO] Construction de l'index depuis {flat_files_dir}...")

    # Trier les fichiers pour assurer un ordre stable dans le corpus
    files = sorted(flat_files_dir.glob("*.md"))

    for filepath in files:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Extraction des métadonnées simplifiée depuis le header
        metadata = {
            "filename": filepath.name,
            "title": "Unknown",
            "url": "",
            "depth": 0,
            "page": ""
        }

        lines = content.split('\n')
        for line in lines:
            if line.startswith("# SECTION: "):
                metadata["title"] = line.replace("# SECTION: ", "").strip()
            elif line.startswith("# URL: "):
                metadata["url"] = line.replace("# URL: ", "").strip()
            elif line.startswith("# DEPTH: "):
                metadata["depth"] = int(line.replace("# DEPTH: ", "").strip())
            elif line.startswith("# PAGE: "):
                metadata["page"] = line.replace("# PAGE: ", "").strip()
            elif line.startswith("---"):
                break

        metadata["char_count"] = len(content)
        index_map[filepath.name] = metadata

        # Ajout au corpus complet avec un séparateur clair pour grep
        full_corpus.append(f"FILE: {filepath.name}\n{content}\n{'='*40}\n")

    # Sauvegarde de la map
    with open(output_map, "w", encoding="utf-8") as f:
        json.dump(index_map, f, indent=2, ensure_ascii=False)

    # Sauvegarde du corpus
    with open(output_corpus, "w", encoding="utf-8") as f:
        f.writelines(full_corpus)

    print(f"[SUCCESS] Index map ({len(index_map)} entrées) et full_corpus ({len(full_corpus)} fichiers) générés.")

if __name__ == "__main__":
    build_index()
