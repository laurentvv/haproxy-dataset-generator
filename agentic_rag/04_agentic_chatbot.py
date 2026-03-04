#!/usr/bin/env python3
"""Script principal pour lancer le chatbot RAG agentic."""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_rag.app.gradio_app import main

if __name__ == '__main__':
    main()
