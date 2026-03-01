import os
import json
from typing import List, Annotated, Set, Literal, Dict, Any
import operator

from pydantic import BaseModel, Field
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    RemoveMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
import chromadb
from chromadb.config import Settings
import tiktoken

from .prompts import *

# --- Configuration ---
INDEX_DIR = "index_agentic"
CHROMA_DIR = os.path.join(INDEX_DIR, "chroma")
PARENTS_DIR = os.path.join(INDEX_DIR, "parents")
CHILD_COLLECTION = "haproxy_agentic_child"

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:8b"
LLM_MODEL = "gemma3:latest"

MAX_TOOL_CALLS = 8
MAX_ITERATIONS = 10
BASE_TOKEN_THRESHOLD = 2000

# --- State Definitions ---


def accumulate_or_reset(existing: List[dict], new: List[dict]) -> List[dict]:
    if new and any(item.get("__reset__") for item in new):
        return []
    return existing + new


def set_union(a: Set[str], b: Set[str]) -> Set[str]:
    return a | b


class State(MessagesState):
    questionIsClear: bool = False
    conversation_summary: str = ""
    originalQuery: str = ""
    rewrittenQuestions: List[str] = []
    agent_answers: Annotated[List[dict], accumulate_or_reset] = []


class AgentState(MessagesState):
    tool_call_count: Annotated[int, operator.add] = 0
    iteration_count: Annotated[int, operator.add] = 0
    question: str = ""
    question_index: int = 0
    context_summary: str = ""
    retrieval_keys: Annotated[Set[str], set_union] = set()
    final_answer: str = ""
    agent_answers: List[dict] = []  # Propagate results back to main graph


class QueryAnalysis(BaseModel):
    is_clear: bool = Field(description="Indique si la question est claire.")
    questions: List[str] = Field(description="Liste des questions réécrites.")
    clarification_needed: str = Field(
        description="Explication si la question est floue."
    )


# --- Utilities ---


def estimate_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except:
        return len(text) // 4


def get_embedding(text: str):
    import requests

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}")
        return [0.0] * 4096


# --- Tools ---

_chroma_client = None


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client


@tool
def search_child_chunks(query: str, limit: int = 5) -> str:
    """Cherche les extraits (child chunks) les plus pertinents dans la doc HAProxy.
    Retourne les Parent IDs et les extraits de texte."""
    client = get_chroma_client()
    try:
        collection = client.get_collection(CHILD_COLLECTION)
    except:
        return "ERREUR: Index non trouvé. Lancez d'abord l'indexation."

    emb = get_embedding(query)
    results = collection.query(query_embeddings=[emb], n_results=limit)

    if not results["ids"][0]:
        return "AUCUN_RÉSULTAT_PERTINENT"

    formatted = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        content = results["documents"][0][i]
        formatted.append(
            f"Parent ID: {meta['parent_id']}\nSection: {meta['title']}\nExtrait: {content}"
        )

    return "\n\n---\n\n".join(formatted)


@tool
def retrieve_parent_chunks(parent_id: str) -> str:
    """Récupère le contenu complet d'une section (parent chunk) par son ID.
    Utilisez ceci pour avoir plus de contexte sur un extrait trouvé via search_child_chunks."""
    path = os.path.join(PARENTS_DIR, f"{parent_id}.json")
    if not os.path.exists(path):
        return f"ERREUR: Section {parent_id} introuvable."

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return f"Titre: {data['title']}\nURL: {data['url']}\nContenu complet:\n{data['content']}"


# --- Models ---

llm = ChatOllama(model=LLM_MODEL, temperature=0, base_url=OLLAMA_URL)
llm_with_tools = llm.bind_tools([search_child_chunks, retrieve_parent_chunks])

# --- Main Graph Nodes ---


