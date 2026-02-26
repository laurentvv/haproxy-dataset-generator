#!/usr/bin/env python3
"""
test_metadata_prompt.py - Tester le prompt d'enrichissement IA

Usage:
    uv run python test_metadata_prompt.py

Teste plusieurs prompts sur des sections critiques et affiche les résultats.
"""

import json
import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3:14b"  # Meilleur équilibre qualité/vitesse (9.3 GB)

# Charger quelques sections critiques
SECTIONS_TEST = [
    {
        "id": "test_backend_name",
        "question": "Comment nommer un backend dans HAProxy ?",
        "section_title": "4. Proxies",
        "content": """Proxy configuration can be located in a set of sections :
 - defaults [<name>] [ from <defaults_name> ]
 - frontend <name>   [ from <defaults_name> ]
 - backend  <name>   [ from <defaults_name> ]
 - listen   <name>   [ from <defaults_name> ]

A "frontend" section describes a set of listening sockets accepting client
connections.

A "backend" section describes a set of servers to which the proxy will connect
to forward incoming connections.

A "listen" section defines a complete proxy with its frontend and backend
parts combined in one section. It is generally useful for TCP-only traffic.

Syntax:
  backend <name>
      balance roundrobin
      server <name> <address>:<port> [weight <weight>] [check] [disabled] [backup]
""",
    },
    {
        "id": "test_server_disabled",
        "question": "Comment désactiver temporairement un serveur ?",
        "section_title": "5.2. Server and default-server options",
        "content": """The "server" and "default-server" keywords support a certain number of settings
which are all passed as arguments on the server line. The order in which those
arguments appear does not count, and they are all optional.

server <name> <address>[:port] [settings ...]
default-server [settings ...]

Settings:
  disabled  : Mark the server as DOWN and do not use it for any traffic.
              The server will remain disabled until manually enabled.
              
  backup    : This server is a backup. It will only receive traffic when all
              non-backup servers are DOWN.
              
  weight    : Server weight (default: 1, range: 0-256). Higher weights receive
              more connections.
              
  check     : Enable health checks for this server.
  
  inter     : Interval between health checks (default: 2000ms).
  
  fall      : Number of consecutive failed checks before marking server DOWN.
  
  rise      : Number of consecutive successful checks before marking server UP.
""",
    },
    {
        "id": "test_balance_source",
        "question": "Comment configurer l'algorithme source pour la persistance ?",
        "section_title": "5.1. Bind options",
        "content": """Balance algorithms determine how requests are distributed among servers.

Available algorithms:

  roundrobin  : Distribute requests in a round-robin fashion.
  
  leastconn   : Send requests to the server with the least active connections.
  
  source      : Hash the client's source IP address to select a server.
                This ensures that the same client IP always reaches the same
                server (persistence/sticky sessions).
                Syntax: balance source
                
  uri         : Hash the request URI to select a server.
  
  hdr         : Hash a specific HTTP header to select a server.
""",
    },
    {
        "id": "test_acl_negation",
        "question": "Comment négativer une condition ACL avec ! ?",
        "section_title": "7.2. Using ACLs to form conditions",
        "content": """ACLs can be used in conditions to control request flow.

Basic syntax:
  acl <name> <criterion> [flags] [operator] <value>

Using ACLs:
  use_backend <backend> if <acl_name>
  http-request deny if <acl_name>
  
Negation:
  The "!" operator negates a condition.
  
  Example:
    acl allowed_method GET POST
    http-request deny if !allowed_method
    
  This denies all requests that are NOT GET or POST.
  
  Negation can also be written as:
    unless <acl_name>  (equivalent to "if !<acl_name>")
    
  Example:
    use_backend backup if !maintenance_mode
    http-request redirect unless authenticated
""",
    },
]

# PROMPTS À TESTER
PROMPTS = {
    "v1_simple": """Extraire de cette section HAProxy :

1. KEYWORDS (5-10) : Mots-clés techniques du texte
2. SYNONYMES (3-5) : Termes associés, variantes
3. SUMMARY (1 phrase) : Résumé court
4. CATEGORY : backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general

Format JSON :
{{"keywords": [], "synonyms": [], "summary": "", "category": ""}}

Section :
{section}
""",
    "v2_strict": """Tu es un expert HAProxy 3.2.

Pour cette section, extraire UNIQUEMENT à partir du contenu fourni :

1. KEYWORDS (5-10) : Mots-clés techniques OBLIGATOIREMENT présents dans le texte
2. SYNONYMES (3-5) : Termes associés, variantes, antonymes (ex: "désactiver" → "disabled")
3. SUMMARY (1 phrase max) : Résumé ultra-court
4. CATEGORY : Une seule parmi : backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general

RÈGLES :
- N'INVENTE RIEN
- Keywords doivent être dans le texte
- Sois précis et technique

Format JSON uniquement :
{{"keywords": [], "synonyms": [], "summary": "", "category": ""}}

Section :
{section}
""",
    "v3_context": """Tu es un expert HAProxy 3.2.

Contexte : Cette section sera utilisée pour un système de retrieval RAG.
Objectif : Générer des metadata pour améliorer la recherche sémantique.

Pour cette section, extraire :

1. KEYWORDS (5-10) : Concepts techniques IMPORTANT pour la recherche
   - Inclure termes spécifiques HAProxy
   - Inclure variantes (ex: "health check", "healthcheck", "check")
   
2. SYNONYMES (3-5) : Mots-clés que les utilisateurs pourraient chercher
   - Ex: "désactiver" → "disabled", "down", "inactive"
   - Ex: "persistance" → "sticky", "source", "ip hash"
   
3. SUMMARY (1 phrase) : Ce que l'utilisateur trouvera dans cette section
   
4. CATEGORY : backend, frontend, acl, ssl, timeout, healthcheck, stick-table, logs, stats, general, loadbalancing

Format JSON :
{{"keywords": [], "synonyms": [], "summary": "", "category": ""}}

Section :
{section}
""",
}


