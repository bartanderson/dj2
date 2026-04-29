Entity Resolution – Final Design Document (v1)
1. Purpose
Map player natural language phrases (e.g., "potion", "the sword", "Grom's wooden table") to actual game objects (items, NPCs, locations, skills, spells, etc.).

Provide a fast, deterministic lookup that works alongside the LLM‑based intent parser.

Handle synonyms, misspellings, and embedding‑based semantic similarity (replaces fuzzy matching). Contextual inference (e.g., "it", "that") is deferred to v2.

2. Inputs
Resolved intent fields – frame.item and frame.target (strings) from IntentParser. The resolver does not operate on raw sentences.

Current context:

current_location (Location object)

merchant (Merchant object, if in trade)

character (player character, with inventory)

active_quests (list of quest objects)

conversation_history (last few messages – reserved for v2 contextual inference)

Entity type hint – optional, e.g., "item", "npc", "location", "skill", "spell", "quest". Used to restrict search domains.

3. Output
Resolved entity object (or None if not found).

Confidence score (optional, for logging). Not used in v1 but may be added later.

4. Resolution Strategy (multi‑stage, ordered)
The resolver attempts stages in order, stopping on first success.

4.1 Stage 1 – Exact match (case‑insensitive)
Compare the input string (lowercased) against the canonical names of entities in the currently loaded index(es) for the given type.

Example: "healing potion" matches an item with name "Healing Potion".

4.2 Stage 2 – Synonym mapping
Apply a hard‑coded dictionary of aliases to the input string, then perform an exact match.

Example: "{'potion': 'Healing Potion'}" → "healing potion" → exact match.

Synonyms are global (not context‑dependent). For v1, synonyms are defined as a class variable.

4.3 Stage 3 – Embedding‑based similarity (replaces fuzzy match)
Pre‑compute embeddings for all entity names in the current index when the index is loaded (see §5).

For the input phrase, compute its embedding and compute cosine similarity against all stored embeddings.

Use a threshold (default 0.8). If the highest similarity >= threshold, return the corresponding entity. If multiple entities exceed the threshold, choose the highest.

Performance note: Embedding computation for a single phrase is ~10ms on a typical CPU. Index embedding computation is done once per load (e.g., when merchant inventory is loaded).

4.3.1 Embedding Index Lifecycle
Each index (merchant items, character inventory, location NPCs, etc.) stores a list of (entity, embedding) tuples.

The embedding for each entity is computed at index creation time (not at resolve time).

The model is a singleton (same as used by IntentManager) to avoid reloading.

4.4 Stage 4 – Fallback
Return None. The caller will generate a clarification prompt (e.g., "I don't know what you mean by '...'. Please rephrase.").

Note: Contextual inference (“it”, “that”, “the first one”) is not included in v1. It will be added in v2.

5. Data Sources and Index Lifecycle
The resolver maintains separate indices for different entity types. Each index is a dictionary mapping normalized names to entity objects and a parallel list of embeddings (computed once).

Entity Type	Index Populated By	When Cleared / Repopulated
Items (trade)	load_merchant_items(merchant)	At the start of each buy/sell interaction (clears previous item index).
Items (sell/barter)	load_character_inventory(character)	At the start of each sell/barter interaction.
NPCs	load_location_npcs(location)	Every time WorldController.current_location changes (clears old NPC index).
Locations	load_discovered_locations(world_map)	Once at game start; not changed during play (discovery adds but not removed).
Skills	load_skills(dnd_data)	Once at game start.
Spells	load_spells(dnd_data)	Once at game start.
Quests	load_active_quests(quest_list)	Every time active quests change (start, complete, fail).
The resolver does not keep a permanent global index; it rebuilds indices as needed.

