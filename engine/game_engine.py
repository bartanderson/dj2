# game_engine.py

"""
================================================================================
DESIGN DOCUMENTATION / TODO: Unified Command Handling
================================================================================

Goal:
    All player actions (movement, buying, selling, teleporting, resting, etc.)
    must be processed through the GameEngine's phase cycle (INPUT → INTERPRETATION
    → AUTHORITY → MUTATION → CONSEQUENCE → VIEW). This ensures that encounters,
    consequences, and state changes are handled consistently and that no action
    bypasses the engine.

GameEngine – Phase-based command processor.

Current status (2025-04-15):
- Movement commands (n, s, e, w, ne, nw, se, sw, go <dir>) are fully handled.
- Authority phase uses world.move_hex() for validation.
- Mutation phase applies movement and stores new hex.
- Consequence phase generates narration.
- Other commands (buy, sell, teleport, fast travel) are planned for next steps.

Required Changes (TODO list):

1. Refactor WorldController.process_command to route ALL commands through
   self.game_engine.advance(), except perhaps admin/debug commands.

2. Extend GameEngine._execute_interpretation_phase to parse:
   - Movement directions (n, s, e, w, ne, nw, se, sw, go <dir>)
   - Buy/sell commands (e.g., "buy shortsword", "sell dagger")
   - Teleport commands (e.g., "teleport 10 20")
   - Fast travel (e.g., "travel to Adventurer's Respite")
   - Rest command
   - Inventory, status, party commands
   - Any other existing command.

3. Extend _execute_authority_phase to validate each command type:
   - For movement: check passability (water, mountains, etc.) and party assets.
   - For buy/sell: verify shop presence, item existence, gold/stock.
   - For teleport: validate coordinates within world bounds.
   - For rest: check if location is safe (e.g., no enemies nearby).

4. Extend _execute_mutation_phase to apply state changes:
   - Update party position, reveal hexes, advance time.
   - Modify character inventory and gold.
   - Apply healing, condition changes, etc.

5. Extend _execute_consequence_phase to:
   - Generate narration for the action.
   - Check for random encounters after any action (not just movement).
   - If an encounter is triggered, generate it and store in ui_data["encounter"].
   - Optionally, call the AI DM to narrate the encounter immediately.

6. Update frontend (world.js) to handle the unified response format, which now
   always includes "encounter" and "action" fields as needed.

7. Remove all direct command handling from WorldController.process_command
   (keep only the call to game_engine.advance and maybe a fallback for errors).

8. Ensure that the engine respects the current mode (world vs. dungeon) and
   delegates appropriately.

Priority:
    - High: Movement and encounter generation.
    - Medium: Buy/sell and inventory.
    - Low: Teleport and fast travel (can be handled by the engine as special
      "move" actions).

TODO, I think this may be largely taken care  of and am wondering about integrating based on phases.py and when to dod it.

================================================================================
"""

import json
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime

class GamePhase(Enum):
    """Canonical game phases as defined in ENGINE_LOOP.md"""
    INPUT = "input"
    INTERPRETATION = "interpretation"
    AUTHORITY = "authority"
    MUTATION = "mutation"
    CONSEQUENCE = "consequence"
    PERSISTENCE = "persistence"
    VIEW = "view"

