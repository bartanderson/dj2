Quest System – Design Document
1. Purpose
Allow state‑driven quest management (inactive, active, completed, failed, abandoned).

Support dependencies (quest must be active, certain items possessed, previous quest stage complete).

Trigger actions on quest acceptance, progression, completion, or failure (e.g., spawn NPCs, give items, change faction standing, emit events).

Integrate with dialogue system (NPC gives quest, updates via conversation) and event system (e.g., kill monster triggers quest progress).

2. Quest Structure
A quest is defined as an FSM (states: inactive, active, completed, failed, abandoned). Transitions are triggered by events (e.g., accept, progress, complete, fail, abandon). Guards check prerequisites (e.g., has_item, reputation > X). Actions execute side effects (e.g., give_item, spawn_monster, emit_event).

3. Definition Format (JSON)
json
{
  "name": "Goblin Menace",
  "states": [
    { "name": "inactive", "initial": true, "prompt": "Not yet started." },
    { "name": "active", "prompt": "Active quest." },
    { "name": "completed", "final": true, "prompt": "Completed!" },
    { "name": "failed", "final": true, "prompt": "Failed." }
  ],
  "events": {
    "accept": {
      "transitions": [
        { "from": "inactive", "to": "active", "actions": ["log_quest_start"] }
      ]
    },
    "progress": {
      "transitions": [
        { "from": "active", "to": "completed", "cond": "goblins_defeated", "actions": ["give_reward", "emit_quest_completed"] }
      ]
    }
  }
}
4. Integration
Quest definitions are loaded by the AdjudicationEngine when needed (e.g., when a quest‑giver NPC is talked to).

The engine maintains a dictionary of active quest instances per character/session.

Events emitted by combat, economy, etc., can trigger quest progress events (e.g., kill_goblin event → call quest.progress).

Dialogue actions can accept quests and show quest status.

5. Testing
Unit tests for state transitions, guards, actions.

Integration test: simulate accepting a quest, completing its objective, and verifying the reward.

