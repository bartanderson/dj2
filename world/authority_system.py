# world/authority_system.py
"""
Authority System - validates and executes game actions
Phase: Authority (validates rules, permissions, dice rolls)
"""
from typing import Dict, Any, Optional, List
import json
import random

class AuthoritySystem:
    """Validates game actions before they're executed"""
    
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self.validation_rules = self._load_validation_rules()
        
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for different action types"""
        return {
            "character_creation": self._validate_character_creation,
            "movement": self._validate_movement,
            "combat": self._validate_combat,
            "interaction": self._validate_interaction,
            "inventory": self._validate_inventory
        }
    
    def validate_action(self, intent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if an action is legal given current game state
        Returns: {"valid": bool, "message": str, "action_data": Dict}
        """
        action_type = intent.get("intent", "unknown")
        
        # Check if we have validation for this action type
        validator = self.validation_rules.get(action_type)
        if validator:
            return validator(intent, context)
        
        # Default validation for unknown actions
        return self._validate_generic_action(intent, context)
    
    def _validate_character_creation(self, intent: Dict, context: Dict) -> Dict:
        """Validate character creation choices"""
        # Basic validation - could be expanded with campaign rules
        char_data = intent.get("parameters", {}).get("character_data", {})
        
        if not char_data.get("name"):
            return {"valid": False, "message": "Character needs a name"}
        
        if not char_data.get("race"):
            return {"valid": False, "message": "Please choose a race"}
        
        if not char_data.get("class"):
            return {"valid": False, "message": "Please choose a class"}
        
        return {"valid": True, "message": "Character creation valid", "action_data": char_data}
    
    def _validate_movement(self, intent: Dict, context: Dict) -> Dict:
        """Validate movement actions"""
        # Check if player can move (not incapacitated, etc.)
        character_state = context.get("character_state", {})
        
        if character_state.get("incapacitated"):
            return {"valid": False, "message": "Cannot move while incapacitated"}
        
        if character_state.get("grappled"):
            return {"valid": False, "message": "Cannot move while grappled"}
        
        # Check destination validity
        destination = intent.get("parameters", {}).get("destination")
        if not destination:
            return {"valid": False, "message": "No destination specified"}
        
        # Additional checks would go here (terrain, permissions, etc.)
        
        return {"valid": True, "message": "Movement valid", "action_data": intent.get("parameters")}
    
    def _validate_combat(self, intent: Dict, context: Dict) -> Dict:
        """Validate combat actions"""
        # Check if combat is allowed
        if not context.get("in_combat"):
            return {"valid": False, "message": "Not in combat"}
        
        # Check action-specific rules
        action = intent.get("parameters", {}).get("action")
        target = intent.get("parameters", {}).get("target")
        
        if not target:
            return {"valid": False, "message": "No target specified"}
        
        # Check range, line of sight, etc. (simplified)
        return {"valid": True, "message": "Combat action valid"}
    
    def _validate_interaction(self, intent: Dict, context: Dict) -> Dict:
        """Validate NPC/object interactions"""
        target = intent.get("parameters", {}).get("target")
        
        if not target:
            return {"valid": False, "message": "No target specified for interaction"}
        
        # Check if target exists and is interactable
        # This would check against world state
        
        return {"valid": True, "message": "Interaction valid"}
    
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
        
        return {"valid": True, "message": "Inventory action valid"}
    
    def _validate_generic_action(self, intent: Dict, context: Dict) -> Dict:
        """Default validation for unknown action types"""
        # For now, allow most actions if they have parameters
        if intent.get("parameters"):
            return {"valid": True, "message": "Action appears valid", "action_data": intent.get("parameters")}
        return {"valid": False, "message": "Action lacks details"}
    
    def roll_dice(self, dice_string: str, context: Dict = None) -> Dict[str, Any]:
        """
        Roll dice with authority
        Format: "2d6+3" or "d20"
        """
        try:
            # Parse dice string
            if "d" not in dice_string:
                return {"total": 0, "rolls": [], "error": "Invalid dice format"}
            
            # Simple dice roller - would need expansion for complex expressions
            parts = dice_string.split("d")
            if len(parts) != 2:
                return {"total": 0, "rolls": [], "error": "Invalid dice format"}
            
            num_dice = int(parts[0]) if parts[0] else 1
            die_sides = int(parts[1])
            
            rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Apply bonuses/penalties from context
            bonuses = context.get("bonuses", {}) if context else {}
            advantage = context.get("advantage", False)
            disadvantage = context.get("disadvantage", False)
            
            if advantage and disadvantage:
                # Cancel out - normal roll
                pass
            elif advantage:
                # Roll twice, take highest
                extra_rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
                rolls = [max(rolls[i], extra_rolls[i]) for i in range(num_dice)]
                total = sum(rolls)
            elif disadvantage:
                # Roll twice, take lowest
                extra_rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
                rolls = [min(rolls[i], extra_rolls[i]) for i in range(num_dice)]
                total = sum(rolls)
            
            return {
                "total": total,
                "rolls": rolls,
                "dice_string": dice_string,
                "advantage": advantage,
                "disadvantage": disadvantage
            }
            
        except Exception as e:
            return {"total": 0, "rolls": [], "error": f"Error rolling dice: {str(e)}"}
    
    def execute_tool(self, tool_name: str, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """
        Execute a tool through the registry with validation
        Phase: Authority (validates) -> returns result for Mutation phase
        """
        # First validate the tool execution
        validation_result = self.validate_tool_execution(tool_name, parameters, context)
        
        if not validation_result.get("valid"):
            return {
                "success": False,
                "message": validation_result.get("message", "Tool execution failed validation"),
                "action_data": parameters,
                "needs_roll": False
            }
        
        # Execute the tool (this should only return what needs to happen, not mutate state)
        try:
            tool_result = self.tool_registry.execute_tool(tool_name, parameters)
            tool_result["validated"] = True
            tool_result["action_data"] = parameters
            return tool_result
        except Exception as e:
            return {
                "success": False,
                "message": f"Tool execution error: {str(e)}",
                "action_data": parameters
            }
    
    def validate_tool_execution(self, tool_name: str, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """Validate if a tool can be executed"""
        # Check if tool exists
        if not self.tool_registry.has_tool(tool_name):
            return {"valid": False, "message": f"Unknown tool: {tool_name}"}
        
        # Tool-specific validation
        if tool_name == "create_door":
            return self._validate_create_door(parameters, context)
        elif tool_name == "move_party":
            return self._validate_move_party(parameters, context)
        elif tool_name == "add_entity":
            return self._validate_add_entity(parameters, context)
        # Add more tool validations as needed
        
        # Default validation passes
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
        if dungeon_state:
            # Would check if coordinates are within bounds, not blocked, etc.
            pass
            
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
        
        return {"valid": True, "message": "Movement valid"}
    
    def _validate_add_entity(self, parameters: Dict, context: Dict) -> Dict[str, Any]:
        """Validate entity addition"""
        entity_type = parameters.get("entity_type")
        
        if not entity_type:
            return {"valid": False, "message": "No entity type specified"}
        
        valid_entities = ["npc", "monster", "item", "trap", "portal", "chest"]
        if entity_type.lower() not in valid_entities:
            return {"valid": False, "message": f"Invalid entity type: {entity_type}"}
        
        return {"valid": True, "message": "Entity addition valid"}