class GameContext:
    """Context object passed between phases to maintain isolation"""
    def __init__(self):
        self.phase_data = {
            GamePhase.INPUT: {},
            GamePhase.INTERPRETATION: {},
            GamePhase.AUTHORITY: {},
            GamePhase.MUTATION: {},
            GamePhase.CONSEQUENCE: {},
            GamePhase.PERSISTENCE: {},
            GamePhase.VIEW: {},
        }
        self.errors = []
        self.warnings = []
        
    def set_phase_data(self, phase: GamePhase, key: str, value: Any):
        """Store data for a specific phase"""
        self.phase_data[phase][key] = value
        
    def get_phase_data(self, phase: GamePhase, key: str, default=None):
        """Retrieve data from a specific phase"""
        return self.phase_data[phase].get(key, default)
        
    def clear_phase_data(self, phase: GamePhase):
        """Clear all data for a phase (for isolation)"""
        self.phase_data[phase] = {}
        
    def add_error(self, message: str, phase: GamePhase):
        """Log a phase violation error"""
        self.errors.append({
            "phase": phase,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
    def add_warning(self, message: str, phase: GamePhase):
        """Log a phase warning"""
        self.warnings.append({
            "phase": phase,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

class GameEngine:
    def __init__(self, world_controller):
        # Temporary: wrap existing controller
        self.world = world_controller
        self.current_phase = GamePhase.INPUT
        self.phase_history = []
        
        # Phase violation tracking
        self.violations = []
        
        # Will be populated with phase-specific systems as we extract them
        self.systems = {
            GamePhase.INPUT: None,
            GamePhase.INTERPRETATION: None,
            GamePhase.AUTHORITY: None,
            GamePhase.MUTATION: None,
            GamePhase.CONSEQUENCE: None,
            GamePhase.PERSISTENCE: None,
            GamePhase.VIEW: None,
        }
        
        # Initialize phase delegates from world_controller
        self._initialize_delegates()
        
        # Add mode switching support
        self.current_mode = "world"  # "world" or "dungeon"
        self.mode_delegates = {
            "world": {},
            "dungeon": {}
        }
        self._initialize_mode_delegates()
        
    def _initialize_delegates(self):
        """Temporary initialization of phase delegates from world_controller"""
        # For now, we'll use the world_controller for everything
        # As we extract systems, we'll replace these
        
        # Input phase: Use world_controller's command processing
        self.systems[GamePhase.INPUT] = self.world
        
        # Interpretation phase: Use DMChatHandler for now (will extract)
        if hasattr(self.world, 'dm_chat_handler'):
            self.systems[GamePhase.INTERPRETATION] = self.world.dm_chat_handler
            
        # Authority phase: Use world_controller's validation (will extract to dm_tools)
        self.systems[GamePhase.AUTHORITY] = self.world
        
        # Mutation phase: Use world_controller's state changes
        self.systems[GamePhase.MUTATION] = self.world
        
        # Consequence phase: Use narrative system
        if hasattr(self.world, 'narrative_system'):
            self.systems[GamePhase.CONSEQUENCE] = self.world.narrative_system
            
        # Persistence phase: Use world_controller's save methods
        self.systems[GamePhase.PERSISTENCE] = self.world
        
        # View phase: Use world_controller's get_map_data, etc.
        self.systems[GamePhase.VIEW] = self.world
        
    def _initialize_mode_delegates(self):
        """Initialize mode delegates from current systems"""
        # World delegates are the current systems
        for phase, system in self.systems.items():
            self.mode_delegates["world"][phase] = system
            # Dungeon delegates are None for now
            self.mode_delegates["dungeon"][phase] = None
    
    def set_mode(self, mode: str):
        """Switch between world and dungeon modes"""
        if mode not in ["world", "dungeon"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'world' or 'dungeon'")
        
        if mode == self.current_mode:
            return  # Already in this mode
        
        print(f"GameEngine switching from {self.current_mode} to {mode} mode")
        
        # Save current context if needed
        # (we'll implement context preservation later)
        
        # Switch systems
        for phase in self.systems:
            self.systems[phase] = self.mode_delegates[mode][phase]
        
        self.current_mode = mode
        print(f"[OK] Now in {self.current_mode} mode")
    
    def set_dungeon_delegates(self, dungeon_systems):
        """Set dungeon mode delegates from provided systems"""
        if not dungeon_systems or "systems" not in dungeon_systems:
            print("[FAIL] No dungeon systems provided")
            return False
        
        systems = dungeon_systems["systems"]
        
        print(f"\nSetting dungeon mode delegates:")
        for phase, system in systems.items():
            if phase in self.mode_delegates["dungeon"]:
                self.mode_delegates["dungeon"][phase] = system
                if system:
                    print(f"  [OK] {phase.value}: {type(system).__name__}")
                else:
                    print(f"  [WARN] {phase.value}: None")
        
        # Store dungeon systems for later use
        self.dungeon_systems = dungeon_systems
        
        print(f"[OK] Dungeon mode ready with {len([s for s in systems.values() if s])} phase systems")
        return True
    
    def get_mode_status(self):
        """Get current mode and available delegates"""
        status = {
            "current_mode": self.current_mode,
            "available_modes": ["world", "dungeon"],
            "delegate_status": {}
        }
        
        for mode in self.mode_delegates:
            status["delegate_status"][mode] = {}
            for phase, delegate in self.mode_delegates[mode].items():
                status["delegate_status"][mode][phase.value] = {
                    "has_delegate": delegate is not None,
                    "type": type(delegate).__name__ if delegate else "None"
                }
        
        return status
        
    def advance(self, player_input: Optional[Any] = None, context: Optional[GameContext] = None) -> Dict[str, Any]:
        """
        Execute one full game loop cycle
        
        Args:
            player_input: Raw input from player (could be text, command, etc.)
            context: Optional existing context (for multi-turn operations)
            
        Returns:
            Dictionary with UI data and game state
        """
        if context is None:
            context = GameContext()
            
        # Clear any previous errors/warnings
        context.errors.clear()
        context.warnings.clear()
        
        # 1. INPUT PHASE
        self.current_phase = GamePhase.INPUT
        self.phase_history.append(GamePhase.INPUT)
        input_data = self._execute_input_phase(player_input, context)
        
        # 2. INTERPRETATION PHASE
        self.current_phase = GamePhase.INTERPRETATION
        self.phase_history.append(GamePhase.INTERPRETATION)
        action = self._execute_interpretation_phase(input_data, context)
        print(f"[ADVANCE] interpretation result: {action}")
        
        # 3. AUTHORITY PHASE
        self.current_phase = GamePhase.AUTHORITY
        self.phase_history.append(GamePhase.AUTHORITY)
        ruling = self._execute_authority_phase(action, context)
        
        # 4. STATE MUTATION PHASE
        self.current_phase = GamePhase.MUTATION
        self.phase_history.append(GamePhase.MUTATION)
        mutation_result = self._execute_mutation_phase(ruling, context)
        
        # 5. CONSEQUENCE PHASE
        self.current_phase = GamePhase.CONSEQUENCE
        self.phase_history.append(GamePhase.CONSEQUENCE)
        consequences = self._execute_consequence_phase(mutation_result, context)
        # Capture pending encounter if any
        if hasattr(self, '_pending_encounter') and self._pending_encounter:
            consequences['encounter'] = self._pending_encounter.to_dict()
            del self._pending_encounter
        
        # 6. PERSISTENCE PHASE
        self.current_phase = GamePhase.PERSISTENCE
        self.phase_history.append(GamePhase.PERSISTENCE)
        self._execute_persistence_phase(consequences, context)
        
        # 7. VIEW PROJECTION PHASE
        self.current_phase = GamePhase.VIEW
        self.phase_history.append(GamePhase.VIEW)
        ui_data = self._execute_view_phase(consequences, context)
        
        # Record any violations
        if context.errors:
            self.violations.extend(context.errors)
            
        # Limit phase history
        if len(self.phase_history) > 100:
            self.phase_history = self.phase_history[-100:]
            
        return {
            "ui_data": ui_data,
            "context": context,
            "current_phase": self.current_phase.value,
            "violations": len(context.errors),
            "warnings": len(context.warnings)
        }
        
    def _execute_input_phase(self, player_input: Any, context: GameContext) -> Dict[str, Any]:
        print(f"[INPUT] player_input={player_input}")
        input_system = self.systems[GamePhase.INPUT]
        if input_system and hasattr(input_system, 'execute_input_phase'):
            try:
                return input_system.execute_input_phase(player_input, context)
            except Exception as e:
                context.add_error(f"Input delegate error: {str(e)}", GamePhase.INPUT)

        try:
            context.set_phase_data(GamePhase.INPUT, "raw_input", player_input)
            context.set_phase_data(GamePhase.INPUT, "timestamp", datetime.now().isoformat())
            if player_input is None:
                return {"type": "system_event", "data": {}}
            if isinstance(player_input, str):
                input_dict = {
                    "type": "player_text",
                    "text": player_input,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"[INPUT] returning: {input_dict}")
                return input_dict
            elif isinstance(player_input, dict):
                print(f"[INPUT] returning dict: {player_input}")
                return player_input
            else:
                context.add_warning(f"Unrecognized input type: {type(player_input)}", GamePhase.INPUT)
                return {"type": "unknown", "data": player_input}
        except Exception as e:
            context.add_error(f"Input phase error: {str(e)}", GamePhase.INPUT)
            return {"type": "error", "error": str(e)}
            
    def _execute_interpretation_phase(self, input_data: Dict[str, Any], context: GameContext) -> Dict[str, Any]:
        print(f"[INTERPRET] called with input_data={input_data}")
        interpretation_system = self.systems[GamePhase.INTERPRETATION]
        if interpretation_system and hasattr(interpretation_system, 'execute_interpretation_phase'):
            try:
                return interpretation_system.execute_interpretation_phase(input_data, context)
            except Exception as e:
                context.add_error(f"Interpretation delegate error: {str(e)}", GamePhase.INTERPRETATION)

        try:
            if input_data.get("type") == "system_event":
                return {"intent": "system", "action": "advance_time", "confidence": 1.0}
            if input_data.get("type") == "error":
                return {"intent": "error", "action": "handle_error", "error": input_data.get("error")}
            if input_data.get("type") == "player_text":
                text = input_data.get("text", "").lower().strip()
                print(f"[INTERPRET] raw text: '{text}'")
                if text.startswith("go "):
                    text = text[3:]
                    print(f"[INTERPRET] after removing 'go ': '{text}'")
                direction_map = {
                    'n': 'n', 'north': 'n',
                    'ne': 'ne', 'northeast': 'ne',
                    'se': 'se', 'southeast': 'se',
                    's': 's', 'south': 's',
                    'sw': 'sw', 'southwest': 'sw',
                    'nw': 'nw', 'northwest': 'nw'
                }
                intent = "unknown"
                action = "unknown"
                if text in ['e', 'east']:
                    intent = "move"
                    action = "move_east"
                elif text in ['w', 'west']:
                    intent = "move"
                    action = "move_west"
                elif text in direction_map:
                    intent = "move"
                    action = f"move_{direction_map[text]}"
                elif text in ['look', 'l']:
                    intent = "inspect"
                    action = "look"
                else:
                    print(f"[INTERPRET] no match for '{text}'")
                result = {
                    "intent": intent,
                    "action": action,
                    "target": text,
                    "confidence": 1.0 if intent != "unknown" else 0.5,
                    "raw_text": input_data.get("text", "")
                }
                print(f"[INTERPRET] returning: {result}")
                return result
            return input_data
        except Exception as e:
            context.add_error(f"Interpretation phase error: {str(e)}", GamePhase.INTERPRETATION)
            return {"intent": "error", "action": "handle_error", "error": str(e)}
            
    def _execute_authority_phase(self, action: Dict[str, Any], context: GameContext) -> Dict[str, Any]:
        print(f"[AUTHORITY] action={action}")
        authority_system = self.systems[GamePhase.AUTHORITY]
        if authority_system and hasattr(authority_system, 'execute_authority_phase'):
            try:
                return authority_system.execute_authority_phase(action, context)
            except Exception as e:
                context.add_error(f"Authority delegate error: {str(e)}", GamePhase.AUTHORITY)

        try:
            intent = action.get("intent", "unknown")
            if intent == "error":
                return action
            if intent == "inspect":
                col, row = self.world.campaign_state.party_position
                hex_data = self.world.campaign_state.get_hex(col, row)
                if hex_data:
                    description = f"You are in {hex_data['terrain']}."
                    if hex_data.get('pois'):
                        poi_names = [p['name'] for p in hex_data['pois'] if p.get('discovered')]
                        if poi_names:
                            description += f" You see: {', '.join(poi_names)}."
                    ruling = {
                        "valid": True,
                        "action": "look",
                        "description": description,
                        "dice_rolls": {}
                    }
                else:
                    ruling = {
                        "valid": False,
                        "action": "look",
                        "error": "Cannot determine location.",
                        "dice_rolls": {}
                    }
                context.set_phase_data(GamePhase.AUTHORITY, "ruling", ruling)
                return ruling
            if intent == "move":
                # Extract direction from action string (e.g., "move_n" -> "n")
                action_str = action.get("action", "")
                direction = action_str.replace("move_", "") if action_str.startswith("move_") else action.get("target", "")
                print(f"[AUTHORITY] movement direction={direction}")
                # Convert east/west
                if direction == "east":
                    col, row = self.world.campaign_state.party_position
                    direction = 'ne' if row % 2 == 0 else 'se'
                elif direction == "west":
                    col, row = self.world.campaign_state.party_position
                    direction = 'nw' if row % 2 == 0 else 'sw'
                result = self.world.move_hex(direction)
                print(f"[AUTHORITY] move_hex result={result}")
                if result.get("success"):
                    ruling = {
                        "valid": True,
                        "action": "move",
                        "direction": direction,
                        "result": result,
                        "dice_rolls": {}
                    }
                else:
                    ruling = {
                        "valid": False,
                        "action": "move",
                        "error": result.get("message", "Movement blocked"),
                        "dice_rolls": {}
                    }
                context.set_phase_data(GamePhase.AUTHORITY, "ruling", ruling)
                return ruling
            else:
                # Unknown intent
                ruling = {
                    "valid": False,
                    "action": "error",
                    "error": f"Unknown intent: {intent}",
                    "dice_rolls": {}
                }
                context.set_phase_data(GamePhase.AUTHORITY, "ruling", ruling)
                return ruling
        except Exception as e:
            context.add_error(f"Authority phase error: {str(e)}", GamePhase.AUTHORITY)
            return {"valid": False, "action": "error", "error": str(e)}
            
    def _execute_mutation_phase(self, ruling: Dict[str, Any], context: GameContext) -> Dict[str, Any]:
        """Execute State Mutation Phase: Apply changes to game state"""

        print(f"[MUTATION] ruling action={ruling.get('action')}, valid={ruling.get('valid')}")

        # Get the mutation system for current mode
        mutation_system = self.systems[GamePhase.MUTATION]
        
        # Try to use delegate if available
        if mutation_system and hasattr(mutation_system, 'execute_mutation_phase'):
            try:
                return mutation_system.execute_mutation_phase(ruling, context)
            except Exception as e:
                context.add_error(f"Mutation delegate error: {str(e)}", GamePhase.MUTATION)
        
        # DEFAULT IMPLEMENTATION (original code)
        try:
            if not ruling.get("valid", False):
                # Invalid action, no state mutation
                return {
                    "applied": False,
                    "reason": ruling.get("error", "Invalid action")
                }
            if ruling.get("action") == "look":
                return {"applied": True, "result": ruling}

            if ruling.get("action") == "move":
                result = ruling.get("result")
                if result and result.get("success"):
                    # Add direction to result for consequence phase
                    result['direction'] = ruling.get("direction")
                    context.set_phase_data(GamePhase.MUTATION, "new_hex", result.get("new_hex"))
                    return {"applied": True, "result": result}
                else:
                    return {"applied": False, "reason": ruling.get("error", "Movement failed")}
                
            action = ruling.get("action", "")

            print(f"[MUTATION] ruling action={ruling.get('action')}, valid={ruling.get('valid')}")
            
            # TEMPORARY: Delegate to world_controller
            # This is where we'll need to extract mutation logic
            
            if action == "move":
                target = ruling.get("target", "")
                
                # TODO: Call world_controller.travel_to_location(target)
                # For now, simulate success
                result = {
                    "applied": True,
                    "action": "move",
                    "target": target,
                    "success": True
                }
                
            elif action == "attack":
                # TODO: Apply damage to target
                result = {
                    "applied": True,
                    "action": "attack",
                    "damage": ruling.get("damage", 0),
                    "hit": ruling.get("hit", False),
                    "target_destroyed": ruling.get("damage", 0) > 15  # Example
                }
                
            elif action == "talk":
                # No state mutation for talking (yet)
                result = {
                    "applied": True,
                    "action": "talk",
                    "target": ruling.get("target", ""),
                    "dialogue_initiated": True
                }
                
            else:
                result = {
                    "applied": False,
                    "action": action,
                    "error": "No mutation logic defined"
                }
                
            # Store in context
            context.set_phase_data(GamePhase.MUTATION, "result", result)
            
            return result
            
        except Exception as e:
            context.add_error(f"Mutation phase error: {str(e)}", GamePhase.MUTATION)
            return {
                "applied": False,
                "error": str(e)
            }
            
    def _execute_consequence_phase(self, mutation_result: Dict[str, Any], context: GameContext) -> Dict[str, Any]:
        """Execute Consequence Phase: Generate narration, trigger encounters"""
        print(f"[CONSEQUENCE] mutation_result = {mutation_result}")
        print(f"[CONSEQUENCE] mutation_result applied={mutation_result.get('applied')}")
        # Try delegate if available
        consequence_system = self.systems[GamePhase.CONSEQUENCE]
        if consequence_system and hasattr(consequence_system, 'execute_consequence_phase'):
            try:
                return consequence_system.execute_consequence_phase(mutation_result, context)
            except Exception as e:
                context.add_error(f"Consequence delegate error: {str(e)}", GamePhase.CONSEQUENCE)

        # DEFAULT IMPLEMENTATION
        try:
            if not mutation_result.get("applied", False):
                print("[CONSEQUENCE] not applied")
                return {"narration": "Nothing happened.", "encounters": [], "transitions": []}
            if mutation_result.get("result", {}).get("action") == "look":
                narration = mutation_result["result"].get("description", "You see nothing special.")
                return {
                    "narration": narration,
                    "encounters": [],
                    "transitions": []
                }
            # Check if this was a movement action
            move_result = mutation_result.get("result")
            print(f"[CONSEQUENCE] move_result = {move_result}")
            if move_result and move_result.get("success") and move_result.get("direction"):
                direction = move_result.get("direction")
                new_hex = move_result.get("new_hex")
                narration = f"You move {direction}.\n"
                if new_hex:
                    hex_desc = f"You are in {new_hex.get('terrain', 'unknown terrain')}."
                    pois = new_hex.get('pois', [])
                    discovered_pois = [p['name'] for p in pois if p.get('discovered')]
                    if discovered_pois:
                        hex_desc += f" You see: {', '.join(discovered_pois)}."
                    narration += hex_desc
                else:
                    narration += "You arrive at a new location."
                # --- Encounter chance (1-in-6) ---
                import random
                if random.randint(1, 6) == 1:
                    # Get new party position from context (set in mutation phase)
                    new_hex = context.get_phase_data(GamePhase.MUTATION, "new_hex")
                    if new_hex:
                        col = new_hex.get('grid_x')
                        row = new_hex.get('grid_y')
                        if col is not None and row is not None:
                            # Get region for encounter context
                            region = self.world.get_region_for_hex(col, row)
                            danger_mod = region.danger_level if region else 0
                            # Build context for encounter generator
                            encounter_context = {
                                "point_id": f"move_{col}_{row}",
                                "party_level": self.world.get_party_average_level(),
                                "party_size": self.world.get_party_size(),
                                "region": {
                                    "danger_level": danger_mod,
                                    "terrain": new_hex.get('terrain', 'plains'),
                                    "faction": region.faction_control if region else "contested"
                                },
                                "point_type": "travel"
                            }
                            from world.encounter_generator import generate_encounter
                            encounter = generate_encounter(encounter_context)
                            # Store encounter in ui_data (to be returned later)
                            self._pending_encounter = encounter
            else:
                # Fallback for other actions (attack, talk, etc.)
                action = mutation_result.get("action", "")
                if action == "attack":
                    if mutation_result.get("hit", False):
                        damage = mutation_result.get("damage", 0)
                        if mutation_result.get("target_destroyed", False):
                            narration = f"You strike a mighty blow, destroying your target! ({damage} damage)"
                        else:
                            narration = f"You hit your target for {damage} damage."
                    else:
                        narration = "Your attack misses!"
                elif action == "talk":
                    target = mutation_result.get("target", "someone")
                    narration = f"You begin a conversation with {target}."
                else:
                    narration = "Something happened, but it's hard to describe."
                self._pending_encounter = None

            # Prepare consequences
            consequences = {
                "narration": narration,
                "encounters": [],
                "phase_transitions": []
            }
            if move_result and move_result.get("success"):
                consequences['action'] = 'centerOnParty'

            context.set_phase_data(GamePhase.CONSEQUENCE, "consequences", consequences)
            return consequences

        except Exception as e:
            context.add_error(f"Consequence phase error: {str(e)}", GamePhase.CONSEQUENCE)
            return {
                "narration": f"An error occurred: {str(e)}",
                "encounters": [],
                "transitions": []
            }
            
    def _execute_persistence_phase(self, consequences: Dict[str, Any], context: GameContext):
        """Execute Persistence Phase: Save game state, log events"""
        # Get the persistence system for current mode
        persistence_system = self.systems[GamePhase.PERSISTENCE]
        
        # Try to use delegate if available
        if persistence_system and hasattr(persistence_system, 'execute_persistence_phase'):
            try:
                return persistence_system.execute_persistence_phase(consequences, context)
            except Exception as e:
                context.add_error(f"Persistence delegate error: {str(e)}", GamePhase.PERSISTENCE)
                # Fall through to default
        
        # DEFAULT IMPLEMENTATION (original code)
        try:
            # TEMPORARY: Minimal persistence
            # In the future, delegate to persistence system
            
            # Log the action
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "phase_history": [phase.value for phase in self.phase_history[-5:]],  # Last 5 phases
                "consequences": consequences.get("narration", "Unknown"),
                "violations": len(context.errors)
            }
            
            # Store in context
            context.set_phase_data(GamePhase.PERSISTENCE, "log_entry", log_entry)
            
            # TODO: Actually save to database via world_controller.persistence
            
        except Exception as e:
            context.add_error(f"Persistence phase error: {str(e)}", GamePhase.PERSISTENCE)
            
    def _execute_view_phase(self, consequences: Dict[str, Any], context: GameContext) -> Dict[str, Any]:
        """Execute View Projection Phase: Prepare data for UI"""
        # Get the view system for current mode
        view_system = self.systems[GamePhase.VIEW]
        
        # Try to use delegate if available
        if view_system and hasattr(view_system, 'execute_view_phase'):
            try:
                return view_system.execute_view_phase(consequences, context)
            except Exception as e:
                context.add_error(f"View delegate error: {str(e)}", GamePhase.VIEW)
        
        # DEFAULT IMPLEMENTATION (original code)
        try:
            # TEMPORARY: Delegate to world_controller for view data
            # This is phase-appropriate since world_controller.get_map_data() is view logic
            
            ui_data = {}
            
            # Get map data if available
            if hasattr(self.world, 'get_map_data'):
                try:
                    ui_data["map"] = self.world.get_map_data()
                except Exception as e:
                    context.add_warning(f"Failed to get map data: {str(e)}", GamePhase.VIEW)
                    
            # Get location data if available
            if hasattr(self.world, 'get_current_location_data'):
                try:
                    ui_data["location"] = self.world.get_current_location_data()
                except Exception as e:
                    context.add_warning(f"Failed to get location data: {str(e)}", GamePhase.VIEW)
                    
            # Add narration from consequences
            ui_data["narration"] = consequences.get("narration", "")
            
            # Add encounters if any
            encounters = consequences.get("encounters", [])
            if encounters:
                ui_data["encounters"] = encounters
                
            # Add phase info for debugging
            ui_data["phase_info"] = {
                "current_phase": self.current_phase.value,
                "recent_phases": [phase.value for phase in self.phase_history[-3:]],
                "violations": len(context.errors),
                "warnings": len(context.warnings)
            }

            if consequences.get('encounter'):
                ui_data['encounter'] = consequences['encounter']

            if consequences.get('action'):
                ui_data['action'] = consequences['action']
            
            # Store in context
            context.set_phase_data(GamePhase.VIEW, "ui_data", ui_data)
            
            return ui_data
            
        except Exception as e:
            context.add_error(f"View phase error: {str(e)}", GamePhase.VIEW)
            return {
                "error": str(e),
                "narration": "UI rendering failed."
            }
            
    def get_phase_violations(self) -> Dict[str, Any]:
        """Get all recorded phase violations"""
        return {
            "total_violations": len(self.violations),
            "violations_by_phase": {},
            "recent_violations": self.violations[-10:] if self.violations else []
        }
        
    def register_system(self, phase: GamePhase, system):
        """Register a phase-specific system (for gradual extraction)"""
        if phase in self.systems:
            self.systems[phase] = system
            
    def validate_phase_compliance(self, method_name: str, allowed_phases: list) -> bool:
        """
        Validate that a method is only called during allowed phases
        
        This is a runtime check to enforce phase separation
        """
        if self.current_phase not in allowed_phases:
            self.violations.append({
                "method": method_name,
                "current_phase": self.current_phase,
                "allowed_phases": allowed_phases,
                "timestamp": datetime.now().isoformat()
            })
            return False
        return True