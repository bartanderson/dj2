ContextBuilder – Final Design Document (v1)
1. Purpose
Provide a deterministic, filtered view of the game world and event history for the LLM (DM), UI, and other subsystems.

Implement visibility, awareness, and knowledge gaps (the LLM should not know what the player cannot perceive).

Convert raw simulation data into a structured, narrative‑ready snapshot (UnifiedContext).

2. Inputs
WorldState – current positions, entity attributes, flags, combat state, encounter context.

EventLog – recent events (configurable window, e.g., last 100 events or last 10 minutes).

Active modifiers – lighting, sound level, stealth status, active encounter, combat state.

3. Output (UnifiedContext)
A read‑only dictionary (JSON‑serializable) with the following sections:

python
UnifiedContext = {
    "timestamp": str,                     # ISO format
    "visible_entities": List[dict],       # full entity data
    "hidden_entities": List[dict],        # minimal entity data (id, type, name)
    "partially_known_entities": List[dict], # previously seen, not currently visible
    "environment": {
        "location": str,
        "terrain": str,
        "lighting": float,                # 0.0 (dark) to 1.0 (bright)
        "sound_level": float,             # 0.0 (silent) to 1.0 (loud)
        "weather": str
    },
    "awareness": {
        "known_threats": List[str],
        "known_allies": List[str],
        "unknown_threat_signals": List[str]   # e.g., "growling heard nearby"
    },
    "salient_events": List[dict],         # filtered event log entries
    "knowledge_gaps": dict,               # e.g., {"unidentified_entities": [...]}
    "encounter_context": dict,            # if active encounter
    "combat_context": dict,               # if active combat
    "escalation_context": dict            # active escalation chains, alerts
}
4. Processing Pipeline (deterministic order)
Slice WorldState – extract raw facts without filtering.

Apply visibility model – determine visible_entities, hidden_entities, and partially_known_entities using lighting, darkvision, stealth, and memory.

Filter events – include only salient events (involving visible entities or domains that override visibility).

Inject context modifiers – encounter, combat, escalation, sound, lighting.

Construct knowledge gaps – list unidentified entities, unresolved sounds.

Return UnifiedContext.

4.1 Visibility Model (v1)
Same location – Entities in the same location (hex or room) are considered for visibility.

Line of sight – Not implemented in v1 (assume direct line unless blocked by terrain flag – future).

Lighting – Each location has a lighting value (0.0 dark, 1.0 bright). Entities in dark locations are only visible if:

The observer has darkvision flag, or

The observer carries a light source (light radius > 0).

Stealth – A character can be in stealth_mode (true/false). If true, they are hidden unless an active perception check succeeds (not implemented in v1). For v1, stealth simply makes the entity hidden (moved to hidden_entities).

Memory – Entities that were visible or partially known in the past but are not currently visible are placed in partially_known_entities. The WorldController maintains a per‑character memory set of entity IDs seen previously (not persisted across sessions in v1).

4.2 Event Filtering
An event is salient if:

Its source is the current character or party (source == session_character_id).

It involves a visible entity (event.data contains entity_id that is in visible_entities).

Its domain is perception, sound, combat, escalation, encounter (regardless of visibility).

The builder includes up to the last 20 salient events.

4.3 Knowledge Gaps
For v1, knowledge gaps are limited to:

Unidentified entities – When a player fails a perception check, an entity may be marked as “sensed but unseen”. This requires the game to emit an event perception.unidentified_entity. The builder lists them in knowledge_gaps["unidentified_entities"].

Unknown sounds – unknown_threat_signals derived from sound.event.heard events that were not resolved.

4.4 Encounter/Combat Context
The builder queries AdjudicationEngine.active_fsms to check for an active EncounterFSM or CombatFSM.

If found, it extracts:

encounter_context – description, allowed actions, difficulty.

combat_context – turn order (visible subset), current actor, enemy health (only for visible enemies), combat status.

These FSMs must provide a get_context() method returning relevant data.

5. API
5.1 Class ContextBuilder
__init__(self, world_controller: WorldController, event_log: EventLog)
Stores references; no other initialization.

build(self, session_id: str) -> dict
Returns a UnifiedContext dict for the given session.

Raises: ValueError if session_id invalid.

Performance: must complete in <20ms.

Helper methods (private):
_compute_visibility(character) -> (List[Entity], List[Entity], List[Entity])

_filter_events(events: List[Event], visible_entities: List[Entity]) -> List[Event]

_get_environment() -> dict

_get_awareness(character, visible_entities) -> dict

_get_knowledge_gaps(visible, hidden, partially, events) -> dict

_get_encounter_context(session_id) -> dict

_get_combat_context(session_id) -> dict

_get_escalation_context() -> dict

6. Integration
Called by dm_chat_handler before invoking the LLM.

Also called by UI and any subsystem that needs a filtered view.

Does not modify state or emit events.

Uses the current WorldController state and EventLog.

7. Performance Constraints
build() must complete in <20ms for a typical game state (100 visible entities, 100 recent events).

If any helper exceeds its budget, it logs a warning and returns a best‑effort result.

8. Error Handling
If a helper fails (e.g., cannot compute visibility), the builder logs the error and returns a sensible default (e.g., treat all entities as hidden, empty context). The game does not crash.

9. Testing
9.1 Unit Tests (tests/unit/test_context_builder.py)
Test visibility with different lighting, darkvision, and stealth flags.

Test memory of previously seen entities (add entity, remove, then check partially known).

Test event filtering (only salient events included).

Test knowledge gap construction from perception events and sound events.

Test each helper method in isolation.

9.2 Integration Test (tests/integration/test_context_builder_integration.py)
Create a mock WorldController with a known state (two locations, one dark, one bright; entities with darkvision flags; a character with memory).

Populate EventLog with a mix of salient and non‑salient events.

Call ContextBuilder.build() and verify that the output matches the expected filtered view (visible/hidden lists, salient events, knowledge gaps).

10. Future Extensions (v2)
Line of sight (ray casting).

Skill‑based perception checks.

Persistent memory across sessions.

More sophisticated knowledge gaps (e.g., "something is moving in the shadows").

Caching for performance.