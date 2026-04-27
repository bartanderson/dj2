# world/intent_parser.py
import json
from typing import Dict, Any, List
from world.intent import IntentFrame

class IntentParser:
    def __init__(self, chat_ai):
        self.chat_ai = chat_ai

    def parse(self, message: str, game_context: Dict, history: List[Dict]) -> IntentFrame:
        prompt = self._build_prompt(message, game_context, history)
        try:
            data = self.chat_ai.json_response(prompt)
            return IntentFrame(
                action=data.get("action", "narrate"),
                category=data.get("category", "other"),
                target=data.get("target"),
                item=data.get("item"),
                destination=data.get("destination"),
                price=data.get("price"),
                motivation=data.get("motivation"),
                manner=data.get("manner"),
                raw_text=message,
                context=data.get("modifiers", {})
            )
        except Exception:
            return IntentFrame(
                action="clarify",
                category="other",
                clarification_needed=True,
                missing_fields=["action", "target"],
                raw_text=message
            )

    def _build_prompt(self, message: str, context: Dict, history: List[Dict]) -> str:
        recent = history[-3:] if history else []
        merchant_display = context.get("merchant_display", "unknown")
        
        return f"""You are a game NLU parser. Convert the player's message into a JSON object with these fields:
- action: the main verb. MUST be one of: "buy", "sell", "haggle", "barter", "move", "look", "talk", "attack", "cast", "rest", "narrate".
- category: one of "movement", "economy", "social", "exploration", "combat", "other".
- target: the person/object being addressed (e.g., "Grom", "merchant", "door", "healing potion").
- item: the item being given or exchanged (e.g., "shortsword", "potion").
- destination: where to go (e.g., "north", "tavern").
- price: numeric amount if money mentioned, else null.
- manner: adverb like "carefully", "loudly", "politely", null.
- motivation: why they're doing it (if stated), else null.
- modifiers: a dict of additional details (e.g., "color": "red", "quality": "shiny").

SPECIAL RULES FOR ECONOMY ACTIONS:
- "buy", "purchase", "get", "acquire", "offer", "bid", "pay" → action="buy"
- "sell", "dispose", "trade away", "pawn" → action="sell"
- "haggle", "negotiate", "bargain", "dicker" → action="haggle"
- "barter", "swap", "exchange", "trade (when two items)" → action="barter"
- For barter: the item you GIVE is "item", the item you WANT is "target". Gold difference is "price" (positive if you add gold).
- For buy/sell: "item" is the item being bought or sold. "price" is the offered amount (if any).

Examples:
Message: "buy potion" → {{"action":"buy","category":"economy","target":null,"item":"potion","destination":null,"price":null,"manner":null,"motivation":null,"modifiers":{{}}}}
Message: "buy potion" → {{"action":"buy","category":"economy","target":null,"item":"potion","destination":null,"price":null,"manner":null,"motivation":null,"modifiers":{{}}}}
Message: "sell shortsword for 8 gp" → {{"action":"sell","category":"economy","target":null,"item":"shortsword","price":8}}
Message: "barter my shortsword for your healing potion" → {{"action":"barter","category":"economy","target":"healing potion","item":"shortsword","price":null}}
Message: "trade shortsword + 5 gp for potion" → {{"action":"barter","category":"economy","target":"potion","item":"shortsword","price":5}}
Message: "look at Grom" → {{"action":"look","category":"exploration","target":"Grom"}}
Message: "go north" → {{"action":"move","category":"movement","destination":"north"}}

Use null for missing fields.

Game context: {context}
Recent conversation: {recent}

Message: "{message}"
Output ONLY the JSON object, no other text.
"""