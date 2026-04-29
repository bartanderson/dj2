ContextBuilder – Design Document
1. Purpose
Provide a deterministic, filtered view of the game world and event history for the LLM (DM), UI, and other subsystems.

Implement visibility, awareness, and knowledge gaps (the LLM should not know what the player cannot perceive).

Convert raw simulation data into a structured, narrative‑ready snapshot.

2. Inputs
WorldState – current positions, entity attributes, flags, combat state, encounter context.

EventLog – recent events (configurable window, e.g., last 100 events or last 10 minutes).

Active modifiers – encounter context (scope, tension), lighting, sound level, stealth status.

3. Output (UnifiedContext)
A read‑only dictionary with the following sections:

visible_entities – list of entities fully perceived.

hidden_entities – list of entities whose existence is known but not details.

partially_known_entities – entities seen before but not currently visible.

environment – location, terrain, lighting, sound level, weather.

awareness – known threats, known allies, unknown threat signals (e.g., "you hear growling").

salient_events – filtered events relevant to the current context.

knowledge_gaps – explicit list of what is unknown (e.g., "unknown entities: goblin archer").

encounter_context – if an active encounter exists, its description, allowed actions, tension.

combat_context – turn order (visible subset), current actor, known combatants.

escalation_context – active escalation chains, alert levels, faction states.

4. Processing Pipeline (deterministic order)
Slice WorldState – extract raw facts without filtering.

Apply visibility model – line of sight, lighting, stealth, occlusion → produce visible_entities, hidden_entities.

Apply perception rules – memory (previously seen) → produce partially_known_entities.

Filter events – include only events that involve visible entities or are from domains (perception, sound, combat, escalation, encounter) that override visibility.

Inject context modifiers – encounter, combat, escalation, sound, lighting.

Construct knowledge gaps – list unknown entities, ambiguous sounds, uncertain event outcomes.

Return UnifiedContext (read‑only).

5. Rules
No inference beyond facts – ContextBuilder does not guess intentions or predict outcomes.

No contradiction of WorldState – if WorldState says X, UnifiedContext must not contradict it.

No narrative shaping – tension or drama is added by the escalation engine or narrative layer, not here.

Deterministic – same inputs always produce same output.

6. Integration
Called by dm_chat_handler before invoking the LLM.

Also used by UI and any subsystem that needs a filtered view.

Does not modify state or emit events.

7. Testing
Unit tests for visibility filtering, event relevance, knowledge gap construction.

Integration test: given a WorldState and EventLog, verify that the UnifiedContext matches expected filtered view.