Event Log & Escalation Engine – Design Document
1. Purpose
Record every significant action or occurrence in the game world as an event.

Allow other systems (escalation rules) to listen to specific event patterns and trigger consequences (state changes, new encounters, faction shifts, etc.).

Provide a deterministic history that can be used for debugging, latent expansion, and AI context.

2. Existing event_log.py
We already have a minimal event log that emits events to a list. We will extend it to support:

Subscribing to event types (e.g., economy.buy, combat.entity.killed).

Associating events with a source (e.g., adjudication_engine, combat_fsm).

Storing events with timestamp, source, type, and data.

3. Escalation Engine (ECA – Event‑Condition‑Action)
Rules are defined in JSON/YAML.

Each rule has:

event_pattern: a string (exact match or regex) to filter events.

conditions: a list of predicates evaluated against the event data and current world state.

actions: a list of action names (which call registered functions) to execute when conditions are met.

The engine runs synchronously after an event is emitted (no background threads).

Actions can alter the world state, emit new events, or cancel further processing.

Example rule:

yaml
- event_pattern: "combat.entity.killed"
  conditions:
    - "event.data.killed_faction == 'goblin'"
    - "world.campaign_state.party.location == 'forest'"
  actions:
    - "spawn_reinforcements"
    - "faction_standing.modify('goblin_tribe', -5)"
    - "emit('escalation.reinforcements_arrived')"
4. Integration with existing systems
AdjudicationEngine will still call event_log.emit() on actions (purchases, kills, etc.).

The escalation engine will listen to the event log and execute rules synchronously (or asynchronously if we add a queue).

Reactions can create new FSMs (e.g., starting an encounter) or modify the world state directly.

5. Implementation steps
Extend event_log.py with:

on(event_type, callback) to register listeners.

emit(event_type, data, source) to push an event and immediately notify listeners.

Create escalation_engine.py:

Load rules from a config/escalation_rules.yaml file.

For each rule, evaluate condition expressions (using a safe evaluator like simpleeval or a simple attribute lookup).

Execute registered action functions (from a registry similar to builtins).

In AdjudicationEngine, after any action that modifies state, call event_log.emit(...).

Ensure the escalation engine runs synchronously (to avoid race conditions).

6. Example use cases
Combat – killing a goblin activates spawn_reinforcements if in a forest.

Economy – buying a rare item raises merchant reputation.

Encounter – failing to flee may trigger a combat escalation.

Quest – completing an objective updates the quest state.

7. Testing
Unit tests for rule matching and condition evaluation.

Integration test: emit an event and verify that the intended action is called.

8. Future extensions
Complex conditions using player skills, reputation, time of day.

Asynchronous execution (if performance requires).

Rule ordering and priority.