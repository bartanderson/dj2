# test_ai_integration.py
from agno.models.message import Message
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from src.ai.dm_agent import EnhancedDMAgent, EnhancedGameContext
from src.game.state import UnifiedGameState
from src.AIDMFramework import PuzzleEntity, Character
import uuid

class TestAIPuzzleIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.game_state = UnifiedGameState()
        self.game_context = EnhancedGameContext()  # Create game context
        self.dm_agent = EnhancedDMAgent(self.game_state, self.game_context)  # Pass context
        
        # Create puzzle with type and effect
        self.puzzle = PuzzleEntity(
            "test_puzzle", 
            "A test puzzle",
            success_effect="Test mechanism activates"
        )
        self.puzzle.add_component("gem_slot", "A slot for gems", {"insert": "The gem fits perfectly"})
        self.puzzle.add_hint("First hint")
        self.puzzle.add_hint("Second hint: Try changing the second step")

        # Mock dungeon state
        self.game_state.dungeon_state = MagicMock()
        self.game_state.dungeon_state.get_current_room_id = MagicMock(return_value="test_room")
        self.game_state.dungeon_state.rooms = {
            "test_room": {"puzzle": self.puzzle}
        }
        
        # Properly mock methods
        self.dm_agent._detect_player_intent = MagicMock(return_value="puzzle")
        self.dm_agent.get_party_summary = MagicMock(return_value="Test party summary")
        self.dm_agent._get_current_dungeon_theme = MagicMock(return_value="test theme")
        self.dm_agent._get_current_situation_description = MagicMock(
            return_value="Test situation description"
        )
        
        # Mock puzzle activation
        self.game_state.activate_puzzle = MagicMock(return_value=self.puzzle)
        self.game_state.complete_puzzle = MagicMock()
        self.game_state.active_puzzle = None


    async def test_puzzle_solution(self):
        # Activate the puzzle
        self.game_state.active_puzzle = self.puzzle
        self.puzzle.attempt_solution = MagicMock(return_value={
            "success": True,
            "message": "Solved! Test mechanism activates"
        })
        self.puzzle.state = "solved"  # Simulate solved state
        self.game_state.complete_puzzle = MagicMock()
        
        # Process a puzzle solution
        response = await self.dm_agent.process_command("solve with correct solution", "player1")
        
        # Verify success effect appears in response
        self.assertIn("mechanism activates", response["response"].lower())
        self.assertTrue(self.puzzle.state == "solved")
        
    async def test_puzzle_hint_request(self):
        """Test AI provides hints when requested"""
        # Activate the puzzle
        self.game_state.active_puzzle = self.puzzle
        self.puzzle.add_hint("First hint")
        
        # Request a hint explicitly
        response = await self.dm_agent.process_command("I'm stuck, give me a hint", "player1")
        self.assertIn("hint", response["response"].lower())
        
    async def test_puzzle_action_processing(self):
        # Activate the puzzle
        self.game_state.active_puzzle = self.puzzle
        self.puzzle.attempt_solution = MagicMock(return_value={
            "success": False,
            "message": "Incorrect solution"
        })
        
        # Process a puzzle action
        response = await self.dm_agent.process_command("solve with wrong solution", "player1")
        # Update assertion to match actual response text:
        self.assertIn("that didn't work", response["response"].lower())
        self.puzzle.attempt_solution.assert_called()
        
    async def test_puzzle_hint_retrieval(self):
        """Test AI provides correct hints"""
        # Activate the puzzle
        self.game_state.active_puzzle = self.puzzle
        
        # Request a hint
        response = await self.dm_agent.process_command("I need a hint", "player1")
        
        # Verify hint appears in response
        self.assertIn("first hint", response["response"].lower())

    async def test_puzzle_solution(self):
        """Test AI handles puzzle solutions with effect-based messages"""
        # Activate the puzzle
        self.game_state.active_puzzle = self.puzzle
        # Fix the mock to update puzzle state on success
        def attempt_solution(*args, **kwargs):
            self.puzzle.state = "solved"
            return {"success": True, "message": "Solved!"}
            
        self.puzzle.attempt_solution = MagicMock(side_effect=attempt_solution)
        self.game_state.complete_puzzle = MagicMock()
        
        # Process solution
        response = await self.dm_agent.process_command("solve with correct solution", "player1")
        
        # Verify success effect and completion
        self.assertIn("mechanism activates", response["response"].lower())
        self.game_state.complete_puzzle.assert_called()

    @patch.object(EnhancedDMAgent, '_generate_puzzle_hint')
    async def test_intelligent_hinting(self, mock_hint):
        """Test AI provides intelligent hints based on progress"""
        # Activate the puzzle
        self.game_state.active_puzzle = self.puzzle
        self.puzzle.attempts = [{"sequence": ["wrong1"]}, {"sequence": ["wrong2"]}]
        
        # Request a hint
        mock_hint.return_value = "Try changing the second step"
        response = await self.dm_agent.process_command("I need help", "player1")
        
        self.assertIn("second step", response["response"])
        mock_hint.assert_called_with(self.puzzle)  # Only one argument now

class TestAINonPuzzleCommands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.game_state = UnifiedGameState()
        self.game_context = EnhancedGameContext()  # Create game context
        self.dm_agent = EnhancedDMAgent(self.game_state, self.game_context)  # Pass both
        
        # Create a character
        self.character = Character(
            id="player1",
            name="TestPlayer",
            character_class="Warrior",
            level=5
        )
        self.game_state.add_character(self.character)
        
        # Mock dungeon state
        self.game_state.dungeon_state = MagicMock()
        self.game_state.dungeon_state.get_room_description = MagicMock(
            return_value="A dark dungeon corridor"
        )
        
        # Properly mock methods
        self.dm_agent._detect_player_intent = MagicMock(return_value="exploration")
        self.dm_agent.get_party_summary = MagicMock(return_value="Test party summary")
        self.dm_agent._get_current_dungeon_theme = MagicMock(return_value="test theme")
        self.dm_agent._get_current_situation_description = MagicMock(
            return_value="Test situation description"
        )
        
        # Mock model responses
        self.dm_agent.model.invoke = MagicMock(return_value="Test response")

    async def test_exploration_command(self):
        """Test exploration command handling"""
        response = await self.dm_agent.process_command("search the room", "player1")
        self.assertIn("Test response", response["response"])


    async def test_combat_command(self):
        """Test combat command handling"""
        response = await self.dm_agent.process_command("attack the goblin", "player1")
        self.assertIn("Test response", response["response"])


    async def test_dialogue_command(self):
        """Test NPC dialogue handling"""
        response = await self.dm_agent.process_command("ask about the secret passage", "player1")
        self.assertIn("Test response", response["response"])


    async def test_rest_command(self):
        """Test rest command handling"""
        response = await self.dm_agent.process_command("take a short rest", "player1")
        self.assertIn("Test response", response["response"])


    async def test_general_command(self):
        """Test general command handling"""
        response = await self.dm_agent.process_command("dance wildly", "player1")
        self.assertIn("Test response", response["response"])


if __name__ == "__main__":
    unittest.main()