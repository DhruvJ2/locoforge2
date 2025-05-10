"""State schema definitions for the agent."""

from typing import TypedDict, List, Dict, Any


class Message(TypedDict):
    """Message structure for chat."""
    role: str
    content: str


class InputState(TypedDict):
    """Input state for the agent."""
    messages: List[Message]


class OutputState(TypedDict):
    """Output state from the agent."""
    messages: List[Message]


class Configuration(TypedDict):
    """Configurable parameters for the agent."""
    temperature: float
    model_name: str 