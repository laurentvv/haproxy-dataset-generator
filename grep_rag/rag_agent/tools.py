import os
import sys

from langchain_ollama import ChatOllama

# Fix absolu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config_grep import DEFAULT_LLM, OLLAMA_URL
from tools.file_search import grep_docs, list_sections, read_section

llm = ChatOllama(
    model=DEFAULT_LLM,
    base_url=OLLAMA_URL,
    temperature=0
)

TOOLS = [grep_docs, read_section, list_sections]
llm_with_tools = llm.bind_tools(TOOLS)
