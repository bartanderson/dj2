Escalation Engine – Design Document
1. Purpose
React to events emitted by the game (combat, economy, movement, perception, etc.) and trigger consequences (world state changes, new event emissions, spawning encounters, etc.).

Implement a deterministic, declarative rule system that can be edited without code changes.

Enable non‑linear storytelling, faction shifts, and dynamic world reactions.

2. Core Concepts
Event – a record of something that happened (see event taxonomy).

Rule – a conditional statement: when an event of type X occurs, if conditions Y are true, then execute actions Z.

Action – a registered function that modifies the world state or emits new events.

Engine – a component that listens to events, evaluates rules, and executes actions synchronously.

3. Rule Definition Format
Rules are stored in YAML files (e.g., config/escalation_rules.yaml). Each rule has:

yaml
- name: "optional_name"                # for debugging
  event_pattern: "event.type.string"   # exact match
  conditions:                          # list of boolean expressions
    - "condition1"
    - "condition2"
  actions:                             # list of actions to perform
    - name: "action_name"
      params:
        param1: value1
  priority: 0                          # higher priority runs first
  stop_on_match: false                 # if true, do not evaluate further rules
3.1 Conditions
Conditions are strings that will be evaluated with access to:

event – the event object (containing .type, .data, .source, .timestamp)

world – a snapshot of relevant world state (e.g., party location, faction standings, character skills)

We will use a safe evaluator (e.g., simpleeval). Examples:

event.data.killed_faction == 'goblins'

world.current_location.terrain == 'forest'

world.get_faction_standing('goblins') < -10

3.2 Actions
Actions are Python functions registered with the escalation engine. They receive:

event – the triggering event

params – the parameters from the rule

Example action: spawn_reinforcements that creates new monsters in the current location.

4. Engine Operation
The EventLog will call escalation.process_event(event) for every event emitted.

The engine iterates rules in priority order (highest first).

For each rule, if the event_pattern matches and all conditions evaluate to True, the actions are executed.

If stop_on_match is true, no further rules are evaluated for this event.

5. Integration with Existing Systems
The engine is initialised in AdjudicationEngine and registered with the EventLog.

The engine will have access to WorldController (via a wrapper) to read/write world state.

Actions can emit new events by calling event_log.emit(...).

6. Example Rule
```yaml
- name: "goblin_death_in_forest"
  event_pattern: "combat.entity.killed"
  conditions:
    - "event.data.killed_faction == 'goblin'"
    - "world.current_location.terrain == 'forest'"
  actions:
    - name: "spawn_reinforcements"
      params:
        monster_type: "goblin"
        count: 2
    - name: "modify_faction_standing"
      params:
        faction: "goblins"
        delta: -5
  priority: 10
  stop_on_match: false
```
7. Testing
Unit tests for rule parsing, condition evaluation, and action execution.

Integration test: emit a known event and verify that the world state changes as expected.

8. Future Extensibility
Allow regex event_pattern matching `(combat.*)`.

Support more complex condition expressions (e.g., event.data.damage > 5).

Add asynchronous action execution (task queue) for long‑running effects.