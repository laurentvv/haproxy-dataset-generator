import json

def read_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

current_data = read_jsonl("data/sections.jsonl")
print(f"Current data: {len(current_data)} sections")

# Analyser les titres des 10 premières sections
for i, s in enumerate(current_data[:10]):
    print(f"{i}. {s['title']}")

# Chercher des mots clés dans les titres
keywords_sections = [s for s in current_data if "bind-process" in s['title'].lower()]
print(f"\nSections with 'bind-process': {len(keywords_sections)}")
if keywords_sections:
    print(f"Example: {keywords_sections[0]['title']}")
