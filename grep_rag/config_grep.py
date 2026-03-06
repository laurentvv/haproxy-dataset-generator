import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FLAT_FILES_DIR = DATA_DIR / "flat_files"
INDEX_MAP_FILE = DATA_DIR / "index_map.json"
FULL_CORPUS_FILE = DATA_DIR / "full_corpus.txt"

# LLM Config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_LLM = os.getenv("LLM_MODEL", "qwen3.5:9b")

# Grep Parameters
MAX_GREP_RESULTS = 20
