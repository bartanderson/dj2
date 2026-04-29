Entity Resolution – Design Document
1. Purpose
Map player natural language phrases (e.g., "potion", "the sword", "Grom's wooden table") to actual game objects (items, NPCs, locations, skills, etc.).

Provide a fast, deterministic lookup that works alongside the LLM‑based intent parser.

Handle synonyms, misspellings, and contextual references (e.g., "that sword" referring to the last mentioned item).

2. Inputs
Player utterance (raw string) – after initial NLU parsing, but before intent classification.

Current context: current location, merchant inventory, character inventory, active quests, recent conversation.

Entity resolution registry – pre‑loaded dictionaries for items, NPCs, locations, skills, spells, etc.

3. Output
Resolved entity (object reference) or None.

Confidence score (optional, for logging).

4. Strategy (multi‑stage)
Exact match – case‑insensitive string comparison against known entity names (e.g., "Healing Potion").

Synonym mapping – hard‑coded aliases (e.g., "potion" → "Healing Potion", "sword" → "Shortsword").

Fuzzy match – using difflib.get_close_matches with a cutoff (e.g., 0.8) to handle typos.

Contextual inference – if the player says "it" or "that", resolve to the last mentioned entity of the appropriate type (requires conversation history tracking).

Fallback – return None and generate a clarification prompt.

5. Data Sources
Items: from merchant inventory (current location) and character inventory (for sell/barter). Also from global item database (dnd_data).

NPCs: from current location and known factions.

Locations: from world map (discovered locations).

Skills: from dnd_data skill list.

Spells: from dnd_data spell list.

Quest objects: from active quests.

6. Integration
Called by `AdjudicationEngine._handle_transaction` and `_handle_look` before using fuzzy matching.

Also used by dialogue system when the player refers to an item, NPC, or location.

Resolved entities become part of the IntentFrame (e.g., item, target).

7. Example
Player: buy potion

exact_match("potion") fails.

synonym_map["potion"] → "Healing Potion".

Exact match on "Healing Potion" succeeds.

Return item object.

8. Testing
Unit tests for each resolution stage.

Integration test: given a sentence and a context, verify that the correct entity is resolved.