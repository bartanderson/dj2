# src/ai/tools/movement_tools.py
from src.ai.tool_registry import registry
@registry.register(
    name="move_party",
    description="Move adventuring party through dungeon",
    parameters={
        "direction": {
            "type": "string",
            "enum": ["north", "south", "east", "west"],
            "description": "Direction to move"
        }
    }
)

def move_party(direction: str, context=None) -> str:
    if not context:
        return "Error: No context available"
    
    # Access game state through context
    success, message = context.game_state.dungeon_state.move_party(direction)
    return message