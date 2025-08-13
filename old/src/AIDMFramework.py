from dungeon.state import DungeonState, DungeonCell
from dungeon.renderer import DungeonRenderer
from dungeon.generator import DungeonGenerator # for CELL_TYPES
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Callable, Union
import json
import random
import logging
from datetime import datetime
import uuid

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class GameState(Enum):
    SETUP = auto()
    EXPLORATION = auto()
    COMBAT = auto()
    SOCIAL = auto()
    REST = auto()
    PUZZLE = auto()
    TRANSITION = auto()
    PAUSED = auto()

class ActionType(Enum):
    ATTACK = auto()
    SPELL = auto()
    SKILL_CHECK = auto()
    SAVING_THROW = auto()
    MOVEMENT = auto()
    INTERACTION = auto()
    REST = auto()

class DifficultyClass(Enum):
    TRIVIAL = 5
    EASY = 10
    MODERATE = 15
    HARD = 20
    VERY_HARD = 25
    NEARLY_IMPOSSIBLE = 30

# ============================================================================
# STATE MACHINE FRAMEWORK
# ============================================================================

class State(ABC):
    """Abstract base class for game states"""
    
    def __init__(self, context: 'GameContext'):
        self.context = context
    
    @abstractmethod
    def enter(self) -> Dict[str, Any]:
        """Called when entering this state"""
        pass
    
    @abstractmethod
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process an action in this state"""
        pass
    
    @abstractmethod
    def exit(self) -> Dict[str, Any]:
        """Called when leaving this state"""
        pass
    
    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """Return list of available actions in this state"""
        pass

class ExplorationState(State):
    def enter(self) -> Dict[str, Any]:
        return {
            "message": "Entering exploration mode",
            "environment": self.context.environment,
            "available_actions": self.get_available_actions()
        }
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "")
        
        if action_type == "move":
            return self._handle_movement(action)
        elif action_type == "search":
            return self._handle_search(action)
        elif action_type == "interact":
            return self._handle_interaction(action)
        elif action_type == "rest":
            self.context.change_state(GameState.REST)
            return {"message": "Initiating rest"}
        
        return {"error": "Unknown action type"}
    
    def exit(self) -> Dict[str, Any]:
        return {"message": "Leaving exploration mode"}
    
    def get_available_actions(self) -> List[str]:
        return ["move", "search", "interact", "rest", "cast_spell", "use_item"]
    
    def _handle_movement(self, action: Dict[str, Any]) -> Dict[str, Any]:
        # Integration point for dungeon generator
        direction = action.get("direction", "")
        result = self.context.dungeon_interface.move_party(direction)
        return result
    
    def _handle_search(self, action: Dict[str, Any]) -> Dict[str, Any]:
        character = self.context.get_character(action.get("character_id"))
        dc = action.get("dc", DifficultyClass.MODERATE.value)
        result = RuleEngine.resolve_skill_check(character, "perception", dc)
        return result
    
    def _handle_interaction(self, action: Dict[str, Any]) -> Dict[str, Any]:
        target = action.get("target", "")
        # Handle NPC interactions, object manipulation, etc.
        return {"message": f"Interacting with {target}"}

class CombatState(State):
    def enter(self) -> Dict[str, Any]:
        self._roll_initiative()
        return {
            "message": "Combat begins!",
            "initiative_order": self.context.combat.initiative_order,
            "current_actor": self.context.combat.get_current_actor()
        }
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if not self._is_current_actor(action.get("character_id")):
            return {"error": "Not your turn"}
        
        action_type = action.get("type", "")
        
        if action_type == "attack":
            result = self._handle_attack(action)
        elif action_type == "spell":
            result = self._handle_spell(action)
        elif action_type == "move":
            result = self._handle_combat_movement(action)
        elif action_type == "end_turn":
            result = self._end_turn()
        else:
            return {"error": "Invalid combat action"}
        
        # Check if combat should end
        if self._should_end_combat():
            self.context.change_state(GameState.EXPLORATION)
        
        return result
    
    def exit(self) -> Dict[str, Any]:
        self.context.combat = None
        return {"message": "Combat ended"}
    
    def get_available_actions(self) -> List[str]:
        return ["attack", "spell", "move", "dodge", "dash", "help", "hide", "ready", "end_turn"]


class SocialState(State):
    def enter(self) -> Dict[str, Any]:
        return {
            "message": "Entering social interaction mode",
            "available_actions": self.get_available_actions(),
            "npcs": self.context.environment.npcs_present
        }
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "")
        npc_id = action.get("npc_id", "")
        
        if action_type == "talk":
            return self._handle_conversation(npc_id, action.get("topic", ""))
        elif action_type == "persuade":
            return self._handle_persuasion(npc_id, action.get("approach", ""))
        elif action_type == "end_conversation":
            self.context.change_state(GameState.EXPLORATION)
            return {"message": "Ending conversation"}
        
        return {"error": "Unknown social action"}
    
    def exit(self) -> Dict[str, Any]:
        return {"message": "Leaving social interaction mode"}
    
    def get_available_actions(self) -> List[str]:
        return ["talk", "persuade", "intimidate", "bribe", "end_conversation"]
    
    def _handle_conversation(self, npc_id: str, topic: str) -> Dict[str, Any]:
        # Simplified conversation handling
        npc = self.context.npc_manager.npcs.get(npc_id)
        if not npc:
            return {"error": "NPC not found"}
        
        return {
            "response": f"{npc['name']} responds: 'I'm not sure about {topic}...'",
            "npc_mood": npc.get("current_mood", "neutral")
        }
    
    def _handle_persuasion(self, npc_id: str, approach: str) -> Dict[str, Any]:
        npc = self.context.npc_manager.npcs.get(npc_id)
        if not npc:
            return {"error": "NPC not found"}
        
        # Simplified persuasion check
        character = self.context.get_character(action.get("character_id"))
        skill = "persuasion" if approach == "friendly" else "intimidation"
        result = RuleEngine.resolve_skill_check(character, skill, 15)
        
        return {
            "success": result["success"],
            "npc_reaction": "convinced" if result["success"] else "unconvinced",
            "roll_result": result
        }

class RestState(State):
    def enter(self) -> Dict[str, Any]:
        return {
            "message": "Party is taking a rest",
            "available_actions": self.get_available_actions()
        }
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "")
        
        if action_type == "short_rest":
            return self._handle_short_rest()
        elif action_type == "long_rest":
            return self._handle_long_rest()
        elif action_type == "end_rest":
            self.context.change_state(GameState.EXPLORATION)
            return {"message": "Ending rest period"}
        
        return {"error": "Unknown rest action"}
    
    def exit(self) -> Dict[str, Any]:
        return {"message": "Rest period ended"}
    
    def get_available_actions(self) -> List[str]:
        return ["short_rest", "long_rest", "keep_watch", "end_rest"]
    
    def _handle_short_rest(self) -> Dict[str, Any]:
        # Heal characters for short rest
        for char in self.context.characters.values():
            char.heal(char.level)
        
        return {
            "message": "Party takes a short rest",
            "healing": f"Each character healed {char.level} hit points"
        }
    
    def _handle_long_rest(self) -> Dict[str, Any]:
        # Full heal and reset abilities
        for char in self.context.characters.values():
            char.heal(char.hit_points["maximum"])
            # Reset spells and abilities
        
        return {
            "message": "Party takes a long rest",
            "effect": "All characters fully healed, spells and abilities reset"
        }

class PuzzleEntity:
    """Complete puzzle implementation with all necessary methods"""
    def __init__(self, puzzle_id: str, description: str, success_effect: str = "A hidden compartment opens"):
        self.id = puzzle_id
        self.description = description
        self.state = "unsolved"
        self.solution = {"type": "dummy", "data": {"sequence": []}}  # Default solution
        self.attempts = []
        self.hints = []
        self.components = {}
        self.success_effect = success_effect  # What happens when puzzle is solved

    def execute_action(self, action: Dict) -> Dict:
        """Execute a puzzle action based on type"""
        action_type = action.get("type")
        
        if action_type == "solve":
            return self.attempt_solution(action.get("solution", {}))
        elif action_type == "interact":
            return self.interact(
                action.get("component_id"), 
                action.get("action")
            )
        elif action_type == "reset":
            self.reset()
            return {"message": "Puzzle reset"}
        else:
            return {"error": "Invalid puzzle action"}
    
    def get_available_actions(self) -> List[str]:
        """Get available actions for the puzzle"""
        actions = ["solve", "examine", "abandon"]
        if self.components:
            actions.append("interact")
        if self.attempts:
            actions.append("reset")
        return actions
    
    def get_success_message(self, action: Dict) -> str:
        """Generate success message based on the puzzle's effect"""
        return f"You solved the puzzle! {self.success_effect}"
    
    def get_failure_message(self, action: Dict) -> str:
        """Get failure message for an action"""
        return "Nothing happens. That didn't seem to work."
        
    def set_solution(self, solution_type: str, solution_data: dict):
        """Define the puzzle solution (fully implemented)"""
        self.solution = {
            "type": solution_type,
            "data": solution_data
        }
        
    def add_component(self, component_id: str, description: str, states: dict):
        """Add an interactive component to the puzzle (fully implemented)"""
        self.components[component_id] = {
            "description": description,
            "current_state": "default",
            "states": states
        }
        
    def add_hint(self, hint: str, condition: str = "always"):
        """Add a hint with display condition (fully implemented)"""
        self.hints.append({
            "text": hint,
            "condition": condition
        })
        
    def attempt_solution(self, solution_data: dict) -> dict:
        """Evaluate a solution attempt (fully implemented)"""
        self.attempts.append(solution_data)
        
        if not self.solution:
            return {"success": False, "message": "No solution defined"}
            
        if self.solution["type"] == "sequence":
            return self._check_sequence(solution_data)
        elif self.solution["type"] == "code":
            return self._check_code(solution_data)
        elif self.solution["type"] == "pattern":
            return self._check_pattern(solution_data)
        else:
            return {"success": False, "message": "Unknown solution type"}
    
    def _check_sequence(self, solution_data: dict) -> dict:
        """Verify sequence solution (fully implemented)"""
        required = self.solution["data"]["sequence"]
        provided = solution_data.get("sequence", [])
        
        if required == provided:
            self.state = "solved"
            return {
                "success": True,
                "message": "Correct sequence! Puzzle solved"
            }
        return {
            "success": False,
            "message": "Incorrect sequence",
            "hint": self._get_hint()
        }
    
    def _check_code(self, solution_data: dict) -> dict:
        """Verify code solution (fully implemented)"""
        required = self.solution["data"]["code"]
        provided = solution_data.get("code", "")
        
        if required == provided:
            self.state = "solved"
            return {
                "success": True,
                "message": "Correct code! Puzzle solved"
            }
        return {
            "success": False,
            "message": "Incorrect code",
            "hint": self._get_hint()
        }
    
    def _get_hint(self) -> str:
        """Get appropriate hint based on attempts (fully implemented)"""
        if not self.hints:
            return "No hints available"
            
        if len(self.attempts) < 2:
            return self.hints[0]["text"]
        elif len(self.attempts) < 4:
            return self.hints[1]["text"] if len(self.hints) > 1 else self.hints[0]["text"]
        else:
            return self.hints[-1]["text"]
    
    def interact(self, component_id: str, action: str) -> dict:
        """Interact with a puzzle component (fully implemented)"""
        component = self.components.get(component_id)
        if not component:
            return {"error": "Component not found"}
            
        response = component["states"].get(action, "Nothing happens")
        return {"response": response}
    
    def reset(self):
        """Reset puzzle to initial state (fully implemented)"""
        self.state = "unsolved"
        self.attempts = []
        for component in self.components.values():
            component["current_state"] = "default"

    def get_contextual_description(self) -> str:
        """Get dynamic description based on puzzle state"""
        base = self.description
        
        if self.state == "solved":
            return f"{base} The puzzle has been solved."
        
        attempts = len(self.attempts)
        if attempts == 0:
            base += "\nNo attempts have been made yet."
        else:
            base += f"\nYou've made {attempts} attempt{'s' if attempts > 1 else ''}."
        
        if attempts >= 2:
            base += f"\n{self._get_hint()}"
        
        return base

    def get_hint(self, level: int = 0) -> str:
        """Get hint based on progress and request level"""
        if not self.hints:
            return "No hints available for this puzzle."
        
        hint_level = min(level, len(self.hints) - 1)
        return self.hints[hint_level]["text"]

    def get_hint_level(self) -> int:
        """Determine appropriate hint level based on progress"""
        attempts = len(self.attempts)
        if attempts < 2:
            return 0
        elif attempts < 4:
            return 1
        else:
            return 2

    def get_inspection_details(self, focus: str = "overview") -> str:
        """Return detailed examination information"""
        details = {
            "overview": self.description,
            "components": "\n".join([f"- {cid}: {comp['description']}" 
                                 for cid, comp in self.components.items()])
        }
        
        if self.state == "unsolved":
            if len(self.attempts) > 0:
                details["analysis"] = ("Based on your previous attempts, "
                                      f"{self._get_attempt_analysis()}")
            else:
                details["analysis"] = "No attempts have been made yet."
        
        return details.get(focus, "No additional details available.")

    def _get_attempt_analysis(self) -> str:
        """Generate analysis of previous attempts"""
        if not self.attempts:
            return "No analysis available yet."
        
        if not self.solution:
            return "The puzzle seems unsolvable currently."
            
        last_attempt = self.attempts[-1]
        if "sequence" in last_attempt and "sequence" in self.solution.get("data", {}):
            return ("the sequence was close but needs adjustment in the "
                    f"{self._identify_sequence_error(last_attempt['sequence'])}")
        
        return "you're making progress but haven't found the solution yet."

    def _identify_sequence_error(self, sequence: list) -> str:
        """Identify where a sequence went wrong"""
        if not self.solution or "data" not in self.solution:
            return "the sequence steps"
            
        solution_seq = self.solution["data"].get("sequence", [])
        for i, step in enumerate(sequence):
            if i >= len(solution_seq) or step != solution_seq[i]:
                return f"step {i+1} ({step})"
        return "the final steps"

