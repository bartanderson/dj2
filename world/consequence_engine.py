# world/consequence_engine.py
"""
Consequence Engine – generates narrative responses from validated actions.
Phase: Consequence (narration)
"""

from typing import List, Dict, Any, Optional
from world.ai_dungeon_master import ConsequenceTracker, ResponseGenerator
from world.dm_chat_handler import DialogResponse

class ConsequenceEngine:
    def __init__(self, world_controller=None, dm_chat_ai=None):
        self.world_controller = world_controller
        self.dm_chat_ai = dm_chat_ai
        self.consequence_tracker = ConsequenceTracker()
        self.response_generator = ResponseGenerator()
        self.dialog_history = []

    def generate_creation_narrative(self, action: Dict, context: Dict) -> List[DialogResponse]:
        """
        Generate a narrative response for a character‑creation action.
        action should contain at least "action" and "parameters".
        """
        action_type = action.get("action")
        params = action.get("parameters", {})

        if action_type == "ask_question":
            question = params.get("question", "Tell me more about your character.")
            return [DialogResponse(speaker="DM", content=question, dialog_type="narration")]

        elif action_type == "suggest_class":
            suggestion = params.get("suggestion", {})
            primary = suggestion.get("primary_class", "fighter")
            explanation = suggestion.get("explanation", "")
            # You can make this more dynamic by using AI later
            text = f"Based on what you've told me, I think {primary} would be a great fit. {explanation} Does that sound right?"
            return [DialogResponse(speaker="DM", content=text, dialog_type="narration")]

        elif action_type == "confirm_class":
            return [DialogResponse(speaker="DM", content="Great! Class confirmed. Let's continue.", dialog_type="narration")]

        elif action_type == "create_character":
            char_data = params.get("character_data", {})
            name = char_data.get("name", "Your character")
            return [DialogResponse(speaker="DM", content=f"Wonderful! {name} is now ready to begin their adventure.",dialog_type= "narration")]

        elif action_type == "error":
            message = params.get("message", "Something went wrong.")
            return [DialogResponse(speaker="DM", content=message, dialog_type="system")]

        else:
            return [DialogResponse(speaker="DM", content="Let's continue with your character.", dialog_type="narration")]

    def generate_response_for_action(self, validated_action: Dict[str, Any], context: Dict) -> List[DialogResponse]:
        """
        Generate narrative responses based on a validated action.
        validated_action should contain at least "action_type", "action_data", "success".
        """
        action_type = validated_action.get("action_type", "unknown")
        success = validated_action.get("success", True)
        action_data = validated_action.get("action_data", {})

        # Use response generator to create immersive text
        if success:
            narrative = self._generate_success_narrative(action_type, action_data)
        else:
            narrative = self._generate_failure_narrative(action_type, action_data, validated_action.get("message", ""))

        dialog = DialogResponse(speaker="DM", content=narrative, dialog_type="narration")
        self.dialog_history.append(dialog)

        # Track consequences if needed
        if action_data.get("requires_consequence_tracking", False):
            self.consequence_tracker.add_unpaid_choice(action_data)

        return [dialog]

    def _generate_success_narrative(self, action_type: str, action_data: Dict) -> str:
        # Use AI or templates – for now, a simple placeholder
        if action_type == "character_created":
            char = action_data.get("character")
            return f"Behold! {char.name}, a {char.race} {char.classs.name}, steps into the world. Their journey begins now."
        return f"You successfully perform the action. The world reacts accordingly."

    def _generate_failure_narrative(self, action_type: str, action_data: Dict, error_msg: str) -> str:
        return f"Your attempt fails: {error_msg}"

    def generate_character_speech(self, player_id: str, message: str) -> List[DialogResponse]:
        """Handle in-character speech – simply echo and maybe generate NPC response."""
        return [DialogResponse(speaker="Player", content=message, dialog_type="character")]