# test_persistence.py
import unittest
import os
from src.AIDMFramework import EnhancedGameContext, GamePersistence, Character
from src.game.state import UnifiedGameState
from test_helpers import create_test_game_state

class TestGamePersistence(unittest.TestCase):
    def setUp(self):
        self.game_state, self.dm_agent = create_test_game_state()
        self.test_file = "test_save.json"
        self.game = EnhancedGameContext()
        # Initialize with test data
        self.game.campaign_journal = "Test campaign"
        self.game.campaign_themes = ["exploration", "mystery"]
        
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
            
    def test_save_and_load(self):
        # Save the game
        save_result = GamePersistence.save_game(self.game, self.test_file)
        self.assertTrue(save_result)
        
        # Load the game
        loaded_game = GamePersistence.load_game(self.test_file)
        
        # Verify data integrity
        self.assertEqual(loaded_game.campaign_journal, self.game.campaign_journal)
        self.assertEqual(loaded_game.campaign_themes, self.game.campaign_themes)
        
    def test_character_persistence(self):
        # Add a character
        char = Character(
            name="Test Hero",
            race="Elf",
            character_class="Ranger",
            level=5
        )
        self.game.add_character(char)
        
        # Save and load
        GamePersistence.save_game(self.game, self.test_file)
        loaded_game = GamePersistence.load_game(self.test_file)
        
        # Verify character data
        loaded_char = next(iter(loaded_game.characters.values()))
        self.assertEqual(loaded_char.name, "Test Hero")
        self.assertEqual(loaded_char.level, 5)

if __name__ == "__main__":
    unittest.main()