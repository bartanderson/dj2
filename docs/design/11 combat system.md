Combat System – Final Design Document (v1)
1. Purpose
Provide a turn‑based combat system for single player character vs. a single enemy (multiple enemies deferred to v2).

Integrate with OG System rules (attributes, skills, hit points, damage).

Emit events for escalation (e.g., combat.attack.resolved, combat.entity.killed, combat.ended).

Be declarative – defined as an FSM (using the generic loader) and driven by data, with guards and actions implemented in Python.

2. Scope (v1)
Single player character vs. single enemy.

Turn order determined by initiative roll (once at start).

Actions: attack (melee), defend (increase defense for one turn), use item (healing potion), flee (skill check).

Enemy AI: simple – attacks the player each turn.

Death: when HP ≤ 0, combat ends.

Events: emitted for attacks, kills, combat end.

No status effects, no multiple enemies, no environmental hazards (these are v2).

3. Relationship to Other Systems
Encounter System: The encounter FSM will include a start_combat action that calls AdjudicationEngine.start_combat. When combat ends, the combat FSM emits combat.ended, and the encounter FSM (if active) listens for this event (via escalation engine or direct callback) to resume.

Event Log & Escalation: The combat FSM emits events that trigger escalation rules (e.g., reinforcements on kill).

ContextBuilder: The combat FSM provides a get_combat_context() method returning a dict with turn_order, current_turn, enemy health (visible), which the ContextBuilder uses to populate combat_context in the unified view.

Entity Resolution: The resolver will support entity_type="enemy" (for future multiple enemies) but in v1 only the single enemy exists, so no need for target resolution.

Dialogue & Quests: The event combat.entity.killed is used by the QuestManager to progress kill‑related objectives.

4. Data Model
4.1 Combat FSM Definition (JSON)
json
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
        { "from": "player_turn", "to": "resolving", "actions": ["resolve_attack", "check_victory"] },
        { "from": "enemy_turn", "to": "resolving", "actions": ["resolve_enemy_attack", "check_victory"] }
      ]
    },
    "victory": { "transitions": [{ "from": ["player_turn", "enemy_turn", "resolving"], "to": "completed" }] },
    "defeat": { "transitions": [{ "from": ["player_turn", "enemy_turn", "resolving"], "to": "completed" }] },
    "flee": { "transitions": [{ "from": "player_turn", "to": "completed", "cond": "flee_success" }] }
  }
}
4.2 Combat State (context)
The FSM’s context will contain:

python
combat_context = {
    "player": Character,
    "enemy": Enemy,                     # single enemy
    "player_defense_mod": 0,           # temporary defense from "defend" action
    "combat_log": []                   # optional
}
Initiative is rolled once at start; the player goes first if their roll >= enemy roll, else enemy goes first. The turn_order is not needed with single enemy; instead the FSM starts in player_turn or enemy_turn based on initiative.

5. API
5.1 CombatManager (integrated into AdjudicationEngine)
start_combat(session_id: str, player: Character, enemy: Enemy) -> dict
Creates a Combat FSM instance, stores it in active_fsms[session_id].

Rolls initiative: player d20 + finesse, enemy d20 + dexterity. Higher goes first.

If player wins, FSM starts in player_turn; else starts in enemy_turn. The next event transitions from initiating to the appropriate turn state based on initiative result.

Stores combat_context.

Emits combat.initiation.triggered event.

process_combat_action(session_id: str, action: str, target: Optional[EntityRef]) -> dict
Called by AdjudicationEngine.process when an active combat FSM exists.

Maps player text to combat event:

"attack" → send attack event.

"defend" → send defend event (adds temporary defense, then proceeds to enemy turn).

"use potion" → resolves item (via EntityResolver) and sends use_item event.

"flee" → send flee event.

Returns updated prompt and context.

`_resolve_attack(combat_context, attacker, target) -> dict`
Calculates hit chance: d20 + attack_bonus (strength for melee, finesse for ranged) vs. target's defense (10 + finesse + armor + temporary defense mod).

If hit, damage = weapon damage + strength modifier (for melee) or finesse/2 for ranged.

Applies damage to target HP.

Emits combat.attack.resolved with details (attacker, target, damage, hit).

If target HP ≤ 0, emits combat.entity.killed (with killed_id and killed_type).

Returns updated context.

```_check_victory(combat_context) -> bool
If enemy HP ≤ 0, emit victory event to FSM.

If player HP ≤ 0, emit defeat event.

Returns True if combat ended.

get_combat_context() -> dict
Returns a read‑only dict for the ContextBuilder: {"active": True, "player_hp": X, "enemy_hp": Y, "player_defense": 10+..., "enemy_defense": ...}.
```

5.2 Enemy AI (v1)
In enemy_turn, the FSM automatically triggers attack event. The action resolve_enemy_attack calls `_resolve_attack` with the enemy as attacker and the player as target.

5.3 Guards and Actions
Guards and actions are implemented as Python functions (registered in the engine). They are attached to the FSM via the context.

Guard flee_success – performs a skill check: d20 + character.athletics vs. DC = 10 + enemy.dexterity_modifier`. Returns True/False.

Action resolve_attack – calls `_resolve_attack`.

Action resolve_enemy_attack – same.

Action check_victory – calls `_check_victory` and sends appropriate event.

Action defend – adds +2 to player’s defense for the duration of the enemy turn (resets after).

Action use_item – applies item effect (healing), consumes item from inventory.

6. Integration
Combat is triggered by the encounter FSM or by a player attack command when no active combat exists.

Player input during combat is forwarded to the combat FSM via process_combat_action.

The combat FSM emits events that the escalation engine can react to.

Combat actions use OG System rules via dnd_data (e.g., weapon damage, armor values).

7. Performance Constraints
Combat actions <20ms.

Initiative roll <10ms.

8. Error Handling
Invalid action → error message.

Target not found (not applicable in v1) → error.

Item use fails (not in inventory) → error.

9. Testing
9.1 Unit Tests (tests/unit/test_combat_system.py)
Initiative roll and turn order (player first or enemy first).

Attack resolution (hit/miss, damage, HP change, death).

Victory/defeat detection.

Flee success/failure.

Defend action (temporary defense).

Use item (healing, inventory consumption).

9.2 Integration Test (tests/integration/test_combat_integration.py)
Simulate a complete combat: start combat, player attacks, enemy attacks, player kills enemy, combat ends. Verify events emitted and final state.

10. Future Extensions (v2)
Multiple enemies (round‑robin turns).

Status effects (poison, stun, buffs).

Environmental hazards.

Special abilities (spells, special attacks).

Ranged combat and cover.

Tactical AI (target low HP, use abilities).

Party‑based combat (multiple player characters).