class PuzzleState(State):
    """Complete puzzle state implementation"""
    def __init__(self, context: 'GameContext', puzzle: PuzzleEntity):
        super().__init__(context)
        self.puzzle = puzzle
        
    def enter(self) -> Dict[str, Any]:
        return {
            "message": "You've encountered a puzzle!",
            "description": self.puzzle.description,
            "available_actions": self.get_available_actions()
        }
    
    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "")
        
        if action_type == "solve":
            return self.puzzle.attempt_solution(action.get("solution", {}))
        elif action_type == "interact":
            return self._handle_interaction(action)
        elif action_type == "examine":
            return self._handle_examination()
        elif action_type == "reset":
            return self._handle_reset()
        elif action_type == "abandon":
            self.context.change_state(GameState.EXPLORATION)
            return {"message": "You abandon the puzzle"}
        
        return {"error": "Unknown puzzle action"}
    
    def _handle_interaction(self, action: Dict[str, Any]) -> Dict[str, Any]:
        component_id = action.get("component_id")
        action_type = action.get("action")
        return self.puzzle.interact(component_id, action_type)
    
    def _handle_examination(self) -> Dict[str, Any]:
        return {
            "details": self.puzzle.description,
            "components": list(self.puzzle.components.keys())
        }
    
    def _handle_reset(self) -> Dict[str, Any]:
        self.puzzle.reset()
        return {"message": "Puzzle has been reset"}
    
    def get_available_actions(self) -> List[str]:
        return ["solve", "interact", "examine", "reset", "abandon"]
    
    def exit(self) -> Dict[str, Any]:
        return {"message": "Puzzle interaction ended"}

# ============================================================================
# CORE DATA STRUCTURES
# ============================================================================

@dataclass
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    def get_modifier(self, ability: str) -> int:
        score = getattr(self, ability.lower())
        return (score - 10) // 2
    
    def to_dict(self) -> Dict[str, Dict[str, int]]:
        return {
            ability: {"score": score, "modifier": self.get_modifier(ability)}
            for ability, score in self.__dict__.items()
        }

@dataclass
class Character:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    race: str = ""
    character_class: str = ""
    level: int = 1
    abilities: AbilityScores = field(default_factory=AbilityScores)
    hit_points: Dict[str, int] = field(default_factory=lambda: {"current": 1, "maximum": 1})
    armor_class: int = 10
    proficiency_bonus: int = 2
    skills: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    spells: Dict[str, Any] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    
    def is_alive(self) -> bool:
        return self.hit_points["current"] > 0
    
    def take_damage(self, damage: int) -> int:
        actual_damage = min(damage, self.hit_points["current"])
        self.hit_points["current"] -= actual_damage
        return actual_damage
    
    def heal(self, healing: int) -> int:
        max_healing = self.hit_points["maximum"] - self.hit_points["current"]
        actual_healing = min(healing, max_healing)
        self.hit_points["current"] += actual_healing
        return actual_healing

@dataclass
class GameEnvironment:
    current_location: str = ""
    weather: str = "clear"
    time_of_day: str = "day"
    temperature: str = "comfortable"
    lighting: str = "bright"
    hazards: List[str] = field(default_factory=list)
    npcs_present: List[str] = field(default_factory=list)
    available_actions: List[str] = field(default_factory=list)