def test_prompt(prompt_name: str, prompt_template: str, section: dict):
    """Teste un prompt sur une section."""
    prompt = prompt_template.format(section=section["content"][:4000])

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500},
            },
            timeout=60,
        )
        response.raise_for_status()

        content = response.json()["response"]

        # Parser JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            metadata = json.loads(content[start:end])
            return metadata, None
        else:
            return None, f"JSON non trouvé: {content[:200]}"

    except Exception as e:
        return None, str(e)


def evaluate_metadata(metadata: dict, expected_keywords: list) -> dict:
    """Évalue la qualité des metadata."""
    score = 0
    max_score = 10

    # Keywords (5 points)
    if metadata.get("keywords"):
        found = sum(
            1
            for kw in expected_keywords
            if kw.lower() in [k.lower() for k in metadata["keywords"]]
        )
        score += min(5, found)

    # Synonyms (2 points)
    if metadata.get("synonyms") and len(metadata["synonyms"]) > 0:
        score += 2

    # Summary (2 points)
    if metadata.get("summary") and 20 < len(metadata["summary"]) < 200:
        score += 2

    # Category (1 point)
    valid_categories = [
        "backend",
        "frontend",
        "acl",
        "ssl",
        "timeout",
        "healthcheck",
        "stick-table",
        "logs",
        "stats",
        "general",
        "loadbalancing",
    ]
    if metadata.get("category") in valid_categories:
        score += 1

    return {"score": score, "max_score": max_score}


def main():
    print("=" * 70)
    print("TEST PROMPTS - ENRICHISSEMENT MÉTADONNÉES")
    print("=" * 70)
    print(f"\nModèle IA: {MODEL}")
    print(f"Sections à tester: {len(SECTIONS_TEST)}")
    print(f"Prompts à tester: {len(PROMPTS)}")
    print("\n" + "=" * 70)

    # Tester TOUTES les sections automatiquement
    sections_to_test = SECTIONS_TEST

    for section in sections_to_test:
        print(f"\n{'=' * 70}")
        print(f"SECTION: {section['section_title']}")
        print(f"Question test: {section['question']}")
        print(f"{'=' * 70}")

        # Mots-clés attendus (pour évaluation)
        if "backend_name" in section["id"]:
            expected_kw = ["backend", "name", "syntax"]
        elif "disabled" in section["id"]:
            expected_kw = ["disabled", "server", "backup", "DOWN"]
        elif "balance_source" in section["id"]:
            expected_kw = ["balance", "source", "hash", "persistence"]
        elif "acl_negation" in section["id"]:
            expected_kw = ["!", "negation", "unless", "deny"]
        else:
            expected_kw = []

        for prompt_name, prompt_template in PROMPTS.items():
            print(f"\n--- PROMPT: {prompt_name} ---")

            metadata, error = test_prompt(prompt_name, prompt_template, section)

            if error:
                print(f"[ERREUR] {error}")
            else:
                print("\n[RESULTATS]:")
                print(f"   Keywords: {metadata.get('keywords', [])}")
                print(f"   Synonyms: {metadata.get('synonyms', [])}")
                print(f"   Summary: {metadata.get('summary', '')[:100]}")
                print(f"   Category: {metadata.get('category', '')}")

                # Évaluation
                eval_result = evaluate_metadata(metadata, expected_kw)
                print(f"\n   SCORE: {eval_result['score']}/{eval_result['max_score']}")

                # Vérifier keywords attendus
                if expected_kw:
                    found_kw = [
                        kw
                        for kw in expected_kw
                        if kw.lower()
                        in [k.lower() for k in metadata.get("keywords", [])]
                    ]
                    print(f"   Keywords attendus trouves: {found_kw}/{expected_kw}")

            print()

    print("\n" + "=" * 70)
    print("TEST TERMINE")
    print("=" * 70)
    print("\nProchaines étapes :")
    print("1. Analyser les scores")
    print("2. Ajuster le prompt si besoin")
    print("3. Créer 01b_enrich_metadata.py avec le meilleur prompt")


if __name__ == "__main__":
    main()
