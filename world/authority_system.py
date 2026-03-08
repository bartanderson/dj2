# world/authority_system.py
"""
Authority System - validates and executes game actions
Phase: Authority (validates rules, permissions, dice rolls)
"""
from typing import Dict, Any, Optional, List
import random
from dataclasses import dataclass, field
from world import dnd_data

# FIX: Added fields for dice rolling
@dataclass
class ValidatedAction:
    valid: bool
    message: str
    action_data: Dict[str, Any] = field(default_factory=dict)
    requires_tool: bool = False
    tool_name: Optional[str] = None
    tool_params: Optional[Dict] = None
    needs_roll: bool = False           # New: indicates if a dice roll is required
    roll_spec: Optional[str] = None    # New: e.g., "d20+5"

class AuthoritySystem:
    """Validates game actions before they're executed"""

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self.validation_rules = self._load_validation_rules()
        # FIX: Map action types to tool names (could be generated from registry)
        self.intent_to_tool = {
            "character_creation": "create_character",
            "movement": "move_party",          # example
            "combat": "combat_action",         # example
            "inventory": "inventory_action",   # example
        }

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for different action types"""
        return {
            "character_creation": self._validate_character_creation,
            "movement": self._validate_movement,
            "combat": self._validate_combat,
            "interaction": self._validate_interaction,
            "inventory": self._validate_inventory
        }

    # FIX: Unify return type – now returns ValidatedAction
    def validate_action(self, intent: Dict[str, Any], context: Dict[str, Any]) -> ValidatedAction:
        """
        Validate if an action is legal given current game state.
        Returns a ValidatedAction object.
        """
        action_type = intent.get("intent", "unknown")
        validator = self.validation_rules.get(action_type)
        if validator:
            result_dict = validator(intent, context)
        else:
            result_dict = self._validate_generic_action(intent, context)

        # Convert dict result to ValidatedAction
        validated = ValidatedAction(
            valid=result_dict.get("valid", False),
            message=result_dict.get("message", ""),
            action_data=result_dict.get("action_data", {}),
            requires_tool=False,   # will be set by validate_and_prepare_action
        )
        return validated

    def validate_creation_action(self, action: Dict, context: Dict) -> ValidatedAction:
        """Public entry point for creation action validation."""
        return self._validate_creation_action(action, context)

    def _validate_creation_action(self, action: Dict, context: Dict) -> ValidatedAction:
        """Validate character‑creation actions."""
        action_type = action.get("action")
        params = action.get("parameters", {})

        # Allowed fields that can be set during creation
        ALLOWED_FIELDS = {
            "name", "race", "subrace", "class", "background", "personality", 
            "fears", "motivations", "skills", "alignment",
            "ability_scores",      # e.g., {"strength": 15, "dexterity": 14, ...}
            "traits",              # list of trait names (e.g., ["Darkvision", "Fey Ancestry"])
            "proficiencies",       # list of skill/tool proficiencies
            "cantrips",            # list of cantrip names
            "spells_known"         # list of spell names (for known spells)
        }

        if action_type == "update_character_attribute":
            field = params.get("field")
            value = params.get("value")
            # ... basic checks ...
            if field not in ALLOWED_FIELDS:
                return ValidatedAction(valid=False, message=f"Field '{field}' cannot be set during creation")
            
            # Field‑specific validation
            if field == "race":
                from world import dnd_data
                if not dnd_data.validate_race(value):
                    return ValidatedAction(valid=False, message=f"'{value}' is not a valid race")
            elif field == "class":
                from world import dnd_data
                if not dnd_data.validate_class(value):
                    return ValidatedAction(valid=False, message=f"'{value}' is not a valid class")
            elif field == "skills":
                from world import dnd_data
                if not dnd_data.validate_skill(value):
                    return ValidatedAction(valid=False, message=f"'{value}' is not a valid skill")
            elif field == "ability_scores":
                # value should be a dict of ability -> score; you could validate each ability name
                if not isinstance(value, dict):
                    return ValidatedAction(valid=False, message="Ability scores must be a dictionary")
                for ability, score in value.items():
                    if not dnd_data.validate_ability_score(ability):
                        return ValidatedAction(valid=False, message=f"'{ability}' is not a valid ability")
                    if not isinstance(score, int) or score < 1 or score > 30:
                        return ValidatedAction(valid=False, message=f"Invalid score for {ability}")
            elif field == "traits":
                if not isinstance(value, list):
                    return ValidatedAction(valid=False, message="Traits must be a list")
                for trait in value:
                    if not dnd_data.validate_trait(trait):
                        return ValidatedAction(valid=False, message=f"'{trait}' is not a valid trait")
            elif field == "proficiencies":
                if not isinstance(value, list):
                    return ValidatedAction(valid=False, message="Proficiencies must be a list")
                for prof in value:
                    if not dnd_data.validate_proficiency(prof):
                        return ValidatedAction(valid=False, message=f"'{prof}' is not a valid proficiency")

            return ValidatedAction(valid=True, message="OK", action_data=params)

        elif action_type == "confirm_class":
            confirmed_class = params.get("confirmed_class")
            if not confirmed_class:
                return ValidatedAction(valid=False, message="No class specified")
            if not dnd_data.validate_class(confirmed_class):
                return ValidatedAction(valid=False, message=f"'{confirmed_class}' is not a valid class")
            return ValidatedAction(valid=True, message="OK", action_data=params)

        elif action_type == "create_character":
            char_data = params.get("character_data", {})
            required = ["name", "race", "class"]
            missing = [f for f in required if not char_data.get(f)]
            if missing:
                return ValidatedAction(valid=False, message=f"Missing required fields: {', '.join(missing)}")
            # Optional: validate that race/class are valid
            return ValidatedAction(valid=True, message="OK", action_data=params)

        else:
            return ValidatedAction(valid=False, message=f"Unknown creation action: {action_type}")

    def validate_and_prepare_action(self, intent: Dict[str, Any], context: Dict[str, Any]) -> ValidatedAction:
        """
        Validate action and prepare data for execution, including tool mapping and roll indication.
        """
        # First get basic validation
        validated = self.validate_action(intent, context)

        if not validated.valid:
            return validated

        # Determine if a tool is needed
        action_type = intent.get("intent")
        tool_name = self.intent_to_tool.get(action_type)
        if tool_name and self.tool_registry.has_tool(tool_name):
            validated.requires_tool = True
            validated.tool_name = tool_name
            # Build tool parameters from intent and context
            validated.tool_params = self._build_tool_params(intent, context, tool_name)

        # Determine if a dice roll is needed (example logic – expand as needed)
        if self._requires_roll(action_type, intent, context):
            validated.needs_roll = True
            validated.roll_spec = self._get_roll_spec(action_type, intent, context)

        return validated

    def _build_tool_params(self, intent: Dict, context: Dict, tool_name: str) -> Dict:
        """Construct parameters for the tool from intent and context."""
        params = intent.get("parameters", {}).copy()
        # Add common context fields
        params["player_id"] = context.get("player_id")
        params["session_id"] = context.get("session_id")
        params["character_id"] = context.get("character_id")
        return params

    def _requires_roll(self, action_type: str, intent: Dict, context: Dict) -> bool:
        """Determine if the action requires a dice roll."""
        # Example: always roll for combat, never for character creation
        if action_type == "combat":
            return True
        # Could check difficulty in intent
        difficulty = intent.get("parameters", {}).get("difficulty")
        return difficulty is not None

    def _get_roll_spec(self, action_type: str, intent: Dict, context: Dict) -> str:
        """Return dice specification (e.g., 'd20+5') based on action."""
        # Default to a d20 with relevant modifier
        modifier = context.get("ability_modifier", 0)
        return f"d20+{modifier}"

    # Internal validators remain returning dict (for backward compatibility within class)
    def _validate_character_creation(self, intent: Dict, context: Dict) -> Dict:
        """Validate character creation choices"""
        char_data = intent.get("parameters", {}).get("character_data", {})

        if not char_data.get("name"):
            return {"valid": False, "message": "Character needs a name"}

        if not char_data.get("race"):
            return {"valid": False, "message": "Please choose a race"}

        if not char_data.get("class"):
            return {"valid": False, "message": "Please choose a class"}

        # Verify class exists in dnd_data
        if not dnd_data.validate_class(char_data.get("class")):
            return {"valid": False, "message": f"Invalid class: {char_data.get('class')}"}

        # Verify race exists in dnd_data
        if not dnd_data.validate_race(char_data.get("race")):
            return {"valid": False, "message": f"Invalid race: {char_data.get('race')}"}

        return {"valid": True, "message": "Character creation valid", "action_data": char_data}

    def _validate_movement(self, intent: Dict, context: Dict) -> Dict:
        """Validate movement actions"""
        character_state = context.get("character_state", {})

        if character_state.get("incapacitated"):
            return {"valid": False, "message": "Cannot move while incapacitated"}

        if character_state.get("grappled"):
            return {"valid": False, "message": "Cannot move while grappled"}

        destination = intent.get("parameters", {}).get("destination")
        if not destination:
            return {"valid": False, "message": "No destination specified"}

        # FIX: Check if destination exists and is reachable (requires world state in context)
        world_map = context.get("world_map")
        if world_map and not world_map.is_reachable(destination):
            return {"valid": False, "message": "Destination is not reachable"}

        return {"valid": True, "message": "Movement valid", "action_data": intent.get("parameters")}

    def _validate_combat(self, intent: Dict, context: Dict) -> Dict:
        """Validate combat actions"""
        if not context.get("in_combat"):
            return {"valid": False, "message": "Not in combat"}

        target = intent.get("parameters", {}).get("target")
        if not target:
            return {"valid": False, "message": "No target specified"}

        # FIX: Check if target is valid (exists, in range, etc.)
        combat_state = context.get("combat_state")
        if combat_state and not combat_state.is_valid_target(target):
            return {"valid": False, "message": "Invalid target"}

        return {"valid": True, "message": "Combat action valid", "action_data": intent.get("parameters")}

    def _validate_interaction(self, intent: Dict, context: Dict) -> Dict:
        """Validate NPC/object interactions"""
        target = intent.get("parameters", {}).get("target")

        if not target:
            return {"valid": False, "message": "No target specified for interaction"}

        # FIX: Check if target exists and is interactable
        world_state = context.get("world_state")
        if world_state and not world_state.is_interactable(target):
            return {"valid": False, "message": f"{target} is not interactable"}

        return {"valid": True, "message": "Interaction valid", "action_data": intent.get("parameters")}

    def _validate_inventory(self, intent: Dict, context: Dict) -> Dict:
        """Validate inventory actions"""
        action = intent.get("parameters", {}).get("action")
        item = intent.get("parameters", {}).get("item")

        if action in ["use", "equip"] and not item:
            return {"valid": False, "message": "No item specified"}

        if action == "drop" and not item:
            return {"valid": False, "message": "No item to drop"}

        # Check if player has the item
        inventory = context.get("inventory", [])
        if item and item not in inventory:
            return {"valid": False, "message": f"You don't have {item}"}

        return {"valid": True, "message": "Inventory action valid", "action_data": intent.get("parameters")}

    def _validate_generic_action(self, intent: Dict, context: Dict) -> Dict:
        """Default validation for unknown action types"""
        # FIX: Require at least a non-empty parameters dict
        params = intent.get("parameters")
        if params and isinstance(params, dict) and len(params) > 0:
            return {"valid": True, "message": "Action appears valid", "action_data": params}
        return {"valid": False, "message": "Action lacks details"}

    def roll_dice(self, dice_string: str, context: Dict = None) -> Dict[str, Any]:
        """
        Roll dice with authority
        Format: "2d6+3" or "d20"
        """
        try:
            if "d" not in dice_string:
                return {"total": 0, "rolls": [], "error": "Invalid dice format"}

            # Simple dice roller – for complex expressions, consider a library
            parts = dice_string.split("d")
            if len(parts) != 2:
                return {"total": 0, "rolls": [], "error": "Invalid dice format"}

            num_dice = int(parts[0]) if parts[0] else 1
            die_sides = int(parts[1])

            rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
            total = sum(rolls)

            # Apply bonuses/penalties from context
            context = context or {}
            advantage = context.get("advantage", False)
            disadvantage = context.get("disadvantage", False)

            if advantage and disadvantage:
                # Cancel out - normal roll
                pass
            elif advantage:
                extra_rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
                rolls = [max(rolls[i], extra_rolls[i]) for i in range(num_dice)]
                total = sum(rolls)
            elif disadvantage:
                extra_rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
                rolls = [min(rolls[i], extra_rolls[i]) for i in range(num_dice)]
                total = sum(rolls)

            # FIX: Apply bonuses from context
            bonus = context.get("bonus", 0)
            total += bonus

            return {
                "total": total,
                "rolls": rolls,
                "dice_string": dice_string,
                "advantage": advantage,
                "disadvantage": disadvantage,
                "bonus": bonus
            }

        except Exception as e:
            return {"total": 0, "rolls": [], "error": f"Error rolling dice: {str(e)}"}

    def execute_tool(self, tool_name: str, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """
        Execute a tool through the registry with validation.
        Returns a dict with at least "success", "message", and optionally "action_data".
        """
        # Validate tool execution (existence and basic parameter checks)
        validation_result = self.validate_tool_execution(tool_name, parameters, context)

        if not validation_result.get("valid"):
            return {
                "success": False,
                "message": validation_result.get("message", "Tool execution failed validation"),
                "action_data": parameters,
            }

        try:
            tool_result = self.tool_registry.execute_tool(tool_name, parameters)
            # Ensure result has expected keys
            if "success" not in tool_result:
                tool_result["success"] = True
            if "message" not in tool_result:
                tool_result["message"] = f"Executed {tool_name}"
            tool_result["action_data"] = parameters
            return tool_result
        except Exception as e:
            return {
                "success": False,
                "message": f"Tool execution error: {str(e)}",
                "action_data": parameters
            }

    def validate_tool_execution(self, tool_name: str, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """Validate if a tool can be executed (tool‑specific checks)."""
        if not self.tool_registry.has_tool(tool_name):
            return {"valid": False, "message": f"Unknown tool: {tool_name}"}

        # Tool‑specific validation
        if tool_name == "create_door":
            return self._validate_create_door(parameters, context)
        elif tool_name == "move_party":
            return self._validate_move_party(parameters, context)
        elif tool_name == "add_entity":
            return self._validate_add_entity(parameters, context)
        # Add more tool validations as needed

        return {"valid": True, "message": "Tool execution valid"}

    def _validate_create_door(self, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """Validate door creation parameters"""
        x = parameters.get("x")
        y = parameters.get("y")

        if x is None or y is None:
            return {"valid": False, "message": "Missing coordinates for door"}

        if not isinstance(x, int) or not isinstance(y, int):
            return {"valid": False, "message": "Coordinates must be integers"}

        # Check if position is valid in dungeon
        dungeon_state = context.get("dungeon_state")
        if dungeon_state and not dungeon_state.is_valid_position(x, y):
            return {"valid": False, "message": "Invalid door position"}

        return {"valid": True, "message": "Door creation valid"}

    def _validate_move_party(self, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """Validate party movement"""
        direction = parameters.get("direction")
        steps = parameters.get("steps", 1)

        if not direction:
            return {"valid": False, "message": "No direction specified"}

        valid_directions = ["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"]
        if direction.lower() not in valid_directions:
            return {"valid": False, "message": f"Invalid direction: {direction}"}

        if not isinstance(steps, int) or steps < 1:
            return {"valid": False, "message": "Steps must be positive integer"}

        # Check movement cost (if needed)
        movement_cost = parameters.get("movement_cost", 1)
        if movement_cost > context.get("remaining_movement", 100):
            return {"valid": False, "message": "Not enough movement points"}

        return {"valid": True, "message": "Movement valid"}

    def _validate_add_entity(self, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """Validate entity addition"""
        entity_type = parameters.get("entity_type")

        if not entity_type:
            return {"valid": False, "message": "No entity type specified"}

        valid_entities = ["npc", "monster", "item", "trap", "portal", "chest"]
        if entity_type.lower() not in valid_entities:
            return {"valid": False, "message": f"Invalid entity type: {entity_type}"}

        # Additional checks (e.g., unique names, limits) can be added here

        return {"valid": True, "message": "Entity addition valid"}