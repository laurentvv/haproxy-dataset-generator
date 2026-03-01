import json

def read_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

current = read_jsonl("data/sections.jsonl")
crawl4ai = read_jsonl("data/sections_crawl4ai.jsonl")

print(f"Current sections: {len(current)}")
print(f"Crawl4ai sections: {len(crawl4ai)}")

# Vérifier une section commune par titre
current_titles = {s['title']: s for s in current}
crawl4ai_titles = {s['title']: s for s in crawl4ai}

common_titles = set(current_titles.keys()) & set(crawl4ai_titles.keys())
print(f"Common titles: {len(common_titles)}")

if common_titles:
    t = sorted(list(common_titles))[10] # Prendre un exemple au milieu
    print(f"\n--- Comparing content for '{t}' ---")
    print(f"Current length: {len(current_titles[t]['content'])}")
    print(f"Crawl4ai length: {len(crawl4ai_titles[t]['content'])}")

    print("\n[Current Preview]:")
    print(current_titles[t]['content'][:500])

    print("\n[Crawl4ai Preview]:")
    print(crawl4ai_titles[t]['content'][:500])
