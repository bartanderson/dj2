from src.ai.tool_registry import registry

@registry.register(
    name="describe_dungeon",
    description="Generate rich description of the current dungeon state",
    parameters={
        "detail_level": {
            "type": "string", 
            "enum": ["brief", "normal", "detailed"],
            "description": "Level of detail for description"
        }
    }
)
def describe_dungeon(detail_level: str = "normal", context=None) -> str:
    # Implementation will be moved here later
    pass