import json
import logging
from typing import Any, Dict, Optional
from world.chat_ai import get_chat_ai

logger = logging.getLogger(__name__)

def get_ai_response(prompt_or_message: str, session: Any = None, game_context: Optional[Dict] = None, encounter: Optional[Dict] = None) -> str:
    """
    Legacy wrapper that calls the AI and returns a JSON string.
    For compatibility with existing code.
    """
    chat_ai = get_chat_ai()
    # Determine if this is a custom prompt (contains "Respond in JSON")
    if "Respond in JSON" in prompt_or_message or "JSON object" in prompt_or_message:
        data = chat_ai.json_response(prompt_or_message)
    else:
        # For simple prompts, we still want JSON output; we'll build a minimal prompt
        # that asks for JSON. But to preserve behavior, we'll just call json_response.
        data = chat_ai.json_response(prompt_or_message)
    return json.dumps(data)