@dataclass
class CombatEncounter:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    participants: List[str] = field(default_factory=list)
    initiative_order: List[str] = field(default_factory=list)
    current_turn: int = 0
    round_number: int = 1
    active_effects: Dict[str, Any] = field(default_factory=dict)
    
    def get_current_actor(self) -> str:
        if self.initiative_order:
            return self.initiative_order[self.current_turn % len(self.initiative_order)]
        return ""
    
    def next_turn(self):
        self.current_turn += 1
        if self.current_turn >= len(self.initiative_order):
            self.round_number += 1


# ============================================================================
# MAIN GAME CONTEXT AND CONTROLLER
# ============================================================================

class GameContext:
    """Main game state container and controller"""
    
    def __init__(self, dungeon_generator=None):
        self.characters: Dict[str, Character] = {}
        self.current_state: GameState = GameState.SETUP
        self.state_machine: Dict[GameState, State] = {}
        self.environment: GameEnvironment = GameEnvironment()
        self.combat: Optional[CombatEncounter] = None
        self.dungeon_interface: DungeonInterface = DungeonInterface(dungeon_generator)
        self.session_log: List[Dict[str, Any]] = []
        self.ai_memory: Dict[str, Any] = {}
        
        # Initialize state machines
        self._initialize_states()
    
    def _initialize_states(self):
        """Initialize all state machine states"""
        self.state_machine[GameState.EXPLORATION] = ExplorationState(self)
        self.state_machine[GameState.COMBAT] = CombatState(self)
        # Add other states as needed
    
    def add_character(self, character: Character):
        """Add a character to the game"""
        self.characters[character.id] = character
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """Get a character by ID"""
        return self.characters.get(character_id)
    
    def change_state(self, new_state: GameState) -> Dict[str, Any]:
        """Change game state and handle transitions"""
        if self.current_state in self.state_machine:
            exit_result = self.state_machine[self.current_state].exit()
        
        self.current_state = new_state
        
        if new_state in self.state_machine:
            enter_result = self.state_machine[new_state].enter()
            self._log_state_change(new_state, enter_result)
            return enter_result
        
        return {"error": f"State {new_state} not implemented"}
    
    def process_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process a player action in the current state"""
        if self.current_state not in self.state_machine:
            return {"error": "Current state not implemented"}
        
        result = self.state_machine[self.current_state].execute(action)
        self._log_action(action, result)
        return result
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get complete game state for AI context"""
        return {
            "current_state": self.current_state.name,
            "characters": {cid: self._serialize_character(char) 
                          for cid, char in self.characters.items()},
            "environment": self.environment.__dict__,
            "combat": self.combat.__dict__ if self.combat else None,
            "dungeon_location": self.dungeon_interface.party_location,
            "current_room": self.dungeon_interface.get_current_room(),
            "available_actions": self._get_available_actions(),
            "ai_memory": self.ai_memory
        }
    
    def _serialize_character(self, character: Character) -> Dict[str, Any]:
        return {
            "id": character.id,
            "name": character.name,
            "race": character.race,
            "class": character.character_class,
            "level": character.level,
            "abilities": character.abilities.to_dict(),
            "hit_points": character.hit_points,
            "armor_class": character.armor_class,
            "conditions": character.conditions,
            "position": character.position
        }
    
    def _get_available_actions(self) -> List[str]:
        if self.current_state in self.state_machine:
            return self.state_machine[self.current_state].get_available_actions()
        return []
    
    def _log_action(self, action: Dict[str, Any], result: Dict[str, Any]):
        """Log action and result for AI memory"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "state": self.current_state.name,
            "action": action,
            "result": result
        }
        self.session_log.append(log_entry)
    
    def _log_state_change(self, new_state: GameState, result: Dict[str, Any]):
        """Log state changes"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "state_change",
            "new_state": new_state.name,
            "result": result
        }
        self.session_log.append(log_entry)

# ============================================================================
# ENHANCED GAME CONTEXT WITH ALL COMPONENTS
# ============================================================================