def summarize_history(state: State):
    if len(state["messages"]) < 4:
        return {"conversation_summary": ""}

    relevant_msgs = [
        m
        for m in state["messages"]
        if isinstance(m, (HumanMessage, AIMessage)) and not m.tool_calls
    ]
    history_text = "\n".join([f"{m.type}: {m.content}" for m in relevant_msgs[-6:]])

    summary = llm.invoke(
        [
            SystemMessage(content=get_conversation_summary_prompt()),
            HumanMessage(content=f"Historique à résumer:\n{history_text}"),
        ]
    )
    return {
        "conversation_summary": summary.content,
        "agent_answers": [{"__reset__": True}],
    }


def rewrite_query(state: State):
    last_message = state["messages"][-1]
    summary = state.get("conversation_summary", "")

    user_input = (
        f"Contexte de conversation: {summary}\nNouvelle requête: {last_message.content}"
    )

    # Using structured output if possible, else fallback to manual parsing
    try:
        structured_llm = llm.with_structured_output(QueryAnalysis)
        analysis = structured_llm.invoke(
            [
                SystemMessage(content=get_rewrite_query_prompt()),
                HumanMessage(content=user_input),
            ]
        )
    except:
        # Fallback manual parsing if structured output fails
        raw_res = llm.invoke(
            [
                SystemMessage(
                    content=get_rewrite_query_prompt()
                    + "\nRéponds UNIQUEMENT au format JSON."
                ),
                HumanMessage(content=user_input),
            ]
        )
        try:
            # Basic cleanup of potential markdown blocks
            content = raw_res.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            data = json.loads(content)
            analysis = QueryAnalysis(**data)
        except:
            analysis = QueryAnalysis(
                is_clear=True, questions=[last_message.content], clarification_needed=""
            )

    if analysis.is_clear and analysis.questions:
        return {
            "questionIsClear": True,
            "originalQuery": last_message.content,
            "rewrittenQuestions": analysis.questions,
            # We don't remove messages here, we'll do it in the Send logic if needed or keep them for reference
        }

    return {
        "questionIsClear": False,
        "messages": [
            AIMessage(
                content=analysis.clarification_needed
                or "Pouvez-vous préciser votre question ?"
            )
        ],
    }


def aggregate_answers(state: State):
    answers = state["agent_answers"]
    if not answers:
        return {
            "messages": [
                AIMessage(
                    content="Désolé, je n'ai pas trouvé d'information pour répondre à votre question."
                )
            ]
        }

    sorted_answers = sorted(answers, key=lambda x: x.get("index", 0))
    formatted = ""
    for i, a in enumerate(sorted_answers):
        formatted += f"--- Sous-question {i + 1}: {a.get('question', '')} ---\nRéponse: {a.get('answer', '')}\n\n"

    final = llm.invoke(
        [
            SystemMessage(content=get_aggregation_prompt()),
            HumanMessage(
                content=f"Requête originale: {state['originalQuery']}\n\nRéponses collectées:\n{formatted}"
            ),
        ]
    )
    return {"messages": [final]}


# --- Agent Sub-Graph Nodes ---


def orchestrator(state: AgentState):
    context_summary = state.get("context_summary", "")
    system_msg = SystemMessage(content=get_orchestrator_prompt())

    messages = [system_msg]
    if context_summary:
        messages.append(
            HumanMessage(
                content=f"[CONTEXTE DE RECHERCHE COMPRESSÉ]\n{context_summary}"
            )
        )

    if not state.get("messages"):
        messages.append(
            HumanMessage(
                content=f"Réponds à cette question en cherchant dans la doc: {state['question']}"
            )
        )
    else:
        # Keep only the last few messages to avoid context bloat
        messages.extend(state["messages"][-5:])

    response = llm_with_tools.invoke(messages)
    return {
        "messages": [response],
        "tool_call_count": len(response.tool_calls)
        if hasattr(response, "tool_calls")
        else 0,
        "iteration_count": 1,  # This will be added due to Annotated[int, operator.add]
    }


