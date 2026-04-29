Escalation Engine – Revised Design Document (v1)
1. Purpose
React to events emitted by the game (see Event Taxonomy) and trigger consequences.

Implement a deterministic, declarative rule system (YAML) that can be edited without code changes.

Enable dynamic world reactions, faction shifts, and non‑linear storytelling.

2. Core Concepts
Event – as defined in Event Taxonomy, with type string following the pattern domain.entity.phase.

Rule – condition‑action pair evaluated when an event of a given type occurs.

Action – registered Python function that modifies world state or emits events.

Engine – listens to events, evaluates rules, executes actions.

3. Data Models
3.1 Rule (internal)
python
Rule = {
    "name": str,                    # optional debug label
    "event_pattern": str,           # exact match (v1)
    "conditions": List[str],        # boolean expressions
    "actions": List[Dict],          # [{"name": str, "params": dict}]
    "priority": int,                # higher = earlier, default 0
    "stop_on_match": bool           # default False
}
3.2 Rule File (YAML) – Example
yaml
rules:
  - name: "goblin_death_in_forest"
    event_pattern: "combat.entity.killed"
    conditions:
      - "event.data.killed_faction == 'goblins'"
      - "world.current_location.terrain == 'forest'"
    actions:
      - name: "spawn_reinforcements"
        params: { monster_type: "goblin", count: 2 }
      - name: "modify_faction_standing"
        params: { faction: "goblins", delta: -5 }
    priority: 10
    stop_on_match: false
4. API
4.1 Class EscalationEngine
__init__(self, event_log: EventLog, world_controller: WorldController)
Stores references; initialises rule list and action registry.

load_rules(self, yaml_path: str) -> None
Loads YAML, validates structure (event_pattern present, actions list, etc.).

Raises: FileNotFoundError, yaml.YAMLError, ValueError.

register_action(self, name: str, func: Callable[[Event, dict], None]) -> None
Stores function for later execution.

process_event(self, event: Event) -> None
Called by Event Log for every event.

Sorts rules by priority descending; for equal priority, maintains insertion order (stable sort).

For each rule:

If event.type != rule["event_pattern"] → skip.

Evaluate all conditions using `_eval_condition`. If any false → skip.

Execute each action: lookup function, call with (event, params).

Log errors (unknown action, exception) but continue.

If stop_on_match True → break.

Never raises exceptions (logs internally).

`_eval_condition(self, expr: str, event: Event) -> bool`
Evaluate expression using simpleeval.

Context includes:

event (Event object, with attributes .type, .data, .source, .timestamp)

world (read‑only facade with methods like get_faction_standing(faction_id), get_party_skill(skill), get_time_of_day(), etc.)

Returns True or False. On error, logs and returns False.

5. World Context Specification
The world object available to conditions must provide at least:

world.current_location – object with attributes name, terrain, region, etc.

world.get_faction_standing(faction_id: str) -> int (range -100 to 100)

world.get_party_skill(skill_name: str) -> int (e.g., "stealth", "athletics")

world.get_time_of_day() -> str ("dawn", "morning", "afternoon", "evening", "night")

world.get_weather() -> str (optional)

Additional read‑only methods can be added as needed.

6. Integration with Event Log
In AdjudicationEngine.__init__:

python
self.event_log = get_event_log()
self.escalation = EscalationEngine(self.event_log, self.world)
self.escalation.load_rules("config/escalation_rules.yaml")
self.event_log.on_any(self.escalation.process_event)
Actions can emit new events via self.event_log.emit(...).

7. Performance Constraints
process_event < 50ms for ≤50 rules.

Condition evaluation <2ms per condition.

8. Error Handling
Invalid YAML → startup failure.

Unknown action name → logged, action skipped.

Exception in action → logged, next action continues.

Condition evaluation error → condition treated as False, rule skipped.

9. Testing
9.1 Unit Tests (tests/unit/test_escalation_engine.py)
Load valid/invalid YAML.

Register action, fire matching event → action called.

Condition evaluation (true/false, invalid expression).

Priority ordering (higher first, stable for equal).

`stop_on_match` halts further rules.

Unknown action logs error but continues.


9.2 Parameterized Integration Test (tests/integration/test_escalation_integration.py)
All tests will be parameterized over relevant inputs (faction, terrain, expected action parameters) to ensure coverage without duplication.

Example:

python
@pytest.mark.parametrize("faction, terrain, expected_delta", [
    ("goblins", "forest", -5),
    ("bandits", "plains", -3),
    ("undead", "graveyard", -10),
])
def test_kill_triggers_faction_change(faction, terrain, expected_delta):
    # Set up mock world with given terrain and faction standing
    # Emit event combat.entity.killed with killed_faction = faction
    # Verify that modify_faction_standing is called with delta = expected_delta
Additional parameterized tests will cover:

Different event patterns (combat, economy, movement)

Different action types (spawn, reputation, quest progress)

Priority and stop_on_match interactions

Example of overly specific test that caused the above
```python
def test_goblin_death_triggers_reinforcements():
    # Mock world controller with faction standing methods
    world_mock = MockWorldController()
    world_mock.current_location.terrain = "forest"
    world_mock.get_faction_standing.return_value = -10
    # Create escalation engine with a rule file
    engine = EscalationEngine(event_log, world_mock)
    engine.load_rules("test_rules.yaml")
    # Emit an event matching the rule
    event = Event("combat.entity.killed", {"killed_faction": "goblins"}, "combat")
    engine.process_event(event)
    # Verify that spawn_reinforcements and modify_faction_standing were called
    world_mock.spawn_reinforcements.assert_called_once_with(monster_type="goblin", count=2)
    world_mock.modify_faction_standing.assert_called_once_with(faction="goblins", delta=-5)
```
10. Future Extensions (v2)
Regex pattern matching for event types.

More complex conditions (e.g., arithmetic comparisons).

Asynchronous action execution (task queue).

Rule hot‑reload during gameplay.