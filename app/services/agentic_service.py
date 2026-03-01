"""Agentic RAG service for HAProxy Chatbot."""

import asyncio
from typing import AsyncGenerator, Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage

from app.agentic.graph import graph
from app.utils.logging import setup_logging

logger = setup_logging(__name__)

class AgenticRAGService:
    """Service RAG Agentique utilisant LangGraph."""

    def __init__(self):
        self.graph = graph

    async def process_message(
        self,
        message: str,
        thread_id: str,
    ) -> AsyncGenerator[str, None]:
        """Traite un message via le graphe agentique."""

        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

        # Initial input
        initial_input = {"messages": [HumanMessage(content=message)]}

        # Stream events from the graph
        # Note: LangGraph async stream can yield updates
        async for event in self.graph.astream(initial_input, config=config, stream_mode="updates"):
            # Log current node
            for node_name, output in event.items():
                logger.info(f"Node '{node_name}' finished")

                # If we have a message in the output, we can show progress or intermediate results
                if "messages" in output and output["messages"]:
                    last_msg = output["messages"][-1]
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        # This might be a partial answer or the final one
                        yield last_msg.content
                    elif isinstance(last_msg, dict) and "content" in last_msg:
                        yield last_msg["content"]

        # Final state check
        final_state = await self.graph.aget_state(config)
        if final_state.values.get("messages"):
            last_msg = final_state.values["messages"][-1]
            yield last_msg.content
