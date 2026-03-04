import json
from pathlib import Path

def read_jsonl(path):
    data = []
    if not Path(path).exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

original = read_jsonl("data/sections.jsonl.bak")
new = read_jsonl("data/sections.jsonl")

print(f"--- Comparaison des scrapers ---")
print(f"Nombre de sections (BeautifulSoup): {len(original)}")
print(f"Nombre de sections (crawl4ai): {len(new)}")

# Analyse de la quantité de contenu total (en caractères)
total_char_orig = sum(len(s['content']) for s in original)
total_char_new = sum(len(s['content']) for s in new)

print(f"Quantité totale de texte (BeautifulSoup): {total_char_orig} chars")
print(f"Quantité totale de texte (crawl4ai): {total_char_new} chars")
print(f"Augmentation du contenu: {(total_char_new/total_char_orig - 1)*100:.2f}%")

# Vérifier la présence de blocs de code (indicateur de qualité du scraping pour de la doc technique)
code_blocks_orig = sum(1 for s in original if "```" in s['content'])
code_blocks_new = sum(1 for s in new if "```" in s['content'])

print(f"Sections avec blocs de code (BS): {code_blocks_orig}")
print(f"Sections avec blocs de code (crawl4ai): {code_blocks_new}")

# Exemple de section mal scrapée par BS (par exemple 3.4.1 dans intro)
bs_titles = {s['title']: s for s in original}
new_titles = {s['title']: s for s in new}

example_title = "3.4.1. Standard features : Sampling and converting information"
if example_title in new_titles:
    print(f"\n--- Exemple de section: '{example_title}' ---")
    if example_title in bs_titles:
        print(f"BS length: {len(bs_titles[example_title]['content'])}")
    else:
        print(f"BS a raté cette section sous ce titre exact.")
    print(f"crawl4ai length: {len(new_titles[example_title]['content'])}")
    print(f"Aperçu crawl4ai (100 chars):\n{new_titles[example_title]['content'][:100]}...")
