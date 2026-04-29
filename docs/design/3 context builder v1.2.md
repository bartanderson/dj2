ContextBuilder – Final Design Document (v1.2)
1. Purpose
Provide a deterministic, filtered view of the game world and event history for the LLM (DM), UI, and other subsystems.

Enforce visibility (line‑of‑sight, lighting, stealth) and knowledge gaps (the AI should not know what the player cannot perceive).

Convert raw simulation data into a structured, narrative‑ready snapshot (UnifiedContext).

2. Inputs
WorldState – current positions, entity attributes, flags, combat state, encounter context.

EventLog – recent events (full history).

EscalationEngine – to query active escalation effects.

Session ID – identifies the player character.

3. Output (UnifiedContext)
A JSON‑serializable dictionary with the following sections:

```python
UnifiedContext = {
    "timestamp": str,
    "visible_entities": List[dict],
    "hidden_entities": List[dict],
    "partially_known_entities": List[dict],
    "environment": {
        "location": str,
        "terrain": str,
        "lighting": float,
        "sound_level": float,
        "weather": str
    },
    "awareness": {
        "known_threats": List[str],
        "known_allies": List[str],
        "unknown_threat_signals": List[str]
    },
    "salient_events": List[dict],      # filtered event log entries
    "knowledge_gaps": dict,
    "encounter_context": dict,
    "combat_context": dict,
    "escalation_context": List[dict]    # active escalation effects
}
```
4. Salient Event Retrieval (Deterministic Backward Scan)
An event is salient if any of the following is true:

event.actor_id == session_character_id (player directly involved)

event.source_system in {'perception','sound','combat','escalation','encounter'} (these systems are always globally relevant)

The event involves at least one currently visible entity, using the entity reference convention:

```python
def event_involves_visible_entity(event, visible_ids):
    ids = set()
    if hasattr(event.data, 'entity_id'):
        ids.add(event.data.entity_id)
    if hasattr(event.data, 'target_id'):
        ids.add(event.data.target_id)
    if hasattr(event.data, 'involved_entities'):
        ids.update(event.data.involved_entities)
    return not ids.isdisjoint(visible_ids)
```
Retrieval algorithm (called during each build):

Set collected = []

Iterate backwards through event_log.get_events() (from newest to oldest).

For each event, if it passes the salience test, add it to collected.

Stop when len(collected) >= SALIENT_LIMIT (default 20) or after scanning MAX_SCAN events (default 1000).

Return collected (already in reverse chronological order, no need to reverse again).

5. Processing Pipeline (Deterministic Order)
Slice WorldState – extract raw facts (positions, flags, combat state, etc.).

Apply visibility model – determine visible_entities, hidden_entities, and partially_known_entities using:

Same location (hex or room)

Lighting (location.lighting, character darkvision, light sources)

Stealth mode (if true, entity is hidden unless perception check succeeds – v1 simplifies to always hidden)

Memory (entities seen before but not currently visible go into partially_known_entities)

Retrieve salient events (as above).

Build environment and awareness from current location and character.

Construct knowledge gaps – list unidentified entities, unknown sounds, etc.

Inject context from active FSMs (encounter, combat) and escalation effects.

Return UnifiedContext (read‑only dict).

6. API
```python
class ContextBuilder:
    def __init__(self, world_controller: WorldController,
                 event_log: EventLog,
                 escalation_engine: EscalationEngine):
        self.world = world_controller
        self.event_log = event_log
        self.escalation = escalation_engine

    def build(self, session_id: str) -> dict:
        """
        Returns UnifiedContext dictionary.
        Raises ValueError if session_id invalid.
        """
        # Implementation follows the pipeline described above.
        # All helper methods are private (e.g., _compute_visibility, _get_salient_events).
```
7. Performance Constraints
build() must complete in <20ms for a typical game state (≤100 visible entities, ≤1000 events).

Backward scan limited to MAX_SCAN = 1000 events.

Visible entity computation must be O(n) where n is number of entities in same location.

8. Error Handling
If any helper fails (e.g., visibility computation), log error and return a safe default (e.g., empty visible list, no salient events). The game does not crash.

9. Testing
9.1 Unit Tests
Visibility with different lighting, darkvision, stealth, and memory.

Salient event backward scan – verify it stops at limit and respects entity involvement.

Knowledge gaps construction.

Each helper function isolated.

9.2 Integration Test
Build a mock WorldController with a location, two entities, one hidden.

Populate EventLog with a mix of salient and non‑salient events.

Call ContextBuilder.build() and verify:

Only visible entity appears in visible_entities.

Only the last 20 salient events (or fewer) are included.

escalation_context contains effects from escalation engine.

10. Future Extensions (v2)
Line‑of‑sight (ray casting) for visibility.

Skill‑based perception checks.

Persistent memory across sessions.

Weighted salience (e.g., combat events more important than sound events).

This document is final (v1.2). All three core designs (Event Log, Escalation Engine, ContextBuilder) are now approved.

We will now proceed to Phase 0 implementation in the following order:

Event Log

Escalation Engine

ContextBuilder

Integration test