class EnhancedGameContext(GameContext):
    """Extended game context with all advanced components"""
    
    def __init__(self, dungeon_generator=None):
        super().__init__(dungeon_generator)
        self.dungeon_state = None
        self.dungeon_renderer = DungeonRenderer()
        self.npc_manager = NPCManager()
        self.quest_manager = QuestManager()
        self.encounter_generator = EncounterGenerator()
        self.world_state = WorldStateManager()
        self.multimedia_generator = MultimediaGenerator()
        
        # Enhanced AI memory system
        self.narrative_threads: List[Dict[str, Any]] = []
        self.player_preferences: Dict[str, Any] = {}
        self.campaign_themes: List[str] = []
        self._initialize_enhanced_states()
    
    def _initialize_enhanced_states(self):
        """Initialize state machines for enhanced context"""
        self.state_machine[GameState.SOCIAL] = SocialState(self)
        self.state_machine[GameState.REST] = RestState(self)
        #self.state_machine[GameState.PUZZLE] = PuzzleState(self) # AI create dynamically see enter_puzzle_state below

    def enter_puzzle_state(self, puzzle: PuzzleEntity):
        """Create and enter puzzle state with a specific puzzle"""
        self.state_machine[GameState.PUZZLE] = PuzzleState(self, puzzle)
        self.change_state(GameState.PUZZLE)

    def start_puzzle(self, puzzle: PuzzleEntity):
        """Set up the puzzle state and transition to it"""
        # Create puzzle state with the specific puzzle
        self.state_machine[GameState.PUZZLE] = PuzzleState(self, puzzle)
        self.change_state(GameState.PUZZLE)

    def process_enhanced_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced action processing with world consequences"""
        # Process the action normally
        result = self.process_action(action)
        
        # Process world consequences
        consequences = self.world_state.process_action_consequences(action, result)
        
        # Update narrative threads
        self._update_narrative_threads(action, result, consequences)
        
        # Generate multimedia content if needed
        multimedia_content = self._generate_multimedia_for_action(action, result)
        
        # Enhanced result with additional context
        enhanced_result = {
            **result,
            "consequences": consequences,
            "multimedia": multimedia_content,
            "narrative_impact": self._assess_narrative_impact(action, result)
        }
        
        return enhanced_result
    
    def _update_narrative_threads(self, action: Dict[str, Any], 
                                 result: Dict[str, Any], consequences: List[Dict[str, Any]]):
        """Update ongoing narrative threads based on actions"""
        # Track important story developments
        if result.get("story_significant", False):
            thread = {
                "id": str(uuid.uuid4()),
                "type": "story_development",
                "action": action,
                "result": result,
                "consequences": consequences,
                "timestamp": datetime.now().isoformat()
            }
            self.narrative_threads.append(thread)
    
    def _generate_multimedia_for_action(self, action: Dict[str, Any], 
                                       result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate appropriate multimedia content for an action"""
        multimedia = {}
        
        # Generate scene images for significant location changes
        if action.get("type") == "move" and result.get("new_location"):
            scene_context = {
                "location": result["new_location"],
                "characters": list(self.characters.keys()),
                "lighting": self.environment.lighting,
                "mood": "mysterious"  # Could be determined by context
            }
            multimedia["scene_image"] = self.multimedia_generator.generate_scene_image_prompt(scene_context)
        
        # Generate audio cues for atmospheric scenes
        if self.current_state in [GameState.EXPLORATION, GameState.COMBAT]:
            scene_context = {
                "location_type": "dungeon",  # Could be determined from current location
                "activity": self.current_state.name.lower(),
                "time_of_day": self.environment.time_of_day
            }
            multimedia["audio_cues"] = self.multimedia_generator.generate_audio_cues(scene_context)
        
        return multimedia
    
    def _assess_narrative_impact(self, action: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Assess the narrative impact of an action"""
        if result.get("critical_success") or result.get("critical_failure"):
            return "high"
        elif result.get("story_significant"):
            return "medium"
        else:
            return "low"
    
    def generate_dynamic_encounter(self) -> Dict[str, Any]:
        """Generate a contextually appropriate encounter"""
        party_level = max(char.level for char in self.characters.values())
        party_size = len(self.characters)
        
        # Determine encounter type based on current context
        encounter_weights = {
            "combat": 0.4,
            "social": 0.3,
            "puzzle": 0.2,
            "trap": 0.1
        }
        
        encounter_type = random.choices(
            list(encounter_weights.keys()), 
            weights=list(encounter_weights.values())
        )[0]
        
        context = {
            "location": self.environment.current_location,
            "time_of_day": self.environment.time_of_day,
            "party_composition": [char.character_class for char in self.characters.values()],
            "recent_actions": self.session_log[-5:] if len(self.session_log) >= 5 else self.session_log
        }
        
        encounter = self.encounter_generator.generate_encounter(
            encounter_type, party_level, party_size, context
        )
        
        return encounter

    def generate_dungeon(self, **kwargs):
        """Generate dungeon and initialize state"""
        dungeon_data = self.dungeon_interface.generate_dungeon(**kwargs)
        self.dungeon_state = DungeonState(dungeon_data)
        return self.dungeon_state
        
    def get_dungeon_view(self):
        """Get current dungeon view with visibility"""
        visible = self.dungeon_state.get_visible_area()
        return self.dungeon_renderer.render(self.dungeon_state, visible)
        
    def move_party(self, direction):
        """Move party in specified direction"""
        result = self.dungeon_interface.move_party(direction)
        if result['success']:
            # Update all character positions
            for char in self.characters.values():
                char.position = result['new_position']
            self.party_position = result['new_position']
        return result
        
    def add_dungeon_feature(self, position, feature_type, data=None):
        """Add environmental feature to dungeon"""
        if not self.dungeon_state:
            logging.warning("No dungeon state available")
            return
            
        self.dungeon_state.add_feature(position, feature_type, data or {})
        logging.info(f"Added {feature_type} at {position}")
        
    def transform_cell(self, position, new_type):
        """Permanently change cell type at position"""
        if not self.dungeon_state:
            return False
            
        type_map = {
            "wall": DungeonGenerator.WALL,
            "floor": DungeonGenerator.FLOOR,
            "door": DungeonGenerator.DOOR,
            "water": DungeonGenerator.WATER,
            "lava": DungeonGenerator.LAVA
        }
        
        if new_type not in type_map:
            logging.error(f"Invalid cell type: {new_type}")
            return False
            
        return self.dungeon_state.transform_cell(position, type_map[new_type])

    def create_production_game(dungeon_generator=None, ai_config: Dict[str, Any] = None):
        """Create a production-ready game instance with all components"""
        # Initialize enhanced game context
        game = EnhancedGameContext(dungeon_generator)
        
        # Configure AI agent with multimedia capabilities
        ai_config = ai_config or {
            "personality": "helpful_storyteller",
            "creativity_level": 0.8,
            "rule_strictness": 0.7,
            "multimedia_enabled": True
        }
        
        ai_agent = AIAgent(game)
        ai_agent.personality_traits = ai_config
        
        # Set up campaign themes
        game.campaign_themes = ["mystery", "exploration", "heroic_fantasy"]
        
        return game, ai_agent
    
    def integration_example():
        """Example showing how to integrate all components"""
        
        # Create game with your dungeon generator
        # game, ai_agent = create_production_game(your_dungeon_generator)
        game, ai_agent = EnhancedGameContext.create_production_game()
        
        # Create sample party
        party = [
            Character(
                name="Aria",
                race="Elf",
                character_class="Ranger",
                level=5,
                abilities=AbilityScores(dexterity=16, wisdom=14, constitution=13),
                hit_points={"current": 42, "maximum": 42},
                skills=["Survival", "Perception", "Stealth"]
            ),
            Character(
                name="Gareth",
                race="Human", 
                character_class="Paladin",
                level=5,
                abilities=AbilityScores(strength=16, charisma=14, constitution=15),
                hit_points={"current": 48, "maximum": 48},
                skills=["Religion", "Persuasion"]
            )
        ]
        
        for character in party:
            game.add_character(character)
        
        # Generate initial dungeon
        dungeon = game.dungeon_interface.generate_dungeon(
            levels=3,
            difficulty="medium",
            theme="ancient_ruins"
        )
        
        # Create initial NPCs
        tavern_keeper = game.npc_manager.create_npc({
            "name": "Mira Goldbrook",
            "race": "Halfling",
            "class": "Commoner",
            "personality_traits": ["cheerful", "gossipy", "helpful"],
            "goals": ["run_successful_tavern", "help_travelers"],
            "dialogue_style": "friendly",
            "location": "tavern"
        })
        
        # Create initial quest
        quest_id = game.quest_manager.create_quest("explore", {
            "quest_giver": tavern_keeper,
            "location": "ancient_ruins",
            "time_limit": None
        })
        
        # Start the game
        game.change_state(GameState.EXPLORATION)
        
        # Example action sequence
        action_sequence = [
            {
                "type": "social",
                "character_id": party[1].id,  # Paladin talks to NPC
                "target_npc": tavern_keeper,
                "intent": "gather_information"
            },
            {
                "type": "move",
                "direction": "north",
                "character_id": party[0].id  # Ranger leads the way
            },
            {
                "type": "search",
                "character_id": party[0].id,  # Ranger searches
                "skill": "perception",
                "dc": 15
            }
        ]
        
        # Process actions and show results
        for action in action_sequence:
            print(f"\n--- Processing Action: {action['type']} ---")
            result = game.process_enhanced_action(action)
            
            # Show game state
            print(f"Current State: {game.current_state.name}")
            print(f"Action Result: {result.get('message', 'No message')}")
            
            # Show multimedia content if generated
            if result.get('multimedia'):
                multimedia = result['multimedia']
                if 'scene_image' in multimedia:
                    print(f"Scene Image Prompt: {multimedia['scene_image']['main_prompt']}")
                if 'audio_cues' in multimedia:
                    print(f"Audio Cues: {[cue['sound'] for cue in multimedia['audio_cues']]}")
            
            # Show consequences
            if result.get('consequences'):
                print(f"World Consequences: {len(result['consequences'])} changes")
        
        # Generate a dynamic encounter
        encounter = game.generate_dynamic_encounter()
        print(f"\n--- Generated Encounter ---")
        print(f"Type: {encounter['type']}")
        print(f"Difficulty: {encounter['difficulty']}")
        print(f"Components: {len(encounter['components'])} elements")
        
        # Show complete game state for AI context
        complete_state = game.get_game_state()
        print(f"\n--- Game State Summary ---")
        print(f"Characters: {len(complete_state['characters'])}")
        print(f"Active Quests: {len(game.quest_manager.active_quests)}")
        print(f"NPCs: {len(game.npc_manager.npcs)}")
        print(f"World Events: {len(game.world_state.world_events)}")
        
        return game, ai_agent

# ============================================================================
# SAVE/LOAD SYSTEM FOR PERSISTENCE
# ============================================================================

# Add this to AIDMFramework.py

class GamePersistence:
    """Handle saving and loading game state"""
    
    @staticmethod
    def save_game(game: EnhancedGameContext, filename: str) -> bool:
        """Save complete game state to file"""
        try:
            game_data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "characters": {cid: GamePersistence._serialize_character(char) 
                              for cid, char in game.characters.items()},
                "current_state": game.current_state.name,
                "environment": game.environment.__dict__,
                "combat": game.combat.__dict__ if game.combat else None,
                "dungeon_state": game.dungeon_interface.party_location,
                "dungeon_data": GamePersistence._serialize_dungeon(game.dungeon_state),
                "grid": [[cell.__dict__ for cell in row] for row in game.dungeon_state.grid] 
                if game.dungeon_state else [],
                "npcs": game.npc_manager.npcs,
                "quests": {
                    "active": game.quest_manager.active_quests,
                    "completed": game.quest_manager.completed_quests
                },
                "world_state": {
                    "events": game.world_state.world_events,
                    "faction_standings": game.world_state.faction_standings,
                    "economic_state": game.world_state.economic_state,
                    "political_climate": game.world_state.political_climate,
                    "environmental_changes": game.world_state.environmental_changes
                },
                "campaign_data": {
                    "journal": game.campaign_journal,
                    "narrative_threads": game.narrative_threads,
                    "themes": game.campaign_themes
                },
                "ai_state": {
                    "memory": game.ai_memory,
                    "session_log": game.session_log
                }
            }
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(game_data, f, indent=2, default=str)
            return True
            
        except Exception as e:
            logging.error(f"Error saving game: {str(e)}")
            return False

    @staticmethod
    def load_game(filename: str) -> EnhancedGameContext:
        """Load game state from file"""
        try:
            with open(filename, 'r') as f:
                game_data = json.load(f)
                
            # Create new game context
            game = EnhancedGameContext()
            
            # Load characters
            for cid, char_data in game_data["characters"].items():
                character = Character(
                    id=cid,
                    name=char_data["name"],
                    race=char_data["race"],
                    character_class=char_data["class"],
                    level=char_data["level"],
                    abilities=AbilityScores(**char_data["abilities"]),
                    hit_points=char_data["hit_points"],
                    armor_class=char_data["armor_class"],
                    skills=char_data["skills"],
                    equipment=char_data["equipment"],
                    spells=char_data["spells"],
                    conditions=char_data["conditions"],
                    position=char_data["position"]
                )
                game.add_character(character)
                
            # Load game state
            game.current_state = GameState[game_data["current_state"]]
            game.environment = GameEnvironment(**game_data["environment"])
            
            # Load combat state
            if game_data["combat"]:
                game.combat = CombatEncounter(
                    id=game_data["combat"]["id"],
                    participants=game_data["combat"]["participants"],
                    initiative_order=game_data["combat"]["initiative_order"],
                    current_turn=game_data["combat"]["current_turn"],
                    round_number=game_data["combat"]["round_number"],
                    active_effects=game_data["combat"]["active_effects"]
                )
                
            # Load dungeon state
            game.dungeon_interface.party_location = game_data["dungeon_state"]
            if "dungeon_data" in game_data:
                game.dungeon_state = GamePersistence._deserialize_dungeon(
                    game_data["dungeon_data"]
                )
                
            # Load NPCs
            game.npc_manager.npcs = game_data["npcs"]
            
            # Load quests
            game.quest_manager.active_quests = game_data["quests"]["active"]
            game.quest_manager.completed_quests = game_data["quests"]["completed"]
            
            # Load world state
            game.world_state = WorldStateManager()
            game.world_state.world_events = game_data["world_state"]["events"]
            game.world_state.faction_standings = game_data["world_state"]["faction_standings"]
            
            # Load campaign data
            game.campaign_journal = game_data["campaign_data"]["journal"]
            game.narrative_threads = game_data["campaign_data"]["narrative_threads"]
            game.campaign_themes = game_data["campaign_data"]["themes"]
            
            # Load AI state
            game.ai_memory = game_data["ai_state"]["memory"]
            game.session_log = game_data["ai_state"]["session_log"]
            
            return game
            
        except Exception as e:
            logging.error(f"Error loading game: {str(e)}")
            raise

    @staticmethod
    def _serialize_character(character: Character) -> dict:
        """Serialize character data for saving"""
        return {
            "id": character.id,
            "name": character.name,
            "race": character.race,
            "class": character.character_class,
            "level": character.level,
            "abilities": character.abilities.__dict__,
            "hit_points": character.hit_points,
            "armor_class": character.armor_class,
            "skills": character.skills,
            "equipment": character.equipment,
            "spells": character.spells,
            "conditions": character.conditions,
            "position": character.position
        }
    
    @staticmethod
    def _serialize_dungeon(dungeon_state: DungeonState) -> dict:
        """Serialize dungeon grid data"""
        if not dungeon_state:
            return {}
        
        # Properly serialize the grid
        grid = []
        for row in dungeon_state.grid:
            grid_row = []
            for cell in row:
                grid_row.append({
                    'base_type': cell.base_type,
                    'current_type': cell.current_type,
                    'features': cell.features,
                    'objects': cell.objects,
                    'visibility': cell.visibility,
                    'metadata': cell.metadata
                })
            grid.append(grid_row)
            
        return {
            "grid": grid,  # Use the properly serialized grid
            "features": dungeon_state.features,
            "stairs": dungeon_state.stairs,
            "current_level": dungeon_state.current_level,
            "party_position": dungeon_state.party_position,
            "modification_history": dungeon_state.modification_history
        }
    
    @staticmethod
    def _deserialize_dungeon(dungeon_data: dict) -> DungeonState:
        """Reconstruct dungeon state from serialized data"""
        if not dungeon_data or 'grid' not in dungeon_data:
            return None
            
        # Create a mock generator with necessary attributes
        class MockGenerator:
            def __init__(self, cell_grid, stairs):
                self.cell = cell_grid
                self.stairs = stairs
        
        # Recreate the cell grid from saved data
        cell_grid = []
        for row in dungeon_data["grid"]:
            cell_row = []
            for cell_dict in row:
                cell = DungeonCell(cell_dict['base_type'])
                # Set all properties from the saved data
                for key, value in cell_dict.items():
                    setattr(cell, key, value)
                cell_row.append(cell)
            cell_grid.append(cell_row)
        
        # Create mock generator with stairs data
        stairs = dungeon_data.get("stairs", [])
        generator = MockGenerator(cell_grid, stairs)
        
        # Create DungeonState with mock generator
        dungeon = DungeonState(generator)
        
        # Set additional properties
        dungeon.features = dungeon_data.get("features", [])
        dungeon.current_level = dungeon_data.get("current_level", 1)
        dungeon.party_position = dungeon_data.get("party_position", (0, 0))
        dungeon.modification_history = dungeon_data.get("modification_history", [])
        
        return dungeon

# ============================================================================
# CORE SYSTEM PROMPT AND DIRECTIVES
# ============================================================================

DM_CORE_PROMPT = """
You are an AI Dungeon Master for a D&D campaign. Your primary objectives:

NARRATIVE GOALS:
- Create immersive, engaging storylines that respond to player choices
- Maintain consistency in world-building and character interactions
- Balance challenge with fun, ensuring all players feel included
- Adapt the story dynamically based on player actions and dice outcomes

MECHANICAL RESPONSIBILITIES:
- Enforce rules fairly and consistently
- Manage combat encounters with tactical depth
- Track all game state including character stats, inventory, and world changes
- Provide clear descriptions of situations requiring player decisions

CREATIVE DUTIES:
- Generate vivid descriptions of environments, NPCs, and events
- Create compelling dialogue for NPCs with distinct personalities
- Design balanced encounters appropriate to party level and composition
- Improvise content when players take unexpected actions

INTERACTION PRINCIPLES:
- Ask clarifying questions when player intent is unclear
- Provide multiple interaction options without railroading
- Respond to player creativity with flexible rule interpretation
- Maintain game flow while ensuring important details aren't missed

MULTIMEDIA CAPABILITIES:
- Generate visual descriptions suitable for image creation
- Create atmospheric audio cues and sound effect descriptions
- Produce maps, character portraits, and scene illustrations as needed
- Adapt content for different sensory modalities (text, audio, visual)
"""

# ============================================================================
# RULE SYSTEM COMPONENTS
# ============================================================================

class RuleEngine:
    """Handles all D&D rule calculations and validations"""
    
    @staticmethod
    def roll_dice(sides: int, count: int = 1, modifier: int = 0) -> Dict[str, Any]:
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        return {
            "rolls": rolls,
            "modifier": modifier,
            "total": total,
            "natural_20": any(roll == 20 for roll in rolls) if sides == 20 else False,
            "natural_1": any(roll == 1 for roll in rolls) if sides == 20 else False
        }
    
    @staticmethod
    def calculate_ac(character: Character) -> int:
        base_ac = 10 + character.abilities.get_modifier("dexterity")
        # Add armor bonuses, shield bonuses, etc.
        return base_ac
    
    @staticmethod
    def calculate_attack_bonus(character: Character, weapon_type: str = "melee") -> int:
        ability = "strength" if weapon_type == "melee" else "dexterity"
        return character.abilities.get_modifier(ability) + character.proficiency_bonus
    
    @staticmethod
    def resolve_skill_check(character: Character, skill: str, dc: int) -> Dict[str, Any]:
        ability_map = {
            "athletics": "strength",
            "acrobatics": "dexterity",
            "stealth": "dexterity",
            "sleight_of_hand": "dexterity",
            "arcana": "intelligence",
            "history": "intelligence",
            "investigation": "intelligence",
            "nature": "intelligence",
            "religion": "intelligence",
            "animal_handling": "wisdom",
            "insight": "wisdom",
            "medicine": "wisdom",
            "perception": "wisdom",
            "survival": "wisdom",
            "deception": "charisma",
            "intimidation": "charisma",
            "performance": "charisma",
            "persuasion": "charisma"
        }
        
        ability = ability_map.get(skill.lower(), "wisdom")
        modifier = character.abilities.get_modifier(ability)
        if skill.lower() in [s.lower() for s in character.skills]:
            modifier += character.proficiency_bonus
            
        roll_result = RuleEngine.roll_dice(20, 1, modifier)
        success = roll_result["total"] >= dc
        
        return {
            "roll": roll_result,
            "dc": dc,
            "success": success,
            "skill": skill,
            "ability_used": ability
        }

    
    def _roll_initiative(self):
        participants = []
        for char_id in self.context.characters:
            character = self.context.characters[char_id]
            roll = RuleEngine.roll_dice(20, 1, character.abilities.get_modifier("dexterity"))
            participants.append((char_id, roll["total"]))
        
        # Sort by initiative (highest first)
        participants.sort(key=lambda x: x[1], reverse=True)
        self.context.combat.initiative_order = [char_id for char_id, _ in participants]
    
    def _is_current_actor(self, character_id: str) -> bool:
        return character_id == self.context.combat.get_current_actor()
    
    def _handle_attack(self, action: Dict[str, Any]) -> Dict[str, Any]:
        attacker = self.context.get_character(action.get("character_id"))
        target_id = action.get("target_id")
        target = self.context.get_character(target_id)
        
        attack_bonus = RuleEngine.calculate_attack_bonus(attacker)
        attack_roll = RuleEngine.roll_dice(20, 1, attack_bonus)
        
        if attack_roll["total"] >= target.armor_class:
            damage_roll = RuleEngine.roll_dice(8, 1, attacker.abilities.get_modifier("strength"))
            actual_damage = target.take_damage(damage_roll["total"])
            return {
                "hit": True,
                "attack_roll": attack_roll,
                "damage": actual_damage,
                "target_hp": target.hit_points
            }
        else:
            return {
                "hit": False,
                "attack_roll": attack_roll
            }
    
    def _handle_spell(self, action: Dict[str, Any]) -> Dict[str, Any]:
        # Implement spell casting logic
        return {"message": "Spell cast"}
    
    def _handle_combat_movement(self, action: Dict[str, Any]) -> Dict[str, Any]:
        # Handle tactical movement in combat
        return {"message": "Movement completed"}
    
    def _end_turn(self) -> Dict[str, Any]:
        self.context.combat.next_turn()
        return {
            "message": "Turn ended",
            "next_actor": self.context.combat.get_current_actor(),
            "round": self.context.combat.round_number
        }
    
    def _should_end_combat(self) -> bool:
        # Check win/loss conditions
        alive_characters = [c for c in self.context.characters.values() if c.is_alive()]
        return len(alive_characters) <= 1

# ============================================================================
# DUNGEON INTEGRATION INTERFACE
# ============================================================================

class DungeonInterface:
    """Interface for integrating external dungeon generators"""
    
    def __init__(self, dungeon_generator=None):
        self.dungeon_generator = dungeon_generator
        self.current_dungeon = None
        self.party_location = {"level": 0, "room": 0, "x": 0, "y": 0}
    
    def generate_dungeon(self, **kwargs) -> Dict[str, Any]:
        """Generate a new dungeon using the external generator"""
        if self.dungeon_generator:
            self.current_dungeon = self.dungeon_generator.generate(**kwargs)
        else:
            # Fallback simple dungeon
            self.current_dungeon = self._create_simple_dungeon()
        return self.current_dungeon
    
    def move_party(self, direction: str) -> Dict[str, Any]:
        """Handle party movement through the dungeon"""
        if not self.current_dungeon:
            return {"error": "No dungeon loaded"}
        
        # Update party location based on direction
        # This would integrate with your dungeon generator's movement system
        return {
            "success": True,
            "new_location": self.party_location,
            "description": self._get_room_description()
        }
    
    def get_current_room(self) -> Dict[str, Any]:
        """Get current room information"""
        if not self.current_dungeon:
            return {}
        
        # Return current room data from dungeon generator
        return {
            "description": self._get_room_description(),
            "exits": self._get_available_exits(),
            "contents": self._get_room_contents(),
            "npcs": self._get_room_npcs(),
            "hazards": self._get_room_hazards()
        }
    
    def _create_simple_dungeon(self) -> Dict[str, Any]:
        """Fallback simple dungeon structure"""
        return {
            "levels": 1,
            "rooms": [
                {"id": 0, "description": "A stone chamber with flickering torches"},
                {"id": 1, "description": "A narrow corridor stretching into darkness"}
            ]
        }
    
    def _get_room_description(self) -> str:
        return "You are in a dungeon room."
    
    def _get_available_exits(self) -> List[str]:
        return ["north", "south", "east", "west"]
    
    def _get_room_contents(self) -> List[str]:
        return []
    
    def _get_room_npcs(self) -> List[str]:
        return []
    
    def _get_room_hazards(self) -> List[str]:
        return []

# ============================================================================
# Enhanced DM AGENT INTERFACE -- initially added to allow setting the seed
# ============================================================================

class EnhancedDMAgent:
    def set_dungeon_seed(self, seed):
        """Allow AI to control dungeon generation seed"""
        self.game_state.generation_seed = seed
        
    def generate_dungeon_with_current_seed(self, **params):
        """Generate dungeon using the current seed"""
        self.game_state.initialize_dungeon(
            seed=self.game_state.generation_seed,
            **params
        )
        
    def describe_dungeon(self):
        """Generate description using current seed"""
        return f"Dungeon generated with seed {self.game_state.generation_seed}"

# ============================================================================
# AI AGENT INTEGRATION INTERFACE
# ============================================================================

class AIAgent:
    """Interface for AI agent integration with multimedia capabilities"""
    
    def __init__(self, game_context: GameContext):
        self.game_context = game_context
        self.personality_traits = {}
        self.narrative_memory = []
        
    def process_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input from players (text, audio, etc.)"""
        input_type = input_data.get("type", "text")
        content = input_data.get("content", "")
        
        if input_type == "text":
            return self._process_text_input(content)
        elif input_type == "audio":
            return self._process_audio_input(content)
        else:
            return {"error": "Unsupported input type"}
    
    def generate_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI response with multimedia options"""
        game_state = self.game_context.get_game_state()
        
        response = {
            "text": self._generate_text_response(context, game_state),
            "audio_cues": self._generate_audio_cues(context, game_state),
            "visual_prompts": self._generate_visual_prompts(context, game_state),
            "actions_taken": context.get("actions_taken", []),
            "state_changes": context.get("state_changes", [])
        }
        
        return response
    
    def _process_text_input(self, text: str) -> Dict[str, Any]:
        """Parse text input and convert to game actions"""
        # Natural language processing to extract intent and actions
        # This would integrate with your AI's NLP capabilities
        return {
            "parsed_intent": "explore",
            "actions": [{"type": "move", "direction": "north"}],
            "clarifications_needed": []
        }
    
    def _process_audio_input(self, audio_data: Any) -> Dict[str, Any]:
        """Process audio input (speech-to-text, tone analysis)"""
        # Speech recognition and emotional tone analysis
        return {
            "transcribed_text": "I want to search the room",
            "emotional_tone": "excited",
            "confidence": 0.95
        }
    
    def _generate_text_response(self, context: Dict[str, Any], game_state: Dict[str, Any]) -> str:
        """Generate narrative text response"""
        # Use AI language model to generate contextual response
        return "You find yourself in a dimly lit chamber..."
    
    def _generate_audio_cues(self, context: Dict[str, Any], game_state: Dict[str, Any]) -> List[str]:
        """Generate audio cue descriptions"""
        return ["distant_dripping", "echo_footsteps", "torch_crackling"]
    
    def _generate_visual_prompts(self, context: Dict[str, Any], game_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prompts for image/map generation"""
        return [
            {
                "type": "scene",
                "prompt": "Medieval stone dungeon chamber with flickering torches",
                "style": "fantasy_art",
                "mood": "mysterious"
            },
            {
                "type": "map",
                "prompt": "Top-down dungeon room layout with stone walls",
                "style": "tactical_grid"
            }
        ]
        
    def describe_current_area(self, game_context):
        """Generate description of current location"""
        if not game_context.dungeon_state:
            return "You find yourself in an undefined space."
            
        return self._generate_area_description(
            game_context.dungeon_state,
            game_context.dungeon_state.party_position
        )

    def _generate_area_description(self, dungeon_state, position):
        """Generate a rich description of the current dungeon area"""
        if not dungeon_state:
            return "You find yourself in an undefined space."
        
        # Get basic cell information
        x, y = position
        cell = dungeon_state.grid[x][y]
        
        # Base description based on cell type
        cell_types = {
            "room": "a chamber",
            "corridor": "a passageway",
            "wall": "a solid wall",
            "door": "a doorway",
            "water": "a water-filled area",
            "lava": "a lava flow",
            "stairs": "a staircase",
            "arch": "a stone archway",
            "rubble": "a pile of rubble"
        }
        
        # Get cell type name
        cell_type = "room"  # default
        for type_name, type_value in DungeonGenerator.cell_types.items():
            if cell.base_type & type_value:
                cell_type = type_name
                break
        
        description = f"You are standing in {cell_types.get(cell_type, 'an area')}."
        
        # Add room description if available
        room_id = dungeon_state.get_current_room_id(position)
        if room_id and room_id in dungeon_state.rooms:
            room = dungeon_state.rooms[room_id]
            description += f" This is {room.get('name', 'a room')} - {room.get('description', 'with unremarkable features')}."
        
        # Add environmental features
        features = dungeon_state.get_cell_features(position)
        if features:
            feature_descs = []
            for feature in features:
                if feature['type'] == 'torch':
                    feature_descs.append("torches cast flickering shadows")
                elif feature['type'] == 'chest':
                    feature_descs.append("a wooden chest sits in the corner")
                elif feature['type'] == 'fountain':
                    feature_descs.append("a stone fountain trickles water")
                elif feature['type'] == 'altar':
                    feature_descs.append("an ancient altar stands at the center")
                elif feature['type'] == 'trap':
                    feature_descs.append("suspicious markings on the floor suggest traps")
                else:
                    feature_descs.append(feature['type'])
            
            description += " You notice " + ", ".join(feature_descs) + "."
        
        # Add atmospheric details based on dungeon theme
        themes = {
            "cavern": "The air is cool and damp, with the sound of dripping water echoing in the distance.",
            "ruins": "Crumbling stonework and faded carvings speak of ancient civilizations long forgotten.",
            "fortress": "The walls bear the scars of ancient battles, with arrow slits looking out into darkness.",
            "temple": "Faded religious symbols adorn the walls, and the scent of old incense lingers in the air.",
            "labyrinth": "The twisting passages seem to shift and change when you're not looking directly at them."
        }
        
        theme = dungeon_state.theme if hasattr(dungeon_state, 'theme') else "dungeon"
        description += " " + themes.get(theme, "The air is heavy with the weight of ages.")
        
        # Add special conditions
        if dungeon_state.current_level > 3:
            description += " A sense of deep foreboding hangs heavy in the air."
        elif "water" in cell_type:
            description += " The sound of lapping water echoes through the chamber."
        
        return description

# ============================================================================
# ADVANCED COMPONENTS AND EXTENSIONS
# ============================================================================

class NPCManager:
    """Manages NPCs with AI-driven personalities and behaviors"""
    
    def __init__(self):
        self.npcs: Dict[str, Dict[str, Any]] = {}
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_npc(self, npc_data: Dict[str, Any]) -> str:
        """Create a new NPC with AI personality"""
        npc_id = str(uuid.uuid4())
        self.npcs[npc_id] = {
            "id": npc_id,
            "name": npc_data.get("name", "Unknown"),
            "race": npc_data.get("race", "Human"),
            "class": npc_data.get("class", "Commoner"),
            "personality_traits": npc_data.get("personality_traits", []),
            "goals": npc_data.get("goals", []),
            "relationships": npc_data.get("relationships", {}),
            "knowledge": npc_data.get("knowledge", []),
            "current_mood": npc_data.get("mood", "neutral"),
            "location": npc_data.get("location", ""),
            "dialogue_style": npc_data.get("dialogue_style", "formal")
        }
        self.conversation_history[npc_id] = []
        return npc_id
    
    def generate_dialogue(self, npc_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate contextual dialogue for an NPC"""
        npc = self.npcs.get(npc_id)
        if not npc:
            return {"error": "NPC not found"}
        
        return {
            "npc_name": npc["name"],
            "dialogue": self._generate_npc_response(npc, context),
            "emotional_state": npc["current_mood"],
            "voice_description": self._get_voice_description(npc),
            "body_language": self._get_body_language(npc, context)
        }
    
    def _generate_npc_response(self, npc: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate AI-driven NPC response based on personality and context"""
        # This would integrate with your AI's natural language generation
        base_response = f"*{npc['name']} responds in a {npc['dialogue_style']} manner*"
        return base_response
    
    def _get_voice_description(self, npc: Dict[str, Any]) -> str:
        """Generate voice characteristics for audio generation"""
        return f"A {npc.get('race', 'human').lower()} voice, {npc.get('dialogue_style', 'neutral')} tone"
    
    def _get_body_language(self, npc: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate body language description for visual generation"""
        mood = npc.get('current_mood', 'neutral')
        return f"Body language suggests {mood} demeanor"

class QuestManager:
    """Manages dynamic quest generation and tracking"""
    
    def __init__(self):
        self.active_quests: Dict[str, Dict[str, Any]] = {}
        self.completed_quests: List[Dict[str, Any]] = []
        self.quest_templates: List[Dict[str, Any]] = []
    
    def create_quest(self, quest_type: str, context: Dict[str, Any]) -> str:
        """Generate a new quest based on current game context"""
        quest_id = str(uuid.uuid4())
        quest = {
            "id": quest_id,
            "title": self._generate_quest_title(quest_type, context),
            "description": self._generate_quest_description(quest_type, context),
            "type": quest_type,
            "objectives": self._generate_objectives(quest_type, context),
            "rewards": self._generate_rewards(quest_type, context),
            "status": "active",
            "progress": {},
            "time_limit": context.get("time_limit"),
            "quest_giver": context.get("quest_giver"),
            "location": context.get("location")
        }
        self.active_quests[quest_id] = quest
        return quest_id
    
    def update_quest_progress(self, quest_id: str, objective_id: str, progress: Any) -> Dict[str, Any]:
        """Update progress on a quest objective"""
        if quest_id not in self.active_quests:
            return {"error": "Quest not found"}
        
        quest = self.active_quests[quest_id]
        quest["progress"][objective_id] = progress
        
        # Check if quest is complete
        if self._is_quest_complete(quest):
            self._complete_quest(quest_id)
            return {"status": "completed", "quest": quest}
        
        return {"status": "updated", "progress": quest["progress"]}
    
    def _generate_quest_title(self, quest_type: str, context: Dict[str, Any]) -> str:
        templates = {
            "fetch": ["Retrieve the {item}", "Find the Lost {item}", "Recover the {item}"],
            "kill": ["Eliminate the {monster}", "Slay the {monster}", "Hunt the {monster}"],
            "escort": ["Escort {npc} to {location}", "Guide {npc} Safely", "Protect {npc}"],
            "explore": ["Explore the {location}", "Map the {location}", "Investigate {location}"]
        }
        return random.choice(templates.get(quest_type, ["Unknown Quest"]))
    
    def _generate_quest_description(self, quest_type: str, context: Dict[str, Any]) -> str:
        return f"A {quest_type} quest has been generated based on current circumstances."
    
    def _generate_objectives(self, quest_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"id": "obj1", "description": "Complete the main task", "completed": False}]
    
    def _generate_rewards(self, quest_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"experience": 100, "gold": 50, "items": []}
    
    def _is_quest_complete(self, quest: Dict[str, Any]) -> bool:
        objectives = quest.get("objectives", [])
        return all(obj.get("completed", False) for obj in objectives)
    
    def _complete_quest(self, quest_id: str):
        quest = self.active_quests.pop(quest_id)
        quest["status"] = "completed"
        self.completed_quests.append(quest)

class EncounterGenerator:
    """Generates balanced encounters based on party composition and level"""
    
    def __init__(self):
        self.encounter_templates = {
            "combat": self._load_combat_templates(),
            "social": self._load_social_templates(), 
            "puzzle": self._load_puzzle_templates(),
            "trap": self._load_trap_templates()
        }
    
    def generate_encounter(self, encounter_type: str, party_level: int, 
                          party_size: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a balanced encounter"""
        encounter_id = str(uuid.uuid4())
        
        encounter = {
            "id": encounter_id,
            "type": encounter_type,
            "difficulty": self._calculate_difficulty(party_level, party_size),
            "components": self._generate_encounter_components(encounter_type, party_level, context),
            "environment_factors": self._generate_environmental_factors(context),
            "potential_outcomes": self._generate_potential_outcomes(encounter_type),
            "scaling_options": self._generate_scaling_options(party_level)
        }
        
        return encounter
    
    def _calculate_difficulty(self, party_level: int, party_size: int) -> str:
        """Calculate appropriate encounter difficulty"""
        base_difficulty = party_level * party_size
        difficulties = ["trivial", "easy", "medium", "hard", "deadly"]
        return random.choice(difficulties)
    
    def _generate_encounter_components(self, encounter_type: str, 
                                     party_level: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate the actual encounter elements"""
        templates = self.encounter_templates.get(encounter_type, [])
        if not templates:
            return []
        
        template = random.choice(templates)
        return self._customize_template(template, party_level, context)
    
    def _customize_template(self, template: Dict[str, Any], 
                           party_level: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Customize encounter template for current party"""
        return [template]  # Simplified implementation
    
    def _generate_environmental_factors(self, context: Dict[str, Any]) -> List[str]:
        """Generate environmental challenges/advantages"""
        factors = ["low_light", "difficult_terrain", "high_ground", "cover_available"]
        return random.sample(factors, random.randint(1, 3))
    
    def _generate_potential_outcomes(self, encounter_type: str) -> Dict[str, List[str]]:
        """Generate possible encounter outcomes"""
        return {
            "success": ["Complete victory", "Partial success", "Pyrrhic victory"],
            "failure": ["Tactical retreat", "Capture", "Partial failure"],
            "alternative": ["Negotiation", "Stealth bypass", "Creative solution"]
        }
    
    def _generate_scaling_options(self, party_level: int) -> Dict[str, Any]:
        """Generate options to scale encounter difficulty on the fly"""
        return {
            "increase_difficulty": ["Add reinforcements", "Enhance abilities", "Environmental hazard"],
            "decrease_difficulty": ["Remove opponent", "Reduce HP", "Provide advantage"],
            "dynamic_elements": ["Changing terrain", "Time pressure", "Multiple objectives"]
        }
    
    def _load_combat_templates(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Bandit Ambush", "creatures": ["bandit"], "tactics": "ambush"},
            {"name": "Monster Lair", "creatures": ["beast"], "tactics": "territorial"}
        ]
    
    def _load_social_templates(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Diplomatic Meeting", "npcs": ["noble"], "stakes": "alliance"},
            {"name": "Merchant Negotiation", "npcs": ["trader"], "stakes": "commerce"}
        ]
    
    def _load_puzzle_templates(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Ancient Riddle", "type": "riddle", "difficulty": "medium"},
            {"name": "Mechanical Lock", "type": "mechanism", "difficulty": "hard"}
        ]
    
    def _load_trap_templates(self) -> List[Dict[str, Any]]:
        return [
            {"name": "Pressure Plate", "type": "mechanical", "damage": "1d6"},
            {"name": "Magic Ward", "type": "magical", "effect": "alarm"}
        ]

class WorldStateManager:
    """Manages persistent world state and consequences of player actions"""
    
    def __init__(self):
        self.world_events: List[Dict[str, Any]] = []
        self.faction_standings: Dict[str, int] = {}
        self.economic_state: Dict[str, Any] = {}
        self.political_climate: Dict[str, Any] = {}
        self.environmental_changes: Dict[str, Any] = {}
    
    def process_action_consequences(self, action: Dict[str, Any], 
                                  result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process long-term consequences of player actions"""
        consequences = []
        
        action_type = action.get("type", "")
        
        if action_type == "combat" and result.get("success", False):
            consequences.extend(self._process_combat_consequences(action, result))
        elif action_type == "social" and result.get("success", False):
            consequences.extend(self._process_social_consequences(action, result))
        elif action_type == "exploration":
            consequences.extend(self._process_exploration_consequences(action, result))
        
        # Update world state based on consequences
        for consequence in consequences:
            self._apply_world_change(consequence)
        
        return consequences
    
    def _process_combat_consequences(self, action: Dict[str, Any], 
                                   result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process consequences of combat actions"""
        consequences = []
        
        # Enemy faction relations
        enemy_faction = action.get("enemy_faction")
        if enemy_faction:
            consequences.append({
                "type": "faction_standing",
                "faction": enemy_faction,
                "change": -10,
                "reason": "Combat with faction members"
            })
        
        # Witness reactions
        if action.get("witnesses"):
            consequences.append({
                "type": "reputation",
                "location": action.get("location"),
                "change": -5,
                "reason": "Public violence"
            })
        
        return consequences
    
    def _process_social_consequences(self, action: Dict[str, Any], 
                                   result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process consequences of social interactions"""
        consequences = []
        
        # Reputation changes
        if result.get("persuasion_success"):
            consequences.append({
                "type": "reputation",
                "location": action.get("location"),
                "change": 5,
                "reason": "Successful diplomacy"
            })
        
        return consequences
    
    def _process_exploration_consequences(self, action: Dict[str, Any], 
                                        result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process consequences of exploration actions"""
        consequences = []
        
        # Discovery consequences
        if result.get("discovery"):
            consequences.append({
                "type": "world_knowledge",
                "discovery": result["discovery"],
                "location": action.get("location")
            })
        
        return consequences
    
    def _apply_world_change(self, consequence: Dict[str, Any]):
        """Apply a consequence to the world state"""
        consequence_type = consequence.get("type")
        
        if consequence_type == "faction_standing":
            faction = consequence.get("faction")
            change = consequence.get("change", 0)
            self.faction_standings[faction] = self.faction_standings.get(faction, 0) + change
        
        elif consequence_type == "reputation":
            location = consequence.get("location")
            change = consequence.get("change", 0)
            # Update location-specific reputation
        
        # Log the world event
        self.world_events.append({
            "timestamp": datetime.now().isoformat(),
            "consequence": consequence
        })

class MultimediaGenerator:
    """Handles generation of multimedia content for the AI DM"""
    
    def __init__(self):
        self.image_prompts = []
        self.audio_cues = []
        self.scene_descriptions = []
    
    def generate_scene_image_prompt(self, scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed prompt for scene image generation"""
        location = scene_context.get("location", "unknown location")
        lighting = scene_context.get("lighting", "moderate")
        mood = scene_context.get("mood", "neutral")
        characters_present = scene_context.get("characters", [])
        
        prompt = {
            "main_prompt": f"{location} with {lighting} lighting, {mood} atmosphere",
            "style_tags": ["fantasy", "detailed", "atmospheric"],
            "composition": "wide shot" if len(characters_present) > 2 else "medium shot",
            "color_palette": self._determine_color_palette(mood, lighting),
            "technical_specs": {
                "aspect_ratio": "16:9",
                "quality": "high",
                "detail_level": "photorealistic"
            },
            "negative_prompts": ["blurry", "low quality", "distorted"]
        }
        
        return prompt
    
    def generate_character_portrait_prompt(self, character: Character) -> Dict[str, Any]:
        """Generate prompt for character portrait"""
        return {
            "main_prompt": f"{character.race} {character.character_class}, {character.name}",
            "style_tags": ["portrait", "fantasy", "detailed"],
            "description_elements": [
                f"Level {character.level} {character.character_class}",
                f"{character.race} features",
                "Fantasy setting"
            ],
            "technical_specs": {
                "aspect_ratio": "3:4",
                "style": "character_portrait"
            }
        }
    
    def generate_map_prompt(self, dungeon_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate prompt for dungeon map creation"""
        return {
            "main_prompt": "Top-down dungeon map layout",
            "style_tags": ["tactical", "grid", "clear"],
            "elements": [
                "Stone walls",
                "Doorways",
                "Room labels",
                "Grid overlay"
            ],
            "technical_specs": {
                "aspect_ratio": "1:1",
                "style": "tactical_map"
            }
        }
    
    def generate_audio_cues(self, scene_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate audio cue descriptions for sound generation"""
        location_type = scene_context.get("location_type", "indoor")
        activity = scene_context.get("activity", "exploration")
        time_of_day = scene_context.get("time_of_day", "day")
        
        cues = []
        
        # Ambient sounds
        if location_type == "dungeon":
            cues.extend([
                {"type": "ambient", "sound": "distant_dripping", "volume": 0.3, "loop": True},
                {"type": "ambient", "sound": "echo_footsteps", "volume": 0.2, "loop": True}
            ])
        elif location_type == "forest":
            cues.extend([
                {"type": "ambient", "sound": "wind_through_trees", "volume": 0.4, "loop": True},
                {"type": "ambient", "sound": "bird_calls", "volume": 0.3, "loop": True}
            ])
        
        # Activity-specific sounds
        if activity == "combat":
            cues.extend([
                {"type": "action", "sound": "sword_clash", "volume": 0.8, "trigger": "attack"},
                {"type": "action", "sound": "spell_cast", "volume": 0.7, "trigger": "spell"}
            ])
        
        return cues
    
    def _determine_color_palette(self, mood: str, lighting: str) -> List[str]:
        """Determine appropriate color palette for scene"""
        palettes = {
            "mysterious": ["deep_purple", "dark_blue", "shadow_gray"],
            "dangerous": ["blood_red", "warning_orange", "black"],
            "peaceful": ["soft_green", "warm_yellow", "light_blue"],
            "magical": ["violet", "silver", "ethereal_blue"]
        }
        return palettes.get(mood, ["neutral_brown", "stone_gray", "torch_orange"])

# ============================================================================
# EXAMPLE USAGE AND INTEGRATION
# ============================================================================

def create_sample_game():
    """Example of how to set up and use the framework"""
    
    # Initialize game context (with placeholder for your dungeon generator)
    game = GameContext()  # Pass your dungeon_generator here
    
    # Create sample characters
    fighter = Character(
        name="Thorin",
        race="Dwarf",
        character_class="Fighter",
        level=3,
        abilities=AbilityScores(strength=16, dexterity=12, constitution=15),
        hit_points={"current": 28, "maximum": 28},
        armor_class=16,
        skills=["Athletics", "Intimidation"]
    )
    
    wizard = Character(
        name="Elara",
        race="Elf",
        character_class="Wizard",
        level=3,
        abilities=AbilityScores(intelligence=16, dexterity=14, constitution=12),
        hit_points={"current": 18, "maximum": 18},
        armor_class=12,
        skills=["Arcana", "History", "Investigation"]
    )
    
    # Add characters to game
    game.add_character(fighter)
    game.add_character(wizard)
    
    # Initialize AI agent
    ai_agent = AIAgent(game)
    
    # Start exploration
    game.change_state(GameState.EXPLORATION)
    
    return game, ai_agent

if __name__ == "__main__":
    # Example usage
    game, ai_agent = create_sample_game()
    
    # Example action processing
    action = {
        "type": "move",
        "direction": "north",
        "character_id": list(game.characters.keys())[0]
    }
    
    result = game.process_action(action)
    print("Action result:", json.dumps(result, indent=2))
    
    # Get current game state
    state = game.get_game_state()
    print("Game state:", json.dumps(state, indent=2))