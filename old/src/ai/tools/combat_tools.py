from src.ai.tool_registry import registry

@registry.register(
    name="resolve_combat",
    description="Resolve combat encounter between party and NPC",
    parameters={
        "npc_id": {
            "type": "string",
            "description": "ID of NPC involved in combat"
        },
        "tactic": {
            "type": "string",
            "enum": ["aggressive", "defensive", "strategic"],
            "description": "Combat approach for NPC"
        }
    }
)
def resolve_combat(npc_id: str, tactic: str, context=None) -> str:
    # Implementation logic here
    return f"Combat with {npc_id} resolved using {tactic} tactic"