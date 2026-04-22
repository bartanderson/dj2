#!/usr/bin/env python
"""
Diagnostic tool for character creation flow.
Simulates a conversation with mocked AI responses and logs each step.
Run from project root: python tools/debug_creation_flow.py
"""
import sys
import json
from unittest.mock import Mock
from world.session_system import SessionSystem
from world.dm_chat_handler import DMChatHandler
from world.dm_chat_ai import DMChatAI
from world.authority_system import AuthoritySystem, ValidatedAction
from world.tool_system import ToolRegistry
from world.consequence_engine import ConsequenceEngine
from world.ai_dungeon_master import Dialog

# ----------------------------------------------------------------------
# Mock AI system that returns canned responses based on prompt content
# ----------------------------------------------------------------------
class MockAISystem:
    def generate_structured_data(self, prompt, schema):
        prompt_lower = prompt.lower()
        # Intent classification
        if "classify player intent" in prompt_lower:
            import re
            # Extract the player's message from the prompt (assuming format: Player says: "...")
            match = re.search(r'Player says: "([^"]+)"', prompt)
            player_msg = match.group(1).lower() if match else ""
            
            # Keyword-based intent classification
            if any(word in player_msg for word in ["what", "how", "why", "tell me about", "explain"]):
                intent = "world_inquiry"
            elif any(word in player_msg for word in ["i want", "i'd like", "i am", "i'm", "my character", "be a"]):
                intent = "declare_intent"
            elif any(word in player_msg for word in ["yes", "no", "confirm", "correct", "that's right"]):
                intent = "confirmation"
            elif any(word in player_msg for word in ["help", "suggest", "recommend", "any ideas"]):
                intent = "seeking_guidance"
            elif "?" in player_msg:
                intent = "clarification"
            else:
                intent = "narrative_input"
            
            return {
                "intent": intent,
                "confidence": 0.9,
                "target": "character",
                "parameters": {},
                "reasoning": "Mock keyword classification"
            }
        # Character data extraction
        if "extract character creation information" in prompt_lower:
            # Return empty dict to simulate no data found
            return {}
        # Next question suggestion
        if "suggest the next question" in prompt_lower:
            return {
                "question": "What race would you like your character to be?",
                "category": "race"
            }
        # Class suggestion
        if "suggest the most appropriate" in prompt_lower:
            return {
                "primary_class": "fighter",
                "secondary_class": "",
                "explanation": "Mock suggestion",
                "custom_traits": []
            }
        # Confirmation interpretation
        if "determine if this message is a confirmation" in prompt_lower:
            return {
                "is_confirmation": False,
                "corrected_value": None,
                "confidence": 0.5,
                "interpretation": "Mock interpretation"
            }
        return {}

    def generate_text(self, prompt):
        # Return a longer, substantive answer to pass quality checks
        return "In Dungeons & Dragons, magic comes in several forms. Arcane magic is wielded by wizards and sorcerers, divine magic by clerics and paladins, and primal magic by druids and rangers. Each has its own flavor and mechanics. Would you like to know more about any of these?"

# ----------------------------------------------------------------------
# Mock world controller with minimal required attributes
# ----------------------------------------------------------------------
class MockWorldController:
    def __init__(self, ai_system, session_system):
        self.ai_system = ai_system
        self.dm_chat_ai = ChatAI(ai_system)
        self.session_system = session_system
        self.tool_registry = ToolRegistry()
        self.authority_system = AuthoritySystem(self.tool_registry)
        self.consequence_engine = ConsequenceEngine(world_controller=self, dm_chat_ai=self.chat_ai)
        # For backward compatibility
        self.dungeon_master = self.consequence_engine
        self.players = {}
        self.character_manager = Mock()
        self.world_data = {"name": "Test World", "theme": "fantasy"}
        self.world_ai = Mock()
        self.world_ai.generate_text.return_value = "Mock world AI response."

    def get_or_create_player(self, session_id, player_name=None):
        # Return a simple mock player
        class MockPlayer:
            def __init__(self, name):
                self.id = f"player_{hash(name)}"
                self.name = name
                self.character_ids = []
                self.active_character_id = None
            def set_active_character(self, char_id):
                self.active_character_id = char_id
        player = MockPlayer(player_name or f"Player_{session_id[:8]}")
        self.players[player.id] = player
        return player

# ----------------------------------------------------------------------
# Main diagnostic routine
# ----------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Character Creation Flow Diagnostic")
    print("=" * 60)

    # Setup
    ai_system = MockAISystem()
    session_system = SessionSystem()
    world_controller = MockWorldController(ai_system, session_system)
    handler = DMChatHandler(world_controller)

    session_id = "test-session"
    player_id = "player1"
    session_system.get_or_create_session(session_id, player_id)

    # Test messages (from the logs)
    test_messages = [
        "Can I be a giraffe?",
        "can I be a god?",
        "What kind of magic is there?",
        "Arcana sounds interesting",
        "Maybe incantations instead?",
        "Maybe enchantment",
        "Tell me about it",
        "That sounds cool. I want that",
        "No, I said enchantment",
        "Enchantment",
        "What class did you write down?",
        "I thought Arcana and Enchantment were different",
        "I want divine magic, not arcane",
        "what are my choices so far?",
    ]

    print("\nStarting conversation...\n")
    for i, msg in enumerate(test_messages, 1):
        print(f"[{i}] User: {msg}")
        result = handler.process_message(session_id, msg, character_id=None)
        if result and "narrative" in result:
            for d in result["narrative"]:
                print(f"    DM: {d.content}")
        else:
            print("    [No narrative returned]")
        # Show current character data
        session = session_system.get_session(session_id)
        print(f"    State: {session.character_data}")
        print()

    print("=" * 60)
    print("Diagnostic complete.")
    print("Check the output above to see where the flow diverges from expectations.")
    print("If a message produced no narrative or an unexpected response, that indicates a logic gap.")

if __name__ == "__main__":
    main()