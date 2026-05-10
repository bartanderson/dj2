Escalation Engine – Design Document (v1.3)

This document defines the EscalationEngine: rule evaluation, causal propagation, and effect generation within the simulation architecture.

Global architectural constraints, authority boundaries, and cross-system execution rules are defined in System Invariants & Cross-Layer Contracts.

--

The Escalation Engine is the rule-driven causal propagation layer of the simulation architecture.

It does not define authoritative world state.
It does not perform narrative interpretation.
It evaluates structured events against deterministic escalation rules and emits rule-driven follow-up effects or events.

Think of it as:

Event Log = “what happened”
Escalation Engine = “what additional consequences may occur because of it”

Core function categories:
- rule matching
- trigger evaluation
- event emission (via EventLog)
- depth control (anti-loop safety)

1. Purpose
EscalationEngine evaluates EventLog events against declarative YAML rules 
Rules are evaluated per event in isolation; the engine does not maintain conversational or narrative state.

Execute actions (registered Python functions) when rules match and conditions are true.
When a rule matches, EscalationEngine executes pre-registered Python functions referenced by name in the YAML.
Actions receive:
- triggering Event
- computed context object (rule + extracted fields)
Actions may emit new events via EventLog 
Actions must not modify the original event.

Manage a structured list of active effects (world modifiers) that can be queried by the ContextBuilder.
EscalationEngine maintains persistent “effects” representing world state modifiers derived from events.
Effects are:
- independent of Event history
- queryable by ContextBuilder during narrative construction
- updated or appended only via rule-triggered actions

Prevent infinite loops using a depth guard stored in the Event object (not inside event data).
EscalationEngine enforces recursion safety using event.depth.
Rules:
- if event.depth >= MAX_DEPTH, processing stops
- emitted event increments depth: new_event.depth = event.depth + 1
- only EscalationEngine is allowed to propagate depth


2. Rule Format (YAML) example
Escalation rules are defined declaratively in YAML. YAML specifies:
- triggering events
- conditions
- rule matching and selection
- resulting actions

Conditions operate against normalized Event objects whose data field is always an AttrDict, allowing deterministic attribute-style access via AttrDict (event.data.entity_id).

Python action handlers implement deterministic mechanics only, including:
- state mutation
- calculations
- persistence
- event emission

The AI layer may contextualize outputs but does not influence rule execution.

Rules are evaluated independently
Multiple rules may match the same event
Execution order is deterministic (YAML order)

Rule execution is strictly single-pass per event. A rule may not re-trigger evaluation of earlier rules within the same processing cycle unless explicitly emitted as a new event via EventLog.

Actions are executed in the order listed in the YAML actions array. Actions are not parallelized and must complete before the next action executes.

Rule evaluation is side-effect aware only at the EventLog emission boundary; conditions must not depend on transient side effects produced earlier in the same rule execution cycle.

Rule logic must remain defined in YAML; Python callbacks may only implement deterministic actions. 

This preserves:
- inspectable causal chains
- deterministic reasoning
- generator compatibility
- AI constraint boundaries
- consistency with the system’s phase/bucket architecture

2.1 Pattern Matching Semantics
Event patterns use shell-style wildcard matching via fnmatch.
Examples:
- event: combat.*
- event: economy.buy
- event: perception.*

Matching behavior:
Matching uses fnmatch semantics against event.type.
Example:
- `"combat.*" matches "combat.entity.killed" and "combat.turn.started".`
- `"*.entity.killed" matches "combat.entity.killed" and "economy.entity.killed".`
combat.* matches all event types in the combat namespace
exact names match only identical event types
matching is deterministic and case-sensitive

For performance, wildcard patterns may be precompiled internally to regex during rule loading, but runtime behavior must remain equivalent to fnmatch.

Rules MAY emit effects that include a salience flag.
This flag is a deterministic instruction consumed by ContextBuilder and does not modify event data or EventLog state.

```yaml
rules:
  - id: faction_retaliation
    event: combat.entity.killed
    conditions:
      - event.data.killed_faction == "bandits"
      - event.data.location_id is not None
    actions:
      - increase_threat
      - spawn_hunters
      - emit_warning_event

  - id: merchant_suspicion
    event: economy.theft.detected
    conditions:
      - event.data.value > 100
    actions:
      - reduce_reputation
      - notify_guards
```

3. Active Effects (structured)
Active effects returned by get_active_effects() MUST represent a snapshot at call time.
ContextBuilder operates only on this snapshot and MUST NOT observe mid-frame mutations.

```python
EscalationEffect = {
    "id": str,                     # unique identifier
    "type": str,                   # e.g., "reinforcement", "faction_modifier"
    "source_event": str,           # the event type that created it
    "expires_at": Optional[str],   # ISO timestamp, None = indefinite
    "salience": Optional[bool],   # if True, forces inclusion in ContextBuilder salience list
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

world (read-only interface exposing query functions)

Returns True/False. If evaluation fails (invalid expression, missing key), logs warning and returns False.

5.1 Integration with Event Log

Event correlation is strictly defined as:

- exact match on event.type, OR
- match on explicit effect.source_event, OR
- shared entity_id between event.data and effect.scope

No semantic or fuzzy matching is permitted.

EscalationEngine is registered as a listener to EventLog and processes all emitted events.

Depth is strictly a propagation control mechanism within EscalationEngine only.
ContextBuilder MUST NOT interpret, filter, or branch logic based on event.depth.

```python
self.event_log = get_event_log()
self.escalation = EscalationEngine(self.event_log, self.world)
self.escalation.load_rules("config/escalation_rules.yaml")
self.event_log.on_any(self.escalation.process_event)

source_system = "escalation_engine"

actor_id = None

depth = event.depth + 1

and call self.event_log.emit(...).
```

5.2 Depth Propagation Rule (v1)

Depth propagation is handled exclusively by EscalationEngine during event emission. Adjudication-originated events always begin with depth = 0.

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

9. Authority Boundary

EscalationEngine visibility-related effects are interpretive overlays only and must never directly mutate or redefine canonical visibility state.
All visibility changes must be applied exclusively through ContextBuilder’s deterministic visibility pipeline.