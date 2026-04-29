Dialogue System – Design Document
1. Purpose
Enable branching conversations with NPCs where player choices affect story, quests, and world state.

Support conditions (skill checks, reputation, flags, inventory) and actions (give items, start quests, modify faction).

Represent dialogue as a state machine (FSM) that can be defined declaratively (JSON/YAML) and loaded by the generic FSM engine.

2. Inputs
Player utterance (raw text) – classified as choosing a dialogue option (by number, keyword, or direct text match).

Current game state – character skills, faction standing, active quests, inventory, flags.

Dialogue definition – from a dialogue.json file.

3. Outputs
NPC response (text).

Possible actions (e.g., give quest, modify reputation, add item to inventory).

New dialogue state (next node) or termination.

4. Dialogue Structure (State Machine Model)
Each state represents a dialogue node (NPC line, description, possible responses).

Transitions are triggered by player choice (event choose_1, choose_2, etc., or a command like ask_about).

Guards determine if a choice is available (e.g., has_item('sword'), skill_check('persuasion') >= 15).

Actions execute when a choice is selected (e.g., give_quest('find_goblins'), remove_item('sword'), modify_reputation('guild', +5)).

Terminal states end the conversation.

5. Definition Format (JSON)
json
{
  "name": "Greeting",
  "states": {
    "start": {
      "text": "Welcome, adventurer. What do you need?",
      "choices": [
        { "text": "I'd like to buy something.", "next": "shop", "conditions": [] },
        { "text": "Tell me about goblins.", "next": "goblin_info", "conditions": [] },
        { "text": "Goodbye.", "next": "goodbye", "conditions": [] }
      ]
    },
    "shop": {
      "text": "I have fine wares. Take a look.",
      "actions": ["open_merchant_inventory"],
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
6. Integration
The dialogue system is an FSM (loaded by GenericFSM with custom guards/actions).

When the player says talk or speak to X, the AdjudicationEngine loads the appropriate dialogue JSON (based on NPC) and stores the FSM in active_fsms.

Player input (choice number or keyword) is sent as events (e.g., choose_1).

Actions are registered in the action registry (e.g., open_merchant_inventory calls the engine's `_start_merchant_trade`).

Dialogue actions can emit events (e.g., dialogue.choice.selected) for escalation.

7. Testing
Unit tests for condition evaluation and action execution.

Integration test: load a dialogue, simulate player choices, verify state transitions and side effects.

