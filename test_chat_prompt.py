#!/usr/bin/env python3
"""Test simple - Chat API"""

import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma3:latest"  # Pas de mode thinking, plus rapide (3.3 GB)

TEST_SECTION = """server <name> <address>[:port] [settings ...]

Settings:
  disabled  : Mark the server as DOWN
  backup    : Backup server, receives traffic when all non-backup servers are DOWN
  weight    : Server weight (default: 1, range: 0-256)
  check     : Enable health checks
  inter     : Interval between health checks (default: 2000ms)
  fall      : Failed checks before marking server DOWN
  rise      : Successful checks before marking server UP"""

MESSAGES = [
    {
        "role": "system",
        "content": "Tu es un expert HAProxy 3.2. Reponds UNIQUEMENT avec un JSON valide. Pas de texte avant ou apres.",
    },
    {
        "role": "user",
        "content": f"""Extraire de cette section HAProxy :

KEYWORDS (5-10): Mots-cles techniques du texte
SYNONYMES (3-5): Termes associes
SUMMARY (1 phrase): Resume court
CATEGORY: backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general

Format JSON : {{"keywords": [], "synonyms": [], "summary": "", "category": ""}}

Section : {TEST_SECTION}

JSON :""",
    },
]

print("=" * 70)
print("TEST SIMPLE - CHAT API")
print("=" * 70)
print(f"\nModele: {MODEL}")
print("\nSection test: server options\n")

print("Envoi a Ollama (mode chat)...")

try:
    print("Envoi requete...")
    print(f"URL: {OLLAMA_URL}/api/chat")
    print(f"Payload: model={MODEL}, messages={len(MESSAGES)}")

    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "messages": MESSAGES,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1000,
                "think": False,  # Desactive le mode thinking de qwen3
            },
        },
        timeout=120,
    )

    print(f"Status HTTP: {response.status_code}")
    print(f"Taille reponse: {len(response.text)} chars")

    response.raise_for_status()

    data = response.json()
    print(f"Keys response: {data.keys()}")
    print(f"Full message: {data.get('message', {})}")
    print(f"Done reason: {data.get('done_reason', 'N/A')}")

    content = data["message"]["content"]
    print(f"Content length: {len(content)}")

    print("\n[REPONSE BRUTE]:")
    print("-" * 70)
    print(content)
    print("-" * 70)

    # Parser JSON
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        json_str = content[start:end]
        metadata = json.loads(json_str)

        print("\n[METADATA PARSEES]:")
        print(f"  Keywords: {metadata.get('keywords', [])}")
        print(f"  Synonyms: {metadata.get('synonyms', [])}")
        print(f"  Summary:  {metadata.get('summary', '')}")
        print(f"  Category: {metadata.get('category', '')}")

        # Evaluation
        expected = ["disabled", "backup", "weight", "check", "server", "DOWN"]
        found = [
            kw
            for kw in expected
            if kw.lower() in [k.lower() for k in metadata.get("keywords", [])]
        ]
        print(f"\n[SCORE]: {len(found)}/{len(expected)} keywords attendus trouves")
        print(f"  Trouves: {found}")
        print(f"  Manquants: {[kw for kw in expected if kw not in found]}")

        if len(found) >= 4:
            print("\n[SUCCESS] Prompt valide pour production!")
        else:
            print("\n[WARNING] Prompt a améliorer")
    else:
        print("\n[ERREUR] JSON non trouve dans la reponse")

except Exception as e:
    print(f"\n[ERREUR] {e}")

print("\n" + "=" * 70)
