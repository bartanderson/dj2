Quest System – Revised Design Document (v1)
1. Purpose
Allow state‑driven quest management (inactive, active, completed, failed, abandoned).

Support dependencies (quest must be active, certain items possessed, previous quest stage complete).

Trigger actions on quest acceptance, progression, completion, or failure (e.g., spawn NPCs, give items, change faction standing, emit events).

Integrate with dialogue system (NPC gives quest, updates via conversation) and event system (e.g., kill monster triggers quest progress).

2. Scope (v1)
Static, pre‑authored quests only – quest definitions are created manually as JSON files. Dynamic / procedural quest generation is v2.

No level scaling – quest difficulty and rewards are fixed. Future v2 may compute rewards based on player level at completion.

No time limits – failure/abandon are triggered by explicit actions or events, not by timers. Time‑based quests are v2.

No quest dependencies (chains) – quests can be started independently. Quest chains and prerequisites are v2.

No persistence across sessions – quest state is not saved in v1 (will be added later).

3. Core Concepts
Quest Definition – a declarative description of a quest (states, transitions, guards, actions).

Quest FSM – each quest instance is a state machine (states: inactive, active, completed, failed, abandoned).

Transitions – triggered by events (e.g., accept, progress, complete, fail, abandon). Guards check prerequisites. Actions execute side effects.

Quest Manager – component that holds active quest instances per character/session, listens to game events, and forwards them to relevant quests.

4. Data Model
4.1 Quest Definition (JSON)
```json
{
  "name": "Goblin Menace",
  "initial_state": "inactive",
  "states": [
    { "name": "inactive", "prompt": "Not yet started." },
    { "name": "active", "prompt": "Active quest." },
    { "name": "completed", "final": true, "prompt": "Completed!" },
    { "name": "failed", "final": true, "prompt": "Failed." },
    { "name": "abandoned", "final": true, "prompt": "Abandoned." }
  ],
  "events": {
    "accept": {
      "transitions": [
        { "from": "inactive", "to": "active", "actions": ["log_quest_start", "emit_quest_accepted"] }
      ]
    },
    "progress": {
      "transitions": [
        { "from": "active", "to": "active", "cond": "objective_not_complete", "actions": ["update_objective"] },
        { "from": "active", "to": "completed", "cond": "all_objectives_complete", "actions": ["give_reward", "emit_quest_completed"] }
      ]
    },
    "fail": {
      "transitions": [
        { "from": "active", "to": "failed", "actions": ["emit_quest_failed"] }
      ]
    },
    "abandon": {
      "transitions": [
        { "from": "active", "to": "abandoned", "actions": ["emit_quest_abandoned"] }
      ]
    }
  },
  "objectives": [
    { "id": "kill_goblins", "description": "Kill 5 goblins", "required": 5, "current": 0 }
  ],
  "rewards": [
    { "type": "item", "id": "healing_potion", "quantity": 2 },
    { "type": "xp", "amount": 100 },
    { "type": "reputation", "faction": "village", "delta": 10 },
    { "type": "gold", "amount": 50 },
    { "type": "quest_flag", "flag": "goblin_menace_completed" }
  ]
}
```
4.2 Supported Reward Types (v1)
item – adds item(s) to character inventory.

xp – adds experience points.

reputation – modifies faction standing.

gold – adds gold.

quest_flag – sets a flag (used to unlock other quests or dialogue options).

4.3 Quest Instance
```python
class QuestInstance:
    def __init__(self, definition: dict, character_id: str):
        self.definition = definition
        self.character_id = character_id
        self.fsm = GenericFSM(definition)   # after conversion
        self.objectives = copy(definition.get('objectives', []))
        self.rewards = definition.get('rewards', [])
```
5. API
5.1 QuestManager (integrated into AdjudicationEngine)
__init__(self, event_log: EventLog, world_controller: WorldController)
Stores references; initialises active_quests: Dict[str, Dict[str, QuestInstance]] (session_id → quest_id → instance).

