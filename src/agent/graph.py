"""LangGraph chat agent implementation."""

from __future__ import annotations

from langgraph.graph import StateGraph
from dotenv import load_dotenv

from agent.utils.state import InputState, OutputState, Configuration
from agent.utils.nodes import supervisor_node

# Load environment variables
load_dotenv()

# Define the graph
graph = (
    StateGraph(InputState, config_schema=Configuration)
    .add_node("supervisor_node", supervisor_node)
    .add_edge("__start__", "supervisor_node")
    .compile(name="Chat Agent")
)
