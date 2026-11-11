# world/equip_agent.py
import json
import logging
from typing import Dict, Any, Tuple
from world import dnd_data

logger = logging.getLogger(__name__)

DEFAULT_EQUIP_DRAFT = {
    "weapon": None,
    "armor": None,
    "shield": False,
    "status": "in_progress"
}

class EquipAgent:
    def __init__(self, chat_ai):
        self.chat_ai = chat_ai

    def process_turn(self, player_message: str, character: Any, draft: Dict[str, Any]) -> Tuple[Dict[str, Any], str, bool]:
        """
        Returns: (updated_draft, dm_response_text, is_complete)
        """
        prompt = f"""You are a wise Dungeon Master guiding a newly created character through choosing their starting equipment.
        
Character: {character.name}, a level 1 {character.race} {character.classs.name}.

Here is the current Equipment Draft:
{json.dumps(draft, indent=2)}

Your task:
1. Listen to what the player wants (e.g., "I want a longsword and chainmail").
2. Update the draft with their choice. Keep it simple: just "weapon", "armor", and "shield" (boolean).
3. If they ask for something a level 1 character wouldn't have (e.g., "a +3 flaming sword"), playfully deny it and offer a basic alternative.
4. If the draft has a weapon and armor, ask them to confirm the loadout.
5. If they confirm, set draft["status"] to "ready_to_equip" and tell them they are ready for adventure.

Output ONLY a JSON object with exactly these keys:
{{
    "updated_draft": {{ ...the full updated equip draft... }},
    "dm_response": "Your conversational reply here."
}}
"""
        try:
            ai_data = self.chat_ai.json_response(prompt + f"\n\nPlayer says: {player_message}")
            
            updated_draft = ai_data.get("updated_draft", draft)
            dm_response = ai_data.get("dm_response", "What weapon will you carry?")
            is_complete = updated_draft.get("status") == "ready_to_equip"

            return updated_draft, dm_response, is_complete
        except Exception as e:
            logger.error(f"EquipAgent failed: {e}")
            return draft, "I'm having trouble thinking about equipment right now. What did you want?", False