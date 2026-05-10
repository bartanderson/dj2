ContextBuilder – Design Document (v1.3)
This document defines subsystem behavior, context derivation, visibility processing, salience filtering, and internal pipeline rules for ContextBuilder.

Global architectural constraints, authority boundaries, and cross-system execution rules are defined in System Invariants & Cross-Layer Contracts.
--
1. Purpose
Provide a deterministic, filtered view of the game world and event history for the LLM (DM), UI, and other subsystems.

Enforce visibility (line‑of‑sight, lighting, stealth) and knowledge gaps (the AI should not know what the player cannot perceive).

Convert raw simulation data into a structured, narrative‑ready snapshot (UnifiedContext).

ContextBuilder must also incorporate EscalationEngine-derived effects as first-class inputs when constructing context. These effects represent rule-generated modifications to world state that are not directly present in the raw event log.

2. Inputs
WorldState – current positions, entity attributes, flags, combat state, encounter context, active_effects (from EscalationEngine)

Active effects represent structured, precomputed outputs of EscalationEngine rule evaluation.
They are immutable within ContextBuilder and must be applied as deterministic modifiers to perception and context construction only.
These effects are sourced exclusively from EscalationEngine.get_active_effects() and are considered already validated and time-pruned at the time ContextBuilder consumes them.

They must be applied during:
- visibility evaluation
- threat interpretation
- environmental modification
- awareness construction

Important ordering constraint:
Escalation effects are applied before knowledge gap construction and before FSM injection.

Escalation effects are applied according to System Invariants & Cross-Layer Contracts and consumed without reinterpretation.

ContextBuilder does not evaluate, infer, or interpret escalation rules.
It only consumes EscalationEngine outputs as structured data.

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
    "escalation_context": List[dict]  # structured EscalationEngine effects (verbatim, read-only, no transformation applied)
}
```
escalation_context must reflect active effects only, not derived interpretation or narrative summaries. It is a direct mirror of EscalationEngine state and must remain untransformed.

4. Salient Event Retrieval (Deterministic Backward Scan)

An event is considered salient through a strictly ordered evaluation process that depends on the final computed visibility state of the current ContextBuilder cycle.

4.1 Salience Evaluation Rules (ordered)

An event is salient if ANY of the following conditions are true, evaluated in order:

    1. Player involvement (highest priority)
     - event.actor_id == session_character_id
    2. EscalationEngine forced salience flag
     - Event is marked salient via EscalationEngine effect metadata or rule-derived flag
    3. System-level event sources
     - event.source_system ∈ {'perception','sound','combat','escalation','encounter'}
    4. Visibility-based relevance
     - The event involves at least one entity that is in the final computed visible entity set for this ContextBuilder cycle

4.2 Entity involvement check
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
4.3 Retrieval Algorithm (deterministic backward scan)
- Initialize collected = []
- Iterate through event_log.get_events() from newest → oldest
- For each event:
    - Evaluate salience rules in order (4.1)
    - If event is salient → append to collected
- Stop when:
    - len(collected) >= SALIENT_LIMIT (default 20), OR
    - MAX_SCAN events have been evaluated (default 1000)
- Return collected in reverse chronological order (no reordering required)

4.4 Hard constraint
- EscalationEngine may force inclusion via salience flag
- EscalationEngine may NOT bypass visibility computation order
- Visibility state used in salience evaluation MUST be the finalized visibility output of the current ContextBuilder cycle

4.5 Invariant
Salience is a deterministic function of:
- event metadata
- final visibility state
- EscalationEngine flags (as modifiers, not replacements)
It does not modify visibility, only consumes it.

5. Processing Pipeline (Deterministic Order)
ContextBuilder executes a single-pass deterministic pipeline.
Each stage consumes the finalized output of the previous stage and must not:
- re-enter prior stages
- recompute prior outputs
- mutate previously finalized perception state
All perception-derived outputs are computed exactly once per build cycle.

5.1 Escalation Application Rules

EscalationEngine effects are applied as deterministic interpretation overlays, not as state mutations.

Each effect must define:
- effect.type (e.g., visibility.override, threat.increase)
- scope (entity_id / location_id / global)
- payload (structured parameters only)

ContextBuilder applies EscalationEngine effects in a single deterministic overlay pass immediately after base visibility computation and before salience retrieval, awareness derivation, and knowledge gap construction.

Overlay evaluation order:
1. Scope resolution
2. Visibility modifications
3. Awareness/environmental modifications
4. Finalized perception snapshot generation

After this overlay pass completes:
- visibility state is considered final for the current build cycle
- salience evaluation operates only on finalized visibility results
- later pipeline stages may consume visibility state but must not modify it

Escalation effects are then injected verbatim into escalation_context without transformation.

ContextBuilder must NOT:
- resolve effects into narrative text
- execute escalation logic
- mutate EscalationEngine state
- recompute visibility after overlay application

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

Knowledge gaps are derived only from final computed visibility state and raw world state. EscalationEngine may influence what is visible, but does not directly construct or modify knowledge gaps unless explicitly defined as a revelation-type effect.

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