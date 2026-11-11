# world/equip_agent.py
import json
import logging
from typing import Dict, Any, Tuple
from world import dnd_data

logger = logging.getLogger(__name__)

DEFAULT_EQUIP_DRAFT = {
    "weapon": None,
    "armor": None,
    "pack": None,
    "gold_remaining": 100,
    "status": "in_progress" # "in_progress", "ready_to_equip"
}

class EquipAgent:
    def __init__(self, chat_ai):
        self.chat_ai = chat_ai

    def process_turn(self, player_message: str, character: Any, draft: Dict[str, Any]) -> Tuple[Dict[str, Any], str, bool]:
        """
        Returns: (updated_draft, dm_response_text, is_complete)
        """
        class_name = character.classs.name if character.classs else "Adventurer"
        
        # Look up class defaults if available
        default_gear = "a basic weapon, simple armor, and a standard adventuring pack"
        if character.classs and hasattr(character.classs, 'starting_gear'):
            default_gear = str(character.classs.starting_gear)
            
        prompt = f"""You are a wise, patient Dungeon Master helping a newly created character pick their starting equipment.
        
Character: {character.name}, a level 1 {character.race} {class_name}.
Current Draft: {json.dumps(draft, indent=2)}

Your task:
1. Listen to what the player wants (e.g., "I want a longsword and chainmail").
2. If the player is indecisive (e.g., "I don't know", "what should I get?", "surprise me"), suggest a loadout suitable for a {class_name}. 
   - Class Defaults: {default_gear}
   - A standard "Explorer's Pack" (rations, waterskin, bedroll, torches) is recommended for supplies.
3. If the player says "just give me the defaults" or "skip this", immediately fill the draft with the Class Defaults and a pack, and set status to "ready_to_equip".
4. Update the draft with their choice. If they buy something expensive, subtract from "gold_remaining" (they start with 100g). 
5. If the draft has a weapon, armor, and pack, ask them to confirm the loadout. 
6. If they confirm, set draft["status"] to "ready_to_equip" and tell them they are ready for adventure.

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