# world/consequence_engine.py
"""
Consequence Engine – generates narrative responses from validated actions.
Phase: Consequence (narration)
"""

from typing import List, Dict, Any, Optional
from world.ai_dungeon_master import Dialog, ConsequenceTracker, ResponseGenerator

class ConsequenceEngine:
    def __init__(self, world_controller=None, dm_chat_ai=None):
        self.world_controller = world_controller
        self.dm_chat_ai = dm_chat_ai
        self.consequence_tracker = ConsequenceTracker()
        self.response_generator = ResponseGenerator()
        self.dialog_history = []

    def generate_response_for_action(self, validated_action: Dict[str, Any], context: Dict) -> List[Dialog]:
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

        dialog = Dialog("DM", narrative, "narration")
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

    def generate_character_speech(self, player_id: str, message: str) -> List[Dialog]:
        """Handle in-character speech – simply echo and maybe generate NPC response."""
        return [Dialog("Player", message, "character")]