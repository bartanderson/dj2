# test_runner.py
from src.game.state import UnifiedGameState
from src.ai.dm_agent import EnhancedDMAgent
from dungeon.generator import EnhancedDungeonGenerator
from src.AIDMFramework import Character, AbilityScores
import uuid
import asyncio

class TestHarness:
    def __init__(self):
        self.game_state = UnifiedGameState()
        # Create dummy game context since it's required by EnhancedDMAgent
        class DummyGameContext:
            def start_puzzle(self, puzzle): pass
            def change_state(self, state): pass
        self.game_context = DummyGameContext()
        
        self.dm_agent = EnhancedDMAgent(self.game_state, self.game_context)
        
        # Create a test party
        self.party = [
            self._create_test_character("Warrior", "Human", position=(0, 0)),
            self._create_test_character("Mage", "Elf", position=(0, 0))
        ]
        
        # Add characters to game state
        for character in self.party:
            self.game_state.add_character(character)
        
        # Set starting position
        self.game_state.party_position = (0, 0)
        
        # Set test player
        self.test_player = self.party[0]
        
        # Create event loop for async operations
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def _create_test_character(self, character_class, race, position):
        """Create a proper character instance"""
        return Character(
            id=str(uuid.uuid4()),
            name=f"Test {character_class}",
            race=race,
            character_class=character_class,
            level=3,
            abilities=AbilityScores(strength=14, dexterity=12, constitution=13),
            hit_points={"current": 25, "maximum": 25},
            armor_class=14,
            position=position
        )

    def run_command(self, command):
        return self.loop.run_until_complete(
            self.dm_agent.process_command(command, self.test_player.id)
        )

    def visualize_dungeon(self):
        # Implement visualization using dungeon_renderer
        pass

    def debug_state(self):
        print("\n--- CURRENT STATE ---")
        print(f"Party Position: {self.game_state.party_position}")
        print(f"Current Level: {self.game_state.current_level}")
        print(f"Active Quests: {len(self.game_state.active_quests)}")
        
        # Print nearby features
        if hasattr(self.game_state, 'dungeon_state') and self.game_state.dungeon_state:
            features = self.game_state.dungeon_state.get_cell_features(
                self.game_state.party_position
            )
            if features:
                print(f"Features: {', '.join(f['type'] for f in features)}")
    
    def __del__(self):
        # Close the event loop when the harness is destroyed
        self.loop.close()
            
# Example test sequence
if __name__ == "__main__":
    harness = TestHarness()
    
    # Initialize dungeon
    harness.dm_agent.generate_dungeon_level(
        theme="ruins",
        difficulty="medium"
    )
    
    # Initial debug
    harness.debug_state()
    
    # Test movement
    response = harness.run_command("We move north")
    print("\nMovement Response:", response)
    harness.debug_state()
    
    # Test interaction
    response = harness.run_command("I search the room")
    print("\nSearch Response:", response)
    
    # Test NPC creation
    response = harness.run_command(
        "Create a mysterious old wizard near us"
    )
    print("\nNPC Creation:", response)