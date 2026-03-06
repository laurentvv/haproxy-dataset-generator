import json
from pathlib import Path


def verify_coverage():
    ref_file = Path("rag/data/sections.jsonl")
    grep_index_file = Path("grep_rag/data/index_map.json")

    if not ref_file.exists():
        print(f"WARN: Reference file {ref_file} not found.")
        return
    if not grep_index_file.exists():
        print(f"ERROR: Grep index {grep_index_file} not found.")
        return

    ref_sections = []
    with open(ref_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ref_sections.append(json.loads(line))

    with open(grep_index_file, encoding="utf-8") as f:
        grep_index = json.load(f)

    ref_urls = {s['url'] for s in ref_sections}
    grep_urls = {s['url'] for s in grep_index.values()}

    missing = ref_urls - grep_urls
    coverage = (len(ref_urls) - len(missing)) / len(ref_urls) * 100 if ref_urls else 0

    print("--- RAPPORT DE COUVERTURE ---")
    print(f"Sections Reference: {len(ref_sections)}")
    print(f"Sections Grep RAG: {len(grep_index)}")
    print(f"Couverture URLs: {coverage:.2f}%")

    if missing:
        print(f"\nExemples d'URLs manquantes ({len(missing)}):")
        for url in sorted(missing)[:10]:
            print(f"  - {url}")

if __name__ == "__main__":
    verify_coverage()
