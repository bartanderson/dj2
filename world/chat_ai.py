import json
import logging
from typing import Optional
from world.ai_integration import BaseAI
from world.event_log import get_event_log

logger = logging.getLogger(__name__)


class ChatAI:
    def __init__(self, ai_system: Optional[BaseAI] = None):
        if ai_system is not None:
            self.ai = ai_system
        else:
            self.ai = BaseAI()

    def json_response(self, prompt: str) -> dict:
        try:
            response_text = self.ai.generate_text(prompt)
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            get_event_log().emit("ai.failure", {"error": str(e)}, source_system="chat_ai")
            raise RuntimeError("AI is not available") from e

        try:
            if not response_text.strip().startswith("{"):
                raise json.JSONDecodeError("Not JSON", response_text, 0)

            import re

            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    data = None
            else:
                data = None

            if not data:
                get_event_log().emit("ai.json_error", {"response": response_text[:200]}, source_system="chat_ai")
                return {"narrative": response_text.strip(), "updates": {}, "needs_confirmation": False}

            if 'narrative' not in data and 'tool' not in data:
                data['narrative'] = "The DM considers your words."

            return data

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from LLM: {response_text}")

            get_event_log().emit(
                "ai.json_error",
                {"response": response_text[:200]},
                source_system="chat_ai"
            )

            return {
                "narrative": response_text,
                "updates": {},
                "needs_confirmation": False
            }

_chat_ai = None

def get_chat_ai():
    global _chat_ai
    if _chat_ai is None:
        _chat_ai = ChatAI()
    return _chat_ai