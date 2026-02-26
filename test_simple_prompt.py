#!/usr/bin/env python3
"""Test simple - Prompt metadata generation"""

import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3:14b"

TEST_SECTION = """server <name> <address>[:port] [settings ...]

Settings:
  disabled  : Mark the server as DOWN and do not use it for any traffic.
  backup    : This server is a backup. It will only receive traffic when all non-backup servers are DOWN.
  weight    : Server weight (default: 1, range: 0-256). Higher weights receive more connections.
  check     : Enable health checks for this server.
  inter     : Interval between health checks (default: 2000ms).
  fall      : Number of consecutive failed checks before marking server DOWN.
  rise      : Number of consecutive successful checks before marking server UP."""

PROMPT = f"""Tu es un expert HAProxy 3.2.

Pour cette section, extraire UNIQUEMENT a partir du contenu fourni :

1. KEYWORDS (5-10) : Mots-cles techniques OBLIGATOIREMENT presents dans le texte
2. SYNONYMES (3-5) : Termes associes, variantes (ex: "desactiver" -> "disabled")
3. SUMMARY (1 phrase max) : Resume ultra-court
4. CATEGORY : backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general

REGLES :
- N'INVENTE RIEN
- Keywords doivent etre dans le texte

Format JSON uniquement :
{{"keywords": [], "synonyms": [], "summary": "", "category": ""}}

Section :
{TEST_SECTION}
"""

print("=" * 70)
print("TEST SIMPLE - GENERATION METADATA")
print("=" * 70)
print(f"\nModele: {MODEL}")
print("\nSection test: server options (disabled, backup, weight...)\n")

print("Envoi prompt a Ollama...")

try:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": PROMPT,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500},
        },
        timeout=120,
    )
    response.raise_for_status()

    content = response.json()["response"]

    print("\n[REPONSE BRUTE]:")
    print("-" * 70)
    print(content[:1000])
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
    else:
        print("\n[ERREUR] JSON non trouve dans la reponse")

except Exception as e:
    print(f"\n[ERREUR] {e}")

print("\n" + "=" * 70)
