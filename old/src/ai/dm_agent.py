# dm_agent.py - Enhanced with AI integration and dungeon manipulation
from agno.models.ollama.tools import OllamaTools
from agno.models.message import Message
from agno.models.response import ModelResponse
from dungeon.state import DungeonState
from dungeon.generator import DungeonGenerator  # Our enhanced dj.py
from src.AIDMFramework import EnhancedGameContext, GameState, PuzzleEntity, Character
from src.game.state import UnifiedGameState
from src.ai.tool_registry import registry
from src.ai.tools import dungeon_tools, npc_tools, item_tools, movement_tools 
import json
import random
from typing import Dict, Any, List, Optional, Tuple
import uuid

class BaseDMAgent:
    async def process_command(self, command: str, player_id: str) -> Dict[str, Any]:
        """Base implementation that should be overridden"""
        return {"error": "Command processing not implemented"}

class EnhancedDMAgent(BaseDMAgent):
    def __init__(self, game_state: UnifiedGameState, game_context: EnhancedGameContext):
        self.game_state = game_state
        self.game_context = game_context
        self.model = OllamaTools(
            id="deepseek-r1:8b", 
            host="http://localhost:11434"
        )
        self.tools = registry.get_tools()
        self.campaign_context = {}
        self.current_npcs = {}
        # Bind tool implementations to agent instance
        self.tool_executor = registry
        # Set context for tool execution
        self.tool_executor.set_context(self)
        print(f"Registered tools: {[tool['function']['name'] for tool in self.tools]}")


    def _define_enhanced_tools(self):
        """Dynamically generate tools from registry"""
        return registry.get_tools()

    def process_tool_call(self, tool_call):
        """Execute a tool call using the registry"""
        import json
        try:
            arguments = json.loads(tool_call.arguments)
            return self.tool_executor.execute(tool_call.name, arguments)
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def handle_trap(self, position):
        """DM decides if trap triggers and its effects"""
        trap = self.game_state.trap_system.traps.get(position)
        if not trap or trap["triggered"]:
            return None
            
        # DM decides outcome based on narrative
        if random.random() < 0.7:  # 70% chance DM triggers it
            trap["triggered"] = True
            return trap["effect"]
        return None
    
    def resolve_combat(self, npc_id):
        """DM-managed combat resolution"""
        npc = self.game_state.npcs.get(npc_id)
        if not npc:
            return "Invalid NPC"
            
        # DM decides outcome based on narrative flow
        outcomes = [
            "You defeat the enemy with ease",
            "A tough battle ensues but you emerge victorious",
            "You barely escape with your life",
            "The enemy surrenders unexpectedly"
        ]
        return random.choice(outcomes)  

    def _get_game_state_context(self, player_id: str = None) -> str:
        """Generate rich context string for the LLM including dungeon state"""
        context = super()._get_game_state_context(player_id)
        context += f"\nDungeon Level: {self.game_state.dungeon_state.current_level}"
        
        if player_id and player_id in self.game_state.characters:
            char = self.game_state.characters[player_id]
            room_id = self.game_state.dungeon_state.get_current_room_id(char.position)
            context += f"\nCurrent Room ID: {room_id}"
            
            # Add environmental features
            features = self.game_state.dungeon_state.get_cell_features(char.position)
            if features:
                context += f"\nRoom Features: {', '.join(f['type'] for f in features)}"
        
        # Add NPC context
        if self.current_npcs:
            context += "\nNearby NPCs: " + ", ".join(
                f"{npc['name']} ({npc['role']})" for npc in self.current_npcs.values()
            )
        
        return context

    def _handle_general_command(self, command: str, character: Character) -> Dict[str, Any]:
        """Handle all other commands"""
        # Generate general response
        prompt = (
            f"Respond to player command: '{command}'\n"
            f"Character: {character.name} ({character.character_class} {character.level})\n"
            "Respond in 1-2 sentences as a game master."
        )
        message = Message(role="user", content=prompt)
        return {"response": self.model.invoke([message])}

    async def _handle_non_puzzle_command(self, command: str, player_id: str) -> Dict[str, Any]:
        """Process non-puzzle commands with AI-driven responses"""
        # Get character and current location
        character = self.game_state.get_character(player_id)
        position = character.position
        location = self.game_state.dungeon_state.get_room_description(position)
        
        # Determine player intent
        intent = self._detect_player_intent(command)
        
        # Handle different intents
        if intent == "exploration":
            return self._handle_exploration(command, location)
        elif intent == "combat":
            return self._handle_combat(command, character)
        elif intent == "dialogue":
            return self._handle_dialogue(command, character)
        elif intent == "rest":
            return self._handle_rest(command, character)
        else:
            return self._handle_general_command(command, character)

    def _handle_exploration(self, command: str, location: str) -> Dict[str, Any]:
        """Handle exploration commands"""
        # Generate response based on location
        prompt = (
            f"Describe what happens when a player attempts: '{command}'\n"
            f"Current location: {location}\n"
            "Respond in 1-2 sentences as a game master."
        )
        # Create proper Message object
        message = Message(role="user", content=prompt)
        return {"response": self.model.invoke([message])}

    def _handle_exploration(self, command: str, location: str) -> Dict[str, Any]:
        """Handle exploration commands"""
        # Generate response based on location
        prompt = (
            f"Describe what happens when a player attempts: '{command}'\n"
            f"Current location: {location}\n"
            "Respond in 1-2 sentences as a game master."
        )
        # Create proper Message object
        message = Message(role="user", content=prompt)
        return {"response": self.model.invoke([message])}
    def _handle_puzzle_command(self, command: str, intent: str, 
                             puzzle: PuzzleEntity, player_id: str) -> Dict[str, Any]:
        """Process puzzle-related commands"""
        # Parse the command into a structured action
        parsed_action = self._parse_puzzle_action(command, puzzle)
        
        if intent == "hint" or (intent == "inspect" and not parsed_action):
            # Generate contextual hint
            hint = self._generate_puzzle_hint(puzzle)
            return {
                "response": hint,
                "hint_level": puzzle.get_hint_level(),
                "puzzle_state": puzzle.state
            }
        
        if parsed_action:
            result = puzzle.execute_action(parsed_action)
            
            # Provide enhanced feedback
            response = self._generate_puzzle_feedback(
                puzzle, parsed_action, result
            )
            
            if result.get("success") and puzzle.state == "solved":
                self.game_state.complete_puzzle(puzzle.id)
                self.game_context.change_state(GameState.EXPLORATION)
            
            return {
                "response": response,
                "puzzle_result": result,
                "puzzle_state": puzzle.state
            }
            
        return {
            "response": "I'm not sure what you're trying to do with this puzzle.",
            "suggestions": puzzle.get_available_actions()
        }

    def _parse_puzzle_action(self, command: str, puzzle: PuzzleEntity) -> Dict:
        command_lower = command.lower()
        
        if "solve" in command_lower or "solution" in command_lower:
            return {"type": "solve", "solution": {"attempt": "default"}}
        elif "gem" in command_lower or "slot" in command_lower:
            return {"type": "interact", "component_id": "gem_slot", "action": "insert"}
        elif "examine" in command_lower or "look" in command_lower:
            return {"type": "examine"}
        elif "reset" in command_lower or "restart" in command_lower:
            return {"type": "reset"}
        elif "hint" in command_lower or "help" in command_lower:
            return {"type": "hint"}
        return {"type": "solve", "solution": {"default": True}}

    def _generate_puzzle_feedback(self, puzzle: PuzzleEntity, 
                                action: Dict, result: Dict) -> str:
        """Generate narrative feedback for puzzle actions"""
        if result.get("success"):
            return f"Success! {puzzle.get_success_message(action)}"
        
        if result.get("partial_success"):
            return (f"Partially correct! {puzzle.get_partial_success_message(action)} "
                    f"{puzzle.get_hint(puzzle.get_hint_level())}")
        
        return (f"Hmm, that didn't work. {puzzle.get_failure_message(action)} "
                f"Maybe try something different?")

    async def process_command(self, command: str, player_id: str) -> Dict[str, Any]:
        # Create serializable context
        context_dict = {
            "player_intent": self._detect_player_intent(command),
            "recent_actions": self.game_state.game_log[-3:],
            "party_status": self.get_party_summary(),
            "dungeon_theme": self._get_current_dungeon_theme()
        }
        
        self.campaign_context = context_dict  # Ensure serializable data
        
        # Prepare AI context
        context = {
            "current_situation": self._get_current_situation_description(),
            "campaign_context": json.dumps(context_dict)  # Now serializable
        }

        # Puzzle detection and handling
        puzzle_intent = self._detect_puzzle_intent(command)
        current_puzzle = self.game_state.active_puzzle
        
        if puzzle_intent:
            if not current_puzzle:
                # Check for puzzle at current position
                position = self.game_state.party_position
                puzzle_data = self.game_state.dungeon_state.get_puzzle_at_position(position)
                
                if puzzle_data:
                    current_puzzle = self.game_state.activate_puzzle(
                        puzzle_data["id"]
                    )
                    self.game_context.start_puzzle(current_puzzle)
            
            if current_puzzle:
                return self._handle_puzzle_command(
                    command, puzzle_intent, current_puzzle, player_id
                )
        
        # Handle non-puzzle commands
        return await self._handle_non_puzzle_command(command, player_id)

    def _detect_puzzle_intent(self, command: str) -> Optional[str]:
        """Detect if player is attempting a puzzle action"""
        puzzle_keywords = {
            "puzzle": ["solve", "puzzle", "riddle", "figure out"],
            "inspect": ["look at", "examine", "study", "inspect"],
            "interact": ["touch", "press", "pull", "turn", "rotate", "move", "use"],
            "solve": ["solution", "answer", "sequence", "order"],
            "hint": ["stuck", "help", "hint", "clue", "what now"]
        }
        
        command_lower = command.lower()
        for intent, keywords in puzzle_keywords.items():
            if any(kw in command_lower for kw in keywords):
                return intent
        return None
    
    def _generate_puzzle_hint(self, puzzle: PuzzleEntity) -> str:
        """Generate intelligent hint based on puzzle state"""
        if not puzzle.attempts:
            return puzzle.get_hint(0)
        
        last_attempt = puzzle.attempts[-1]
        
        # Sequence-based puzzles
        if "sequence" in last_attempt:
            solution = puzzle.solution["data"].get("sequence", [])
            if len(last_attempt["sequence"]) < len(solution):
                return ("You haven't completed the full sequence. "
                        f"Try adding more steps after '{last_attempt['sequence'][-1]}'")
            
            error_index = self._find_sequence_discrepancy(
                last_attempt["sequence"], solution
            )
            if error_index is not None:
                return (f"Step {error_index+1} might be incorrect. "
                        f"You used '{last_attempt['sequence'][error_index]}' "
                        f"but consider alternatives related to {solution[error_index-1]}")
        
        # Component-based puzzles
        if "interaction" in last_attempt:
            component = last_attempt["interaction"].get("component")
            action = last_attempt["interaction"].get("action")
            if component and action:
                return (f"Your action '{action}' on '{component}' was noted. "
                        "Have you tried combining it with other elements?")
        
        return puzzle.get_hint(puzzle.get_hint_level())

    def _find_sequence_discrepancy(self, attempt: list, solution: list) -> int:
        """Find the first point of divergence in sequences"""
        min_length = min(len(attempt), len(solution))
        for i in range(min_length):
            if attempt[i] != solution[i]:
                return i
        return None

    def generate_dungeon_level(self, theme: str, difficulty: str, 
                             special_features: List[str] = []) -> str:
        """Generate a new dungeon level with AI-guided parameters"""
        # Convert difficulty to generator parameters
        difficulty_map = {
            "easy": {"room_min": 3, "room_max": 5, "remove_deadends": 70},
            "medium": {"room_min": 4, "room_max": 7, "remove_deadends": 50},
            "hard": {"room_min": 5, "room_max": 9, "remove_deadends": 30},
            "deadly": {"room_min": 6, "room_max": 10, "remove_deadends": 10}
        }
        
        params = {
            "theme": theme,
            "difficulty": difficulty,
            **difficulty_map.get(difficulty, {})
        }
        
        # Add special features
        if "water" in special_features:
            params["water_level"] = 0.3
        if "traps" in special_features:
            params["trap_density"] = 0.2
        
        # Generate new level
        self.game_state.generate_new_level(**params)
        return f"Generated {theme} dungeon level with {difficulty} difficulty"

    def add_dungeon_feature(self, feature_type: str, feature_data: Dict = None) -> str:
        """Add environmental feature at current party position"""
        position = self.game_state.party_position
        self.game_state.dungeon_state.add_feature(position, feature_type, feature_data or {})
        
        # Get feature description from templates
        feature_desc = FEATURE_TEMPLATES.get(feature_type, {}).get("description", feature_type)
        return f"Added {feature_desc} at position {position}"

    def transform_cell(self, position: Tuple[int, int], new_type: str) -> str:
        """Permanently change cell type"""
        type_map = {
            "arch": DungeonGenerator.ARCH,
            "door": DungeonGenerator.DOOR,
            "rubble": DungeonGenerator.RUBBLE,
            "water": DungeonGenerator.WATER
        }
        
        if new_type.lower() not in type_map:
            return f"Invalid cell type: {new_type}"
        
        self.game_state.dungeon_state.transform_cell(position, type_map[new_type.lower()])
        return f"Transformed cell at {position} to {new_type}"

    def create_npc(self, name: str, role: str, personality: str = "", 
                 goals: List[str] = None, location: Tuple[int, int] = None) -> str:
        """Create a new NPC with AI-generated characteristics"""
        npc_id = str(uuid.uuid4())
        
        # Generate missing attributes with AI
        if not personality:
            personality = self._generate_npc_personality(role)
        if not goals:
            goals = [self._generate_npc_goal(role)]
        
        npc = {
            "id": npc_id,
            "name": name,
            "role": role,
            "personality": personality,
            "goals": goals,
            "location": location or self.game_state.party_position,
            "dialogue": self._generate_initial_dialogue(role, personality)
        }
        
        self.current_npcs[npc_id] = npc
        return f"Created NPC {name} ({role}) with personality: {personality}"

    def generate_quest(self, quest_type: str, difficulty: str, 
                     thematic_elements: List[str] = None) -> str:
        """Generate a new quest with AI-created details"""
        quest_id = str(uuid.uuid4())
        
        # Generate quest details with AI
        title = self._generate_quest_title(quest_type, thematic_elements)
        description = self._generate_quest_description(quest_type, difficulty, thematic_elements)
        objectives = self._generate_quest_objectives(quest_type, difficulty)
        
        quest = {
            "id": quest_id,
            "title": title,
            "type": quest_type,
            "difficulty": difficulty,
            "description": description,
            "objectives": objectives,
            "thematic_elements": thematic_elements or [],
            "status": "active"
        }
        
        self.game_state.active_quests[quest_id] = quest
        return f"Generated new quest: {title}"

    def describe_dungeon(self) -> str:
        """Generate a rich description of the current dungeon area"""
        if not hasattr(self.game_state, 'dungeon_state') or not self.game_state.dungeon_state:
            return "No dungeon has been generated yet."
        
        # Get basic position information
        position = self.game_state.party_position
        x, y = position
        
        # Get cell information
        cell = self.game_state.dungeon_state.grid[x][y]
        
        # Base description based on cell type
        cell_type = "room"  # default

        cell_type_mapping = {
            DungeonGenerator.NOTHING: "nothing",
            DungeonGenerator.BLOCKED: "wall",
            DungeonGenerator.ROOM: "room",
            DungeonGenerator.CORRIDOR: "corridor",
            DungeonGenerator.PERIMETER: "perimeter",
            DungeonGenerator.ENTRANCE: "entrance",
            DungeonGenerator.ARCH: "arch",
            DungeonGenerator.DOOR: "door",
            DungeonGenerator.LOCKED: "locked door",
            DungeonGenerator.TRAPPED: "trapped door",
            DungeonGenerator.SECRET: "secret door",
            DungeonGenerator.PORTC: "portcullis",
            DungeonGenerator.STAIR_DN: "stairs down",
            DungeonGenerator.STAIR_UP: "stairs up"
        }

        for flag, name in cell_type_mapping.items():
            if cell.base_type & flag:
                cell_type = name
                break

        
        # Start with a basic description
        description = f"You are in a {cell_type} at position ({x}, {y})."
        
        # Add room description if available
        room_id = self.game_state.dungeon_state.get_current_room_id(position)
        if room_id and room_id in self.game_state.dungeon_state.rooms:
            room = self.game_state.dungeon_state.rooms[room_id]
            description += f" This area is described as: {room.get('description', 'an unremarkable space')}."
        
        # Add environmental features
        features = self.game_state.dungeon_state.get_cell_features(position)
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
        
        theme = self.game_state.dungeon_theme if hasattr(self.game_state, 'dungeon_theme') else "dungeon"
        description += " " + themes.get(theme, "The air is heavy with the weight of ages.")
        
        return description

    def _get_current_dungeon_theme(self) -> str:
        """Get the current dungeon theme"""
        if hasattr(self.game_state, 'dungeon_state') and self.game_state.dungeon_state:
            return self.game_state.dungeon_state.theme
        return "unknown"

    def _get_current_situation_description(self) -> str:
        """Get description of current situation"""
        if hasattr(self.game_state, 'dungeon_state') and self.game_state.dungeon_state:
            return self.game_state.dungeon_state.get_room_description(
                self.game_state.party_position
            )
        return "Unknown location"

    def get_party_summary(self) -> str:
        """Return a summary of the party's status"""
        if not hasattr(self.game_state, 'characters') or not self.game_state.characters:
            return "No party members"
            
        summary = []
        for char in self.game_state.characters.values():
            char_summary = (
                f"{char.name} ({char.character_class} {char.level}): "
                f"HP {char.hit_points['current']}/{char.hit_points['maximum']}"
            )
            if char.conditions:
                char_summary += f", Conditions: {', '.join(char.conditions)}"
            summary.append(char_summary)
            
        return "\n".join(summary)

    # AI GENERATION HELPERS
    def _generate_npc_personality(self, role: str) -> str:
        """Use AI to generate NPC personality based on role"""
        prompt = f"Generate a brief personality description for a {role} NPC in a fantasy RPG. Focus on key traits."
        message = Message(role="user", content=prompt)
        response = self.model.invoke([message])
        return response.strip()

    def _generate_quest_title(self, quest_type: str, themes: List[str]) -> str:
        """Generate quest title with AI"""
        theme_str = " and ".join(themes) if themes else "adventure"
        prompt = f"Create a compelling quest title for a {quest_type} quest with {theme_str} themes."
        message = Message(role="user", content=prompt)
        response = self.model.invoke([message])
        return response.strip().replace('"', '')
    
    def _detect_player_intent(self, command: str) -> str:
        """Use AI to classify player intent"""
        prompt = (
            "Classify player intent from this command:\n"
            f"Player: {command}\n"
            "Intent options: [exploration, combat, dialogue, puzzle, rest, meta]\n"
            "Respond with just the intent keyword."
        )
        
        # Create a proper Message object instead of passing a string
        message = Message(role="user", content=prompt)
        response = self.model.invoke([message])
        try:
            return response.strip().lower()
        except:
            return "general"