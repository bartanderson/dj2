# test_puzzles.py
import unittest
from src.AIDMFramework import PuzzleEntity, PuzzleState, GameContext


class TestPuzzleSystem(unittest.TestCase):
    def setUp(self):
        self.context = GameContext()
        self.puzzle = PuzzleEntity("door_puzzle", "A locked door with three runes")
        self.puzzle_state = PuzzleState(self.context, self.puzzle)
        # ADD SOLUTION FOR ALL TESTS
        self.puzzle.set_solution("sequence", {"sequence": ["fire", "water", "earth"]})
        
    def test_sequence_puzzle(self):
        # Setup puzzle
        self.puzzle.set_solution("sequence", {"sequence": ["fire", "water", "earth"]})
        self.puzzle.add_hint("The runes glow in a specific order")
        self.puzzle.add_hint("Fire comes first, then water")
        
        # Test correct solution
        result = self.puzzle.attempt_solution({"sequence": ["fire", "water", "earth"]})
        self.assertTrue(result["success"])
        self.assertEqual(self.puzzle.state, "solved")
        
        # Test incorrect solution
        self.puzzle.reset()
        result = self.puzzle.attempt_solution({"sequence": ["water", "fire", "earth"]})
        self.assertFalse(result["success"])
        self.assertIn("hint", result)
        
    def test_puzzle_components(self):
        # Add puzzle component
        self.puzzle.add_component("rune1", "A fiery rune", {
            "touch": "The rune glows red",
            "press": "The rune sinks into the door"
        })
        
        # Test interaction
        result = self.puzzle.interact("rune1", "touch")
        self.assertEqual(result["response"], "The rune glows red")
        
        # Test invalid interaction
        result = self.puzzle.interact("rune1", "break")
        self.assertEqual(result["response"], "Nothing happens")
        
    def test_puzzle_state(self):
        # Enter puzzle state
        state_info = self.puzzle_state.enter()
        self.assertIn("description", state_info)
        self.assertIn("available_actions", state_info)
        
        # Test valid action
        result = self.puzzle_state.execute({"type": "examine"})
        self.assertIn("components", result)
        
        # Test invalid action
        result = self.puzzle_state.execute({"type": "invalid"})
        self.assertIn("error", result)
        
        # Test state exit
        exit_info = self.puzzle_state.exit()
        self.assertEqual(exit_info["message"], "Puzzle interaction ended")
        
    def test_contextual_description(self):
        desc = self.puzzle.get_contextual_description()
        self.assertIn("A locked door", desc)
        self.assertIn("No attempts have been made yet", desc)  # Updated expectation
        
        # After an attempt
        self.puzzle.attempt_solution({"sequence": ["wrong"]})
        desc = self.puzzle.get_contextual_description()
        self.assertIn("You've made 1 attempt", desc)  # Should now pass
        
    def test_hint_system(self):
        self.puzzle.add_hint("First hint")
        self.puzzle.add_hint("Second hint")
        
        # First hint level
        self.assertEqual(self.puzzle.get_hint(0), "First hint")
        
        # Second hint level
        self.assertEqual(self.puzzle.get_hint(1), "Second hint")
        
        # Beyond available hints
        self.assertEqual(self.puzzle.get_hint(2), "Second hint")
        
    def test_inspection_details(self):
        self.puzzle.add_component("rune1", "A fiery rune", {})
        details = self.puzzle.get_inspection_details("overview")
        self.assertIn("A locked door", details)
        
        details = self.puzzle.get_inspection_details("components")
        self.assertIn("rune1", details)
        
        # Test after an attempt
        self.puzzle.attempt_solution({"sequence": ["wrong"]})
        details = self.puzzle.get_inspection_details("analysis")
        self.assertIn("Based on your previous attempts", details)  # Updated expectation

if __name__ == "__main__":
    unittest.main()