def should_compress_context(
    state: AgentState,
) -> Command[Literal["compress_context", "orchestrator"]]:
    # Calculate token usage
    total_text = state.get("context_summary", "")
    for m in state["messages"]:
        total_text += str(m.content)

    tokens = estimate_tokens(total_text)

    if tokens > BASE_TOKEN_THRESHOLD:
        return Command(goto="compress_context")
    return Command(goto="orchestrator")


def compress_context(state: AgentState):
    messages = state["messages"]
    summary_prompt = get_context_compression_prompt()

    history = ""
    for m in messages:
        if isinstance(m, ToolMessage):
            history += f"RESULTAT OUTIL: {m.content}\n"
        elif isinstance(m, AIMessage) and m.content:
            history += f"ASSISTANT: {m.content}\n"

    new_summary = llm.invoke(
        [
            SystemMessage(content=summary_prompt),
            HumanMessage(content=f"Données de recherche à compresser:\n{history}"),
        ]
    )

    # Remove old messages after compression to save space
    ids_to_remove = [m.id for m in messages if m.id]

    return {
        "context_summary": new_summary.content,
        "messages": [RemoveMessage(id=mid) for mid in ids_to_remove],
    }


def collect_answer(state: AgentState):
    last_msg = state["messages"][-1]
    answer = (
        last_msg.content
        if isinstance(last_msg, AIMessage)
        else "Erreur: pas de réponse générée."
    )
    return {
        "final_answer": answer,
        "agent_answers": [
            {
                "index": state["question_index"],
                "question": state["question"],
                "answer": answer,
            }
        ],
    }


# --- Routing ---

from langgraph.types import Send


def route_after_rewrite(state: State):
    if not state["questionIsClear"]:
        return END

    return [
        Send("agent", {"question": q, "question_index": i, "messages": []})
        for i, q in enumerate(state["rewrittenQuestions"])
    ]


def route_agent(state: AgentState):
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "fallback"

    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        # Check if we should compress context before tool execution?
        # Actually LangGraph does tools in a separate node.
        return "tools"

    return "end"


def route_after_tools(state: AgentState):
    # After tools, check if we should compress
    total_text = state.get("context_summary", "")
    for m in state["messages"]:
        total_text += str(m.content)

    if estimate_tokens(total_text) > BASE_TOKEN_THRESHOLD:
        return "compress"
    return "orchestrator"


# --- Building Graph ---

# Sub-graph for single question agent
agent_builder = StateGraph(AgentState)
agent_builder.add_node("orchestrator", orchestrator)
agent_builder.add_node("tools", ToolNode([search_child_chunks, retrieve_parent_chunks]))
agent_builder.add_node("compress", compress_context)
agent_builder.add_node("collect", collect_answer)
agent_builder.add_node(
    "fallback",
    lambda s: {
        "messages": [
            AIMessage(
                content="Désolé, j'ai atteint la limite de recherche pour cette question."
            )
        ]
    },
)

agent_builder.add_edge(START, "orchestrator")
agent_builder.add_conditional_edges(
    "orchestrator",
    route_agent,
    {"tools": "tools", "fallback": "fallback", "end": "collect"},
)
agent_builder.add_conditional_edges(
    "tools", route_after_tools, {"compress": "compress", "orchestrator": "orchestrator"}
)
agent_builder.add_edge("compress", "orchestrator")
agent_builder.add_edge("collect", END)
agent_builder.add_edge("fallback", "collect")
agent_subgraph = agent_builder.compile()

# Main graph
builder = StateGraph(State)
builder.add_node("summarize", summarize_history)
builder.add_node("rewrite", rewrite_query)
builder.add_node("agent", agent_subgraph)
builder.add_node("aggregate", aggregate_answers)

builder.add_edge(START, "summarize")
builder.add_edge("summarize", "rewrite")
builder.add_conditional_edges("rewrite", route_after_rewrite, ["agent", END])
builder.add_edge("agent", "aggregate")
builder.add_edge("aggregate", END)

# Compiled graph
from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)