5.1 API for Index Loading
```python
def load_merchant_items(self, merchant: Merchant) -> None:
    """Clear current item index, populate with merchant's inventory, and pre-compute embeddings."""
    self.item_index = {}
    self.item_embeddings = []
    for item in merchant.inventory:
        name = item.name.lower()
        self.item_index[name] = item
        self.item_embeddings.append((item, self._get_embedding(name)))

def load_character_inventory(self, character: Character) -> None:
    """Same pattern, but for character inventory."""

def load_location_npcs(self, location: Location) -> None:
    """Clear NPC index and populate with NPCs in the given location."""

def load_discovered_locations(self, world_map: WorldMap) -> None:
    """Load all discovered locations (called once)."""

def load_skills(self, skill_list: List[str]) -> None:
    """Load skill name → skill object (called once)."""

def load_spells(self, spell_list: List[str]) -> None:
    """Load spell name → spell object (called once)."""

def load_active_quests(self, quest_list: List[Quest]) -> None:
    """Refresh quest index (called when active quests change)."""
```
5.2 Helper Methods (private)
```
_get_embedding(text: str) -> List[float] – returns embedding vector using the singleton model.

_exact_match(term, type_filter) – search current indices.

_synonym_match(term, type_filter) – use internal synonym dict.

_embedding_match(term, type_filter) – compute term embedding and compare to stored embeddings.

_contextual_match(raw_text, context) – v2 only (stub for now).
```

6. Type Filtering
Each resolve call may include an optional entity_type parameter (e.g., "item").

If provided, the resolver only searches indices that belong to that type. If multiple indices match the type (e.g., items could be from merchant or character), all such indices are searched in order of most recent (merchant before character for buy, character before merchant for sell – determined by caller, not resolver).

If no type is provided, the resolver searches all currently loaded indices in a fixed order: items (if any), NPCs, locations, skills, spells, quests.

7. Integration with IntentParser
The IntentFrame produced by the IntentParser already contains item and target fields (strings).

The resolver is called after the IntentParser, with those fields as input.

Example flow:

Player says: buy potion
IntentParser produces IntentFrame(action="buy", item="potion", ...)
`AdjudicationEngine._handle_buy` calls `self.entity_resolver.resolve(item, entity_type="item")`
Resolver returns the MerchantItem object or None.
8. Performance Constraints
resolve() must complete in <15ms for typical input (including embedding computation). Because the phrase embedding is computed each time, and index embeddings are pre‑computed.

Loading a merchant inventory (≤50 items) must be <50ms (includes embedding all item names). Acceptable because it happens only when entering a trade.

Loading location NPCs (≤20 NPCs) <20ms.

9. Error Handling
If no entity found, return None.

If a synonym points to a non‑existent canonical name, log a warning and continue (skip that synonym).

If the embedding model fails (e.g., out of memory), log error and fallback to exact match + synonym only (skip embedding stage).

If difflib is not used (replaced by embedding), no fallback needed.

10. Testing
10.1 Unit Tests (tests/unit/test_entity_resolver.py)
Exact match on item, NPC, location, skill, spell, quest.

Synonym mapping (e.g., "potion" → "Healing Potion").

Embedding similarity: test that "healing potion" matches "Healing Potion" with similarity above threshold. Test that a nonsense term returns None.

Type filtering: request "item" only, ensure location names are not returned.

Index lifecycle: load merchant items, then load character inventory – verify that the index is replaced, not merged.

Empty indices (return None).

Performance test: measure that resolve() finishes within 15ms.

10.2 Integration Test (tests/integration/test_entity_resolver_integration.py)
Create a mock WorldController with a merchant, a character, a location with NPCs, and discovered locations.

Run a series of resolve calls that simulate actual game operations (buy, sell, look at NPC, travel to location).

Verify that the correct entity objects are returned.

11. Future Extensions (v2)
Contextual inference for “it”, “that”, “the first one”, “the last one” (using conversation history).

Embedding‑based semantic matching for phrases not captured by synonyms (already in v1).

Learning from player corrections (e.g., “no, the red potion”).

Dynamic synonym loading from configuration files.

Support for possessive references (“his sword” → resolve to owner’s last mentioned item).

Async embedding pre‑computing to reduce load time.