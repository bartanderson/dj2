# world/intent_mapper.py
from typing import Dict, Any, Optional

class IntentMapper:
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self.intent_to_tool = {
            "move": "move_tool",
            "buy": "merchant_buy",
            "sell": "merchant_sell",
            "haggle": "merchant_haggle",
            "talk": "talk_tool",   # placeholder
            "look": "look_tool",   # placeholder
            "rest": "rest_tool",   # placeholder
        }

    def map_intent(self, intent: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Special case: answer (rules, lore, secrets) – not a tool
        if intent == "answer":
            return {"type": "answer", "parameters": parameters}

        if intent == "move" and "steps" not in parameters:
            parameters["steps"] = 1

        tool_name = self.intent_to_tool.get(intent)
        if not tool_name:
            return {"error": f"Unknown intent: {intent}"}
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not registered"}
        required = set(tool.param_types.keys())
        provided = set(parameters.keys())
        if not required.issubset(provided):
            missing = required - provided
            return {"error": f"Missing parameters: {missing}"}
        return {"type": "tool", "tool": tool_name, "arguments": parameters}