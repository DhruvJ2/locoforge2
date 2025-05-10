"""Utility functions for LLM message processing."""

from typing import Dict, Any, List
import json
from llm_config import llm

def process_message(message: str, system_prompt: str = None) -> Dict[str, Any]:
    """
    Process a message using the LLM.
    
    Args:
        message: The user message to process
        system_prompt: Optional system prompt to guide the LLM
        
    Returns:
        Dict containing the processed response
    """
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        response = llm.invoke(messages)
        return json.loads(response.content)
    except Exception as e:
        return {
            "error": f"Failed to process message: {str(e)}",
            "status": "error"
        } 