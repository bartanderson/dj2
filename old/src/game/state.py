# src\game\state.py - Unified game state management
# from dungeon.renderers.base_renderer import BaseRenderer # not sure this is or needs to be called
from dungeon.renderers.image_renderer import ImageRenderer
from dungeon.renderers.web_renderer import WebRenderer
from dungeon.generator import EnhancedDungeonGenerator, DungeonGenerator
from dungeon.state import EnhancedDungeonState
from dungeon.objects import EnvironmentalEffect, MONSTER_DB, FEATURE_TEMPLATES
from src.AIDMFramework import PuzzleEntity
from typing import Tuple ,List #, Dict, Any, Optional, Union
import random

class TrapSystem:
    def __init__(self):
        self.traps = {}
        
    def add_trap(self, position, trap_type, dc, effect):
        trap_id = f"trap_{len(self.traps)+1}"
        self.traps[trap_id] = {
            "position": position,
            "type": trap_type,
            "dc": dc,  # Difficulty class to detect/avoid
            "effect": effect,
            "triggered": False
        }
        return trap_id

class ItemSystem:
    ITEM_TYPES = {
        "consumable": ["health_potion", "mana_potion", "antidote"],
        "equipment": ["sword", "shield", "armor"],
        "key_item": ["dungeon_key", "ancient_relic"],
        "quest": ["lost_amulet", "dragon_scale"],
        "valuable": ["gold_coins", "gemstone", "silver_ring"],
        "junk": ["broken_shard", "dusty_bone", "torn_cloth"],
        "special": ["get_out_of_jail_card", "mysterious_scroll"]
    }
    
    def __init__(self):
        self.items = {}
        self.item_counter = 1
        
    def create_item(self, item_type, subtype=None, **kwargs):
        """Create a new item with automatic categorization"""
        if subtype is None:
            if item_type in self.ITEM_TYPES:
                subtype = random.choice(self.ITEM_TYPES[item_type])
            else:
                subtype = "mysterious_item"
                
        item_id = f"item_{self.item_counter}"
        self.item_counter += 1
        
        self.items[item_id] = {
            "id": item_id,
            "name": kwargs.get("name", subtype.replace("_", " ").title()),
            "type": item_type,
            "subtype": subtype,
            "description": kwargs.get("description", f"A {subtype.replace('_', ' ')}"),
            "value": kwargs.get("value", random.randint(1, 100)),
            "weight": kwargs.get("weight", 0.1),
            "attributes": kwargs.get("attributes", {}),
            "discovered": False
        }
        return item_id
    
    def place_item(self, item_id, location_type, location_id, hidden=False):
        """Place item in a specific location"""
        item = self.items.get(item_id)
        if not item:
            return False
            
        item["location"] = {"type": location_type, "id": location_id}
        item["hidden"] = hidden
        return True

