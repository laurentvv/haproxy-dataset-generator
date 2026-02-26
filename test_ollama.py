#!/usr/bin/env python3
"""Test ultra-simple"""

import requests

print("Test Ollama API...")

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen3:14b",
        "prompt": 'Donne un JSON: {"test": 1}',
        "stream": False,
    },
    timeout=30,
)

print(f"Status: {response.status_code}")
print(f"Reponse: {response.text[:500]}")

data = response.json()
print(f"\nParsed: {data.get('response', 'N/A')[:200]}")
