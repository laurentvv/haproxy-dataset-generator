import os
import sys
from pathlib import Path
from typing import Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import ChatOllama
from agentic_rag.config_agentic import EMBEDDING_MODEL, GOOGLE_API_KEY, LLM_CONFIG

class SimpleAgenticRAG:
    def __init__(self):
        if not GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY not found in environment")
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GOOGLE_API_KEY
        )
        self.llm = ChatOllama(model=LLM_CONFIG['model'])

    def run(self, query: str):
        # Implementation placeholder
        print(f"Running query: {query}")
        return "Not implemented in this simplified view"

if __name__ == "__main__":
    rag = SimpleAgenticRAG()
    rag.run("What is HAProxy?")