start_quest(self, session_id: str, quest_id: str) -> bool
Loads quest definition (from config/quests/{quest_id}.json), creates QuestInstance, stores in active_quests[session_id][quest_id], sends accept event.

Returns True if quest started, False if already active or definition missing.

progress_quest(self, session_id: str, quest_id: str, event_type: str, event_data: dict) -> None
If the quest instance exists and is active, sends the progress event to its FSM.

The FSM’s guards and actions will evaluate objectives and possibly transition to completed.

get_quest_state(self, session_id: str, quest_id: str) -> Optional[str]
Returns current state name (e.g., "active") or None if not started.

get_quest_status(self, session_id: str, quest_id: str) -> Optional[str]
Returns a human‑readable description of objectives and progress (e.g., "Kill goblins: 3/5"). Used for UI and DM context.

`_handle_event(self, event: Event) -> None`
Called by EventLog (registered via on_any). For each active quest, if the event matches a configured trigger (e.g., combat.entity.killed and the killed entity has a quest tag), call progress_quest with the event details.

5.2 Action Registry (shared)
register_quest_action(name: str, func: Callable[[QuestInstance, dict], None]) – same pattern as escalation actions.

Example actions:

update_objective – increments or sets an objective count. It expects objective_id and delta parameters.

give_reward – iterates over rewards list and applies each.

emit_quest_completed – emits quest.completed event.

emit_quest_failed – emits quest.failed event.

spawn_monster – spawns a creature and tags it with the quest ID and objective ID (e.g., quest_id="goblin_menace", objective_id="kill_goblins"). When the creature is killed, the death event includes these tags, allowing the quest to correctly attribute progress.

5.3 Guard Registry
Guards are evaluated using the same simpleeval mechanism as escalation engine. Context includes:

quest (the QuestInstance object, with methods like get_objective_count, all_objectives_complete, etc.)

character (player character, with methods like has_background(background_id))

world (read‑only facade)

event (the event that triggered the progress, if any)

Example guard: "quest.get_objective_count('kill_goblins') >= 5" or "character.has_background('hermit')".

6. Integration
The QuestManager is initialised in AdjudicationEngine.__init__.

It subscribes to the Event Log via `event_log.on_any(self._handle_event)`.

When an event matches a quest trigger (identified by tags or by event pattern), the manager calls progress_quest.

Dialogue actions can call start_quest or progress_quest.

Quest completion can emit events that trigger escalation rules (e.g., reputation changes, new encounters).

7. Performance Constraints
Starting a quest: load JSON (<50ms), create FSM (<10ms).

Handling an event: for each active quest, check triggers (<5ms per quest). Acceptable for ≤20 active quests.

8. Error Handling
Missing quest definition → log error and do not start quest.

Invalid JSON → startup error.

Unknown action name → logged; action skipped.

Guard evaluation error → treat as false; transition not taken.

9. Testing
9.1 Unit Tests (tests/unit/test_quest_system.py)
Load a quest definition, start it, verify state becomes active.

Send progress event that completes objectives, verify quest transitions to completed and rewards are granted (mock engine).

Test guards (e.g., objective not met → no transition; background condition → only true if character has background).

Test actions (e.g., update_objective changes context, spawn_monster tags correctly).

Test `_handle_event` dispatches to correct quest based on event tags.

9.2 Integration Test (tests/integration/test_quest_integration.py)
Simulate game: start quest via dialogue, kill a goblin (emit event with correct tags), verify quest progresses, and upon completion, reward (item added to inventory) is granted.

10. Future Extensions (v2)
Quest chains (dependencies, prerequisites).

Time‑limited quests (real‑time or in‑game clock).

Branching quests (multiple paths based on player choices).

Persistent quest state across sessions (saved to database).

Dynamic / procedural quest generation (e.g., radiant quests).

Level scaling for rewards and difficulty.