Dialogue System – Design Document (v1)
1. Purpose
Enable branching conversations with NPCs where player choices affect story, quests, and world state.

Support conditions (skill checks, reputation, flags, inventory) and actions (give items, start quests, modify faction).

Represent dialogue as a state machine (FSM) that can be defined declaratively (JSON/YAML) and loaded by the generic FSM engine.

Integrate with Entity Resolution (to map player‑typed responses to choices) and Event Log (to emit dialogue‑related events).

2. Core Concepts
Dialogue FSM – each node (state) contains NPC line, list of player choices, possible actions, and next state.

Choices – can be selected by number (1,2,3) or by keyword (exact match or resolved via Entity Resolution).

Conditions – guard statements that determine if a choice is available (e.g., has_item('sword'), skill_check('persuasion') >= 15).

Actions – executed when a choice is selected (e.g., give_quest('find_goblins'), modify_reputation('guild', +5)).

Terminal states – end the conversation.

3. Data Model
3.1 Dialogue Definition (JSON)
```json
{
  "name": "Greeting",
  "initial_state": "start",
  "states": {
    "start": {
      "text": "Welcome, adventurer. What do you need?",
      "choices": [
        { "text": "I'd like to buy something.", "next": "shop", "conditions": [], "actions": [] },
        { "text": "Tell me about goblins.", "next": "goblin_info", "conditions": [], "actions": [] },
        { "text": "Goodbye.", "next": "goodbye", "conditions": [], "actions": [] }
      ]
    },
    "shop": {
      "text": "I have fine wares. Take a look.",
      "actions": [{ "name": "open_merchant_inventory", "params": {} }],
      "next": "start"
    },
    "goblin_info": {
      "text": "Goblins are weak but cunning. They live in caves.",
      "next": "start"
    },
    "goodbye": {
      "text": "Farewell!",
      "final": true
    }
  }
}
```
3.2 Condition Evaluation Context
character – the current player character (has attributes, skills, inventory).

world – read‑only facade with methods: get_faction_standing(faction), get_quest_state(quest_id), get_time_of_day(), etc.

event – (null for dialogue conditions, but available for future use).

Example condition: "character.has_item('shortsword')" or "world.get_faction_standing('guild') > 10".

3.3 Internal Representation (when loaded)
The dialogue definition is converted to an FSM using GenericFSM.

Each state’s choices become transitions triggered by events (choose_1, choose_2, …, or choose_by_text).

Actions are mapped to registered functions (same mechanism as economy/combat builtins).

4. API
4.1 DialogueManager (or integrated into AdjudicationEngine)
start_dialogue(session_id: str, npc_id: str, dialogue_def_path: str) -> dict

process_dialogue_choice(...) – after choice is processed, emits dialogue.choice.selected event with:

  choice_index (int)

  choice_text (str)

  npc_id (str)

  next_state (str)

Loads dialogue JSON, creates a GenericFSM instance, stores in active_fsms[session_id].

Returns the first prompt (text of initial state) and the list of choices.

process_dialogue_choice(session_id: str, choice_text_or_index: Union[int, str]) -> dict

Resolves choice to an event (e.g., choose_1 or choose_by_text).

Sends event to FSM.

Returns new response (NPC line) and list of choices (or terminal flag).

4.2 Action Registry (shared with other systems)
register_dialogue_action(name: str, func: Callable[[dict], None]) – same pattern as escalation actions.

Example actions:

open_merchant_inventory – calls `AdjudicationEngine._start_merchant_trade`

give_quest(quest_id) – starts a quest

modify_reputation(faction, delta)

add_item(item_id)

4.3 Condition Evaluation
Use the same simpleeval‑based evaluator as the escalation engine. The context passed to simpleeval includes:

character (the player character object, with methods like has_item(item_id) exposed as functions)

world (a dict of convenience functions)

quests (for completeness)

Example: character.has_item('shortsword') maps to a callable has_item on the character object.

5. Integration
When the player types talk or speak to X, the AdjudicationEngine routes to dialogue system.

The dialogue FSM is stored in active_fsms alongside trade/combat/encounter FSMs.

The process method’s active FSM handling already works for dialogue (sends events to the FSM). No special routing needed.

Dialogue actions emit events (e.g., dialogue.choice.selected, dialogue.quest_given) which trigger escalation.

For v1, player must select a choice by typing the number (e.g., 1, 2). No free‑text matching.

The IntentParser will detect a single digit and pass it as event choose_1, etc.

If the player types something else, the system replies: "Please type the number of your choice."

6. Performance Constraints
Loading a dialogue JSON: <100ms.

Processing a choice: <10ms.

7. Error Handling
Invalid JSON → load fails (game startup error).

Unknown action name → logged; action skipped.

Choice index out of range → return error message.

Condition evaluation error → treat as false, choice not shown.

8. Testing
8.1 Unit Tests
Load a dialogue, verify initial state and prompt.

For each choice, simulate the choose_N event, verify state transition and any actions.

Mock condition evaluation (by patching the condition evaluator or the world object) to test conditional choice availability.

Mock action functions to verify they are called with correct parameters.

8.2 Integration Test
Start a dialogue with a mock engine that has a character with specific inventory and skill values.

Make a sequence of numeric choices, verify final state and that appropriate actions (e.g., open_merchant_inventory) were invoked.

Check that dialogue.choice.selected events are emitted.

9. Future Extensions (v2)
Free‑text choice matching (using Entity Resolution).

Dynamic choice generation (e.g., list of available spells).

Dialogue variables (memory).

Branching based on player class/race/background.

Dialogue trees with dynamic variables (e.g., NPC memory of previous conversations).

Rich condition language (e.g., quest_active, reputation > 10).

Voice acting triggers.