Below is the consolidated design specification for all major components. It defines data models, APIs, integration with the 7‑phase GameEngine, performance constraints, and test requirements. Please review and approve or request changes. Once approved, I will implement strictly to this specification.

Consolidated Design Specification
1. Shared Data Models
1.1 Event
python
Event = {
    "type": str,               # domain.entity.phase (see event taxonomy)
    "data": dict,              # arbitrary JSON data
    "source": str,             # e.g., "adjudication_engine", "combat_fsm"
    "timestamp": str           # ISO format
}
1.2 UnifiedContext (output of ContextBuilder)
python
UnifiedContext = {
    "timestamp": str,
    "visible_entities": List[Entity],
    "hidden_entities": List[Entity],
    "partially_known_entities": List[Entity],
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
    "salient_events": List[Event],
    "knowledge_gaps": dict,
    "encounter_context": dict,
    "combat_context": dict,
    "escalation_context": dict
}
1.3 Entity Reference
python
EntityRef = {
    "type": str,   # "item", "npc", "location", "skill", "spell", "quest"
    "id": str,
    "name": str
}
2. Component Specifications
2.1 Event Log
Data Models – as above.

API:

emit(event_type: str, data: dict, source: str) -> None

on(event_type: str, callback: Callable[[Event], None]) -> None

on_any(callback: Callable[[Event], None]) -> None

get_events(event_type: Optional[str] = None, limit: int = 100) -> List[Event]

clear() -> None

Integration: AdjudicationEngine holds a singleton instance. Called whenever an action (buy, attack, etc.) completes.

Performance: emit must return in <10ms; listeners are synchronous.

Test requirements:

Emit an event, verify it appears in get_events.

Register a listener, emit, verify listener called.

2.2 Escalation Engine
Data Models: Rule as defined in design document.

API:

load_rules(yaml_path: str) -> None (raises FileNotFoundError, YAMLError)

register_action(name: str, func: Callable[[Event, dict], None]) -> None

process_event(event: Event) -> None (called by EventLog)

Integration: Registered in AdjudicationEngine.__init__. Calls event_log.on_any(self.process_event). Evaluates rules synchronously.

Performance: Must process all rules for an event within 50ms.

Test requirements:

Load a rule, emit matching event, verify action called.

Conditions evaluate correctly.

Priority and stop_on_match work.

2.3 ContextBuilder
Data Models: Input = (WorldState, EventLog, active_modifiers); Output = UnifiedContext.

API:

build(session_id: str) -> UnifiedContext
Caches nothing; deterministic.

Integration: Called by dm_chat_handler before LLM invocation. Also by UI and other subsystems.

Performance: Must build context within 20ms.

Test requirements:

Given a simple world state and event log, verify that visible/hidden entities are correct.

Knowledge gaps are populated.

2.4 Entity Resolution
Data Models: Input = (raw_text: str, context: dict); Output = Optional[EntityRef].

API:

resolve(raw_text: str, context: dict) -> Optional[EntityRef]

register_synonym(alias: str, canonical: str) -> None

load_merchant_items(merchant) -> None (populates internal index)

Integration: Used in `_handle_transaction` and `_handle_look`. Falls back to fuzzy matching.

Performance: Resolution <5ms.

Test requirements:

Exact match, synonym, fuzzy match, contextual inference.

2.5 Dialogue System
Data Models: Dialogue definition JSON (as in design doc). FSM states + transitions.

API:

start_dialogue(session_id, npc_id, dialogue_def_path) -> FSMWrapper

process_choice(session_id, choice_index_or_text) -> (response_text, actions)

Integration: AdjudicationEngine routes talk intent to dialogue system. Dialogue actions call engine methods (e.g., give_quest).

Test requirements:

Load a dialogue, traverse nodes, verify conditions and actions.

2.6 Quest System
Data Models: Quest definition JSON (states, transitions, guards, actions).

API:

start_quest(quest_id, character_id) -> None

progress_quest(quest_id, event_type, event_data) -> None

get_quest_state(quest_id, character_id) -> str

Integration: Quest actions can be called from dialogue or combat. Quests listen to events (e.g., combat.entity.killed).

Test requirements:

Accept quest, satisfy condition, complete, verify reward.

2.7 Combat System
Data Models: Combat FSM JSON (as in design doc). Participants list, turn order.

API:

start_combat(participants, location) -> None

process_action(session_id, action_type, target_ref) -> None

get_combat_state(session_id) -> dict

Integration: Triggered by encounter FSM or direct player command. Uses OGSystem for skill checks, damage. Emits combat events for escalation.

Test requirements:

Simulate attack, verify damage applied, death, end of combat.

3. Integration with 7‑Phase GameEngine
Input (player message) → Interpretation (IntentParser, Entity Resolution)

Adjudication (FSM routing, AI DM) – this is where most components live

Authority (validation, guards)

Mutation (execute actions, emit events)

Consequence (escalation engine reacts)

Persistence (save state)

View (ContextBuilder builds UnifiedContext for UI/LLM)

The escalation engine runs during the Consequence phase. The ContextBuilder runs during View.

4. Performance and Error Handling
All synchronous operations must complete within the limits stated above.

Any component that fails (e.g., rule evaluation error) logs the error and continues (does not crash the game).

Missing event patterns or unknown actions are logged and ignored.

5. Test Requirements (non‑negotiable)
Each component must have:

Unit tests for all public methods, covering normal and error paths.

At least one integration test that exercises the component with the AdjudicationEngine and mock world controller.