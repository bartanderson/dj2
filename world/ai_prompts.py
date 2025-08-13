def generate_location_description(location, world_state):
    prompt = f"""
    Location: {location.name} ({location.type})
    Base Description: {location.description}
    
    World Context:
    - Current factions: {', '.join(world_state.factions.keys())}
    - Global events: {', '.join(world_state.global_events[-3:])}
    
    Generate a vivid description including:
    1. Current atmosphere and notable sights
    2. 2-3 NPCs with brief motivations
    3. 1-2 potential quest hooks
    4. Available services (shops, temples, etc.)
    """
    return prompt

def generate_npc_dialogue(npc, narrative_state):
    prompt = f"""
    NPC: {npc.name} - {npc.role}
    Backstory: {npc.backstory}
    
    Known Secrets: {narrative_state.revealed_secrets}
    Active Quests: {[q.name for q in narrative_state.quest_log]}
    
    Generate:
    1. Greeting and current concerns
    2. 2-3 dialogue options for players
    3. Potential quest hooks or information
    """
    return prompt