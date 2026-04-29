Escalation Engine – Final Design Document (v1.2)
1. Purpose
React to events emitted by the game (see Event Log) by evaluating declarative rules defined in YAML.

Execute actions (registered Python functions) when rules match and conditions are true.

Manage a structured list of active effects (world modifiers) that can be queried by the ContextBuilder.

Prevent infinite loops using a depth guard stored in the Event object (not inside event data).

2. Rule Format (YAML)
```yaml
rules:
  - name: "goblin_death_in_forest"
    event_pattern: "combat.entity.killed"       # supports wildcards (*)
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
```
2.1 Pattern Matching Semantics (fnmatch + precompiled regex)
Patterns are matched against the full event.type string.

* matches any sequence of characters (including .).

The engine precompiles each pattern into a regex at rule load time using fnmatch.translate + re.compile.

Matching is full‑string (the pattern must match the entire event.type).
Example:

`"combat.*" matches "combat.entity.killed", "combat.turn.started".`

`"*.entity.killed" matches "combat.entity.killed", "economy.entity.killed".`

3. Active Effects (structured)
```python
EscalationEffect = {
    "id": str,                     # unique identifier
    "type": str,                   # e.g., "reinforcement", "faction_modifier"
    "source_event": str,           # the event type that created it
    "expires_at": Optional[str],   # ISO timestamp, None = indefinite
    "data": dict                   # effect‑specific parameters
}
```
The engine maintains self.active_effects: List[EscalationEffect].
Actions can add/remove effects. The engine prunes expired effects before processing events (or on a scheduled tick).

4. Engine API
4.1 Initialisation
```python
def __init__(self, event_log: EventLog, world_controller: WorldController):
    self.event_log = event_log
    self.world = world_controller
    self.rules = []               # list of rule dicts, each with a "_compiled" key
    self.action_registry = {}     # name -> callable
    self.active_effects = []
```
4.2 Rule Loading
```python
def load_rules(self, yaml_path: str) -> None:
    """Load YAML, precompile patterns, store rules."""
    # Raises FileNotFoundError, yaml.YAMLError, or ValueError on invalid structure.
```
4.3 Action Registration
```python
def register_action(self, name: str, func: Callable[[Event, dict], None]) -> None:
    """Register a function that can be invoked by name from a rule."""
    self.action_registry[name] = func
```
4.4 Event Processing (Depth Guard)
```python
def process_event(self, event: Event) -> None:
    """Called by EventLog for every event. Evaluates rules in priority order."""
    if event.depth > MAX_DEPTH:   # MAX_DEPTH = 10
        logger.warning(f"Event depth {event.depth} exceeded limit, discarding")
        return

    for rule in sorted(self.rules, key=lambda r: -r.get("priority", 0)):
        if not rule["_compiled"].match(event.type):
            continue
        # Evaluate conditions (simpleeval with event (AttrDict) and world facade)
        if not all(self._eval_condition(cond, event) for cond in rule.get("conditions", [])):
            continue
        # Execute actions
        for action in rule.get("actions", []):
            func = self.action_registry.get(action["name"])
            if func:
                func(event, action.get("params", {}))
            else:
                logger.error(f"Unknown escalation action: {action['name']}")
        if rule.get("stop_on_match", False):
            break
```
4.5 Effect Management
```python
def add_effect(self, effect: EscalationEffect) -> None:
    self.active_effects.append(effect)

def remove_effect(self, effect_id: str) -> None:
    self.active_effects = [e for e in self.active_effects if e["id"] != effect_id]

def get_active_effects(self) -> List[EscalationEffect]:
    self.prune_effects(datetime.now(timezone.utc))
    return self.active_effects.copy()

def prune_effects(self, current_time: datetime) -> None:
    self.active_effects = [e for e in self.active_effects
                           if e["expires_at"] is None or e["expires_at"] > current_time.isoformat()]
```
4.6 Condition Evaluation
Uses simpleeval with a context containing:

event (AttrDict‑wrapped Event object, so event.data.target.faction works)

world (a read‑only facade with methods like get_faction_standing, get_current_location, etc.)

Returns True/False. If evaluation fails (invalid expression, missing key), logs warning and returns False.

5. Integration with Event Log
In AdjudicationEngine.__init__:

```python
self.event_log = get_event_log()
self.escalation = EscalationEngine(self.event_log, self.world)
self.escalation.load_rules("config/escalation_rules.yaml")
self.event_log.on_any(self.escalation.process_event)
When an action (e.g., spawn_reinforcements) needs to emit a new event, it should create an Event with:

source_system = "escalation_engine"

actor_id = None

depth = event.depth + 1

and call self.event_log.emit(...).
```
6. Performance Constraints
Rule matching (precompiled regex): <1ms per rule.

Condition evaluation: <2ms per condition.

process_event for ≤50 rules: <50ms.

7. Testing
7.1 Unit Tests
Load rules, verify precompiled patterns match correctly.

Register an action, emit event that matches rule → action called.

Condition evaluation (true/false, invalid expression).

Priority ordering (higher first, stable for equal).

stop_on_match halts further rules.

Depth guard prevents infinite loops.

Effect lifecycle (add, remove, prune).

7.2 Integration Test
Emit an event that triggers a rule, which adds an effect and emits a follow‑up event. Verify that the follow‑up event has depth = original_depth + 1 and that the effect appears in get_active_effects().

8. Future Extensions (v2)
Rule hot‑reload.

Asynchronous action execution.

Conditional branching in rule actions.