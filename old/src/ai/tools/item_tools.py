# src/ai/tools/item_tools.py
from src.ai.tool_registry import registry

@registry.register(
    name="create_item",
    description="Create a new game item",
    parameters={
        "item_type": {
            "type": "string", 
            "enum": ["consumable", "equipment", "key_item"],
            "description": "Category of item"
        },
        "description": {
            "type": "string",
            "description": "Flavor text for the item"
        }
    }
)
def create_item(item_type: str, description: str, context=None) -> str:
    item_id = self.game_state.item_system.create_item(item_type, description)
    return f"Created item {item_id}: {description}"