class UnifiedGameState:
    def __init__(self, campaign_theme="default"):
        self.campaign_theme = campaign_theme
        self.characters = {}
        self.monsters = {}
        self.active_quests = {}
        self.completed_quests = {}
        self.game_log = []
        self.dungeon_state: Optional[EnhancedDungeonState] = None
        self.current_level = None
        self.active_puzzle = None
        self.puzzle_history = {}
        self.npcs = {}
        self.items = {}
        self.game_context = None
        self.generation_seed = None


    def get_renderer(self, render_type='image'):
        if not self.dungeon_state:
            self.initialize_dungeon()
        
        if render_type == 'web':
            return WebRenderer(self.dungeon_state)
        else:  # Default to image renderer
            return ImageRenderer(self.dungeon_state)

    def initialize_dungeon(self, **params):
        """Create dungeon state from generator with given parameters"""

        # Store seed if provided, otherwise generate new one
        if 'seed' in params:
            self.generation_seed = params['seed']
        elif self.generation_seed is None:
            self.generation_seed = random.randint(1, 100000)

        generator = EnhancedDungeonGenerator({
            'seed': self.generation_seed,
            'n_rows': params.get('n_rows', 39),
            'n_cols': params.get('n_cols', 39),
            'room_min': params.get('room_min', 3),
            'room_max': params.get('room_max', 9),
            'theme': params.get('theme', 'dungeon'),
            'difficulty': params.get('difficulty', 'medium'),
            'feature_density': params.get('feature_density', 0.1)
        })

        dungeon_data = generator.create_dungeon()
        self.dungeon_state = EnhancedDungeonState(generator)
        self.current_level = 1
        self.party_position = self.find_starting_position()

        self.dungeon_state.grid = dungeon_data['grid']
        self.dungeon_state.stairs = dungeon_data['stairs']
        self.dungeon_state.rooms = dungeon_data['rooms']
        
    def find_starting_position(self) -> Tuple[int, int]:
        """Find stairs or suitable starting position in current dungeon"""
        if not self.dungeon_state:
            return (0, 0)
            
        # Use stairs if available
        if hasattr(self.dungeon_state, 'stairs') and self.dungeon_state.stairs:
            return self.dungeon_state.stairs[0]['position']
            
        # Find first open space
        for r in range(len(self.dungeon_state.grid)):
            for c in range(len(self.dungeon_state.grid[0])):
                cell = self.dungeon_state.grid[r][c]
                if cell.base_type & (DungeonGenerator.ROOM | DungeonGenerator.CORRIDOR):
                    return (r, c)
        return (0, 0)
    
    @property
    def party_position(self) -> Tuple[int, int]:
        """Get party position from dungeon state"""
        if self.dungeon_state:
            return self.dungeon_state.party_position
        return (0, 0)
    
    @party_position.setter
    def party_position(self, value: Tuple[int, int]):
        if self.dungeon_state:
            self.dungeon_state.party_position = value

    def move_party(self, direction: str) -> Tuple[int, int]:
        """Move party and return new position"""
        if not self.dungeon_state:
            return self.party_position
            
        old_pos = self.party_position
        
        # Get result from dungeon state
        result = self.dungeon_state.move_party(direction)
        print(f"game/state.move_party {result}")
        
        # Handle result
        if isinstance(result, tuple) and len(result) == 2:
            success, message = result
            if not success:
                self.log_event(f"Movement failed: {message}")
                return old_pos
        else:
            self.log_event(f"Movement failed: invalid response from dungeon state")
            return old_pos
            
        new_pos = self.party_position
        self.log_event(f"Party moved {direction} from {old_pos} to {new_pos}")
        # Force visibility update after move
        self.dungeon_state.visibility.update_visibility()
        return new_pos

    def get_available_moves(self) -> List[str]:
        """Get list of available movement directions from current position"""
        print("get_available_moves")
        if not self.dungeon_state:
            return []
        
        available = []
        position = self.party_position
        
        # Check all four directions
        for direction, vector in [('north', (-1, 0)), 
                                 ('south', (1, 0)), 
                                 ('east', (0, 1)), 
                                 ('west', (0, -1))]:
            new_x = position[0] + vector[0]
            new_y = position[1] + vector[1]
            if self.is_valid_position((new_x, new_y)):
                available.append(direction)
        
        return available

    def search_current_cell(self, search_skill=0):
        """Search the current cell"""
        if not self.dungeon_state:
            return False, "Dungeon not initialized", []
        
        position = self.party_position
        return self.dungeon_state.search_cell(position, search_skill)

    def add_dungeon_feature(self, feature_type: str, data: dict, position: Tuple[int, int] = None):
        """Add feature to current or specified position"""
        if not self.dungeon_state:
            self.initialize_dungeon()
            
        pos = position or self.party_position
        self.dungeon_state.add_feature(pos, feature_type, data)

    def get_current_room_description(self) -> str:
        """Get AI-generated description of current room"""
        if not self.dungeon_state:
            self.initialize_dungeon()

    def render_dungeon_image(self) -> "Image":
        """Render dungeon to PIL Image"""
        if not self.dungeon_state:
            self.initialize_dungeon()
            
        return self.dungeon_state.render_to_image()
        
    def render_dungeon_web(self) -> dict:
        """Render dungeon for web interface"""
        if not self.dungeon_state:
            self.initialize_dungeon()
            
        return self.dungeon_state.render_to_web()
        
    def log_event(self, event: str):
        """Add entry to game log"""
        self.game_log.append(event)


    def add_npc(self, npc_id, name, position, dialogue, role="neutral"):
        self.npcs[npc_id] = {
            'name': name,
            'position': position,
            'dialogue': dialogue,
            'role': role,
            'quests': []
        }
    
    def interact_with_npc(self, npc_id):
        npc = self.npcs.get(npc_id)
        if not npc:
            return "No NPC found"
        
        # Check if NPC is nearby
        if npc['position'] not in self.dungeon_state.visibility.get_visible_cells():
            return f"{npc['name']} is too far to interact with"
        
        return {
            'name': npc['name'],
            'dialogue': npc['dialogue'],
            'quests': npc.get('quests', [])
        }

    def assign_quest(self, npc_id, quest_id):
        if npc_id in self.npcs and quest_id in self.active_quests:
            self.npcs[npc_id]['quests'].append(quest_id)
            return True
        return False
        
    def find_starting_position(self):
        """Find stairs or suitable starting position"""
        if self.dungeon_state.stairs and len(self.dungeon_state.stairs) > 0:
            return self.dungeon_state.stairs[0]['position']
        # Find first open space
        for r in range(len(self.dungeon_state.grid)):
            for c in range(len(self.dungeon_state.grid[0])):
                if self.dungeon_state.grid[r][c].base_type & (DungeonGenerator.ROOM | DungeonGenerator.CORRIDOR):
                    return (r, c)
        return (0, 0)
    
    def generate_new_level(self, **params):
        self.initialize_dungeon(**params)
        self.game_log.append(f"Descended to dungeon level {self.current_level}")
        
    def add_character(self, character):
        self.characters[character.id] = character
        character.position = self.party_position

    def get_character(self, character_id: str):
        """Get a character by ID"""
        return self.characters.get(character_id)
            
    def is_valid_position(self, pos):
        """Check if position is traversable"""
        x, y = pos
        if not self.dungeon_state:
            return False
        # Check bounds
        if not (0 <= x < len(self.dungeon_state.grid) and 
                0 <= y < len(self.dungeon_state.grid[0])):
            return False
        
        # Check cell type    
        cell = self.dungeon_state.grid[x][y]
        return cell and bool(cell.current_type & (DungeonGenerator.ROOM | DungeonGenerator.CORRIDOR))

    def complete_puzzle(self, puzzle_id: str):
        """Mark a puzzle as completed"""
        self.puzzle_history[puzzle_id] = {
            "timestamp": datetime.now().isoformat(),
            "attempts": len(self.active_puzzle.attempts)
        }
        self.active_puzzle = None

    def activate_puzzle(self, puzzle_id: str) -> PuzzleEntity:
        """Activate a puzzle with hints from dungeon state"""
        # Get puzzle data from dungeon
        puzzle_data = self.dungeon_state.get_puzzle_data(puzzle_id)
        
        # Create puzzle entity
        puzzle = PuzzleEntity(
            puzzle_id, 
            puzzle_data['description'],
            success_effect=puzzle_data['success_effect']
        )
        
        # Add hints
        for hint in puzzle_data.get('hints', []):
            puzzle.add_hint(hint['text'])
            
        return puzzle