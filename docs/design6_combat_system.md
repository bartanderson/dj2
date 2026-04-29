Combat System – Design Document
1. Purpose
Provide a turn‑based combat system that supports player vs. one or more enemies.

Integrate with OG System rules (attributes, skills, hit points, damage, etc.).

Emit events for escalation (e.g., combat.entity.killed, combat.turn.ended).

Be declarative – defined as an FSM (using the generic loader) and driven by data.

2. Core Concepts
Combat FSM – manages states: initiating, player_turn, enemy_turn, resolving, completed.

Participants – player character(s) and enemy creatures.

Turn order – determined by initiative roll (or fixed sequence).

Actions – attack, defend, use item, flee.

Guards – hit chance, damage calculation, death check.

Event emission – every significant action emits an event for the escalation engine.

3. Combat Flow (State Machine)
Initiating – triggered by an event (e.g., combat.initiation.triggered). Rolls initiative, sets turn order.

Player Turn – player can attack, defend, use item, flee. After action, either resolve enemy turn or check victory.

Enemy Turn – enemy AI chooses action (attack, special move, etc.). After action, back to player turn or check victory.

Resolving – intermediate state for processing actions (damage, healing) and emitting events.

Completed – all enemies defeated or player(s) defeated. Emit combat.ended.

4. FSM Definition (JSON)
```json
{
  "name": "CombatFSM",
  "states": [
    { "name": "initiating", "initial": true, "prompt": "Combat begins!" },
    { "name": "player_turn", "prompt": "Your turn." },
    { "name": "enemy_turn", "prompt": "Enemy attacks!" },
    { "name": "resolving", "prompt": "Resolving action..." },
    { "name": "completed", "final": true, "prompt": "Combat ended." }
  ],
  "events": {
    "next": { "transitions": [{ "from": "initiating", "to": "player_turn" }] },
    "attack": {
      "transitions": [
        { "from": "player_turn", "to": "resolving", "actions": ["player_attack"] },
        { "from": "resolving", "to": "enemy_turn", "cond": "combat_not_ended" },
        { "from": "enemy_turn", "to": "resolving", "actions": ["enemy_attack"] },
        { "from": "resolving", "to": "player_turn", "cond": "combat_not_ended" }
      ]
    },
    "enemy_defeated": { "transitions": [{ "from": "*", "to": "completed", "cond": "all_enemies_defeated" }] },
    "player_defeated": { "transitions": [{ "from": "*", "to": "completed", "cond": "all_players_defeated" }] },
    "flee": { "transitions": [{ "from": "player_turn", "to": "completed", "cond": "flee_success" }] }
  }
}
```
5. Guards and Actions
Guards and actions are implemented as Python functions (registered in the engine). Examples:

Guards
combat_not_ended – returns True if both sides still have living participants.

all_enemies_defeated – returns True if enemy HP <= 0.

all_players_defeated – returns True if all player characters HP <= 0.

flee_success – performs a skill check (e.g., Athletics) vs. enemy speed; returns True if success.

Actions
player_attack – calculate hit chance, damage, reduce enemy HP; emit combat.attack.resolved; if enemy dies, emit combat.entity.killed and call enemy_defeated event.

enemy_attack – similarly.

start_combat – initialises participant lists, rolls initiative, sets turn order.

end_combat – emits final events, cleans up.

6. Integration with Existing Systems
Combat is triggered by an event (e.g., from encounter FSM, or from a player attack command). The AdjudicationEngine will create a CombatFSM instance and store it in active_fsms.

Player input during combat (e.g., attack, flee) is forwarded to the combat FSM.

The combat FSM emits events that the escalation engine can react to (e.g., reinforcements, reputation changes).

Combat actions use OG System rules via the dnd_data module (skill checks, damage, etc.).

7. Multiple Enemies and Party Support
The combat FSM will maintain a list of participants (player characters and enemies).

Turn order will be a round‑robin based on initiative order.

Actions will target a specific enemy or ally (via entity resolution).

The FSM may need to be extended with hierarchical states for targeting, but that can be added later.

8. Testing
Unit tests for guards (hit chance, flee success) and actions (damage, death).

Integration test that simulates a full combat: start, attack, defeat enemy, end.