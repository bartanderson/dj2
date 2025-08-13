# tests/test_helpers.py
from src.AIDMFramework import Character, AbilityScores, EnhancedGameContext
from src.game.state import UnifiedGameState
from src.ai.dm_agent import EnhancedDMAgent
import uuid

def create_test_game_state():
    """Create a pre-configured game state for testing"""
    game_state = UnifiedGameState()
    game_context = EnhancedGameContext() 
    dm_agent = EnhancedDMAgent(game_state, game_context)
    
    # Create party
    warrior = Character(
        id=str(uuid.uuid4()),
        name="Test Warrior",
        race="Human",
        character_class="Warrior",
        level=3,
        abilities=AbilityScores(strength=16, dexterity=10, constitution=14),
        hit_points={"current": 30, "maximum": 30},
        armor_class=16,
        position=(0, 0)
    )
    
    mage = Character(
        id=str(uuid.uuid4()),
        name="Test Mage",
        race="Elf",
        character_class="Mage",
        level=3,
        abilities=AbilityScores(intelligence=16, dexterity=14, constitution=10),
        hit_points={"current": 20, "maximum": 20},
        armor_class=12,
        position=(0, 0)
    )
    
    game_state.add_character(warrior)
    game_state.add_character(mage)
    game_state.party_position = (0, 0)
    
    return game_state, dm_agent