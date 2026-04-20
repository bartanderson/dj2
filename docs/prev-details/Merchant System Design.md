Merchant System Design Document (Final)
1. Core Principles
Per‑character relationships – not party‑wide reputation.

Dynamic pricing – computed from personality, relationship, context.

Progressive visibility – items appear based on trust, affinity, quests, etc.

AI‑driven interaction – all buy/sell/steal/haggle actions via chat, not UI buttons.

DM overrides – allow narrative flexibility (elastic inventory, forced reveals, etc.).

Integration with 7‑phase engine – each merchant action flows through INPUT → INTERPRETATION → AUTHORITY → MUTATION → CONSEQUENCE → PERSISTENCE → VIEW.

2. Data Models
2.1 Merchant (Static)
python
class Merchant:
    id: str
    name: str
    location: str               # region, settlement, or "traveling"
    personality: MerchantPersonality
    constraints: MerchantConstraints
    inventory: List[MerchantItem]
    faction: Optional[str]
    schedule: Optional[MerchantSchedule]
    global_bias: int            # baseline attitude toward strangers (-5..5)
2.2 MerchantPersonality
python
class MerchantPersonality:
    greed: int          # markup multiplier (0..10)
    paranoia: int       # suspicion of theft (0..10)
    honor: int          # fairness (0..10)
    sociability: int    # willingness to talk/reveal (0..10)
    risk_tolerance: int # willingness to deal with shady players (0..10)
2.3 MerchantConstraints
python
class MerchantConstraints:
    max_discount: float        # e.g., 0.5 (50% off max)
    max_markup: float          # e.g., 2.0 (200% of base)
    refuses_if_hostile: bool
    guards_present: bool
    barter_allowed: bool
    credit_allowed: bool
2.4 MerchantRelationship (Per Character)
python
class MerchantRelationship:
    merchant_id: str
    character_id: str
    affinity: int          # -10..10 (liking)
    trust: int             # -10..10 (willingness to reveal/credit)
    fear: int              # -10..10 (affects pricing, compliance)
    respect: int           # -10..10 (heroic actions, status)
    last_interaction: datetime
    flags: Set[str]        # e.g., "saved_life", "caught_stealing"
2.5 MerchantItem
python
class MerchantItem:
    id: str
    item: InventoryItem    # reference to actual item (name, cost, etc.)
    quantity: Optional[int]  # None = abstract/elastic (DM can adjust)
    base_price: int
    steal_dc: int
    barter_value: int
    visibility_rules: List[VisibilityRule]
    tags: Set[str]         # e.g., "rare", "illegal", "quest_item"
2.6 VisibilityRule
python
class VisibilityRule:
    type: Literal["affinity", "trust", "fear", "respect", "flag", "quest"]
    threshold: Union[int, str]   # e.g., 5, "saved_life"
    hint: Optional[str]          # what the merchant says if close
2.7 Party Overlay (Optional)
python
class PartyMerchantState:
    merchant_id: str
    shared_flags: Set[str]    # e.g., "party_caught_stealing"
    heat_level: int           # how alert merchant is to the group
    last_visit: datetime
3. Pricing Engine
Dynamic computation – no stored current_price.

python
```def compute_price(
    item: MerchantItem,
    merchant: Merchant,
    rel: MerchantRelationship,
    context: dict
) -> int:
    price = item.base_price
    # Personality
    price *= (1 + merchant.personality.greed * 0.05)
    # Relationship axes
    price *= (1 - rel.affinity * 0.03)
    price *= (1 - rel.trust * 0.02)
    price *= (1 + rel.fear * 0.04)
    # Context (e.g., urgency, scarcity, time of day)
    if context.get('desperate'):
        price *= 1.25
    if context.get('scarcity'):
        price *= 1.1
    # Clamp by constraints
    max_price = item.base_price * (1 + merchant.constraints.max_markup)
    min_price = item.base_price * (1 - merchant.constraints.max_discount)
    return max(min_price, min(price, max_price))
```
4. Phase Integration (GameEngine)
Merchant actions flow through the 7 phases. The AI DM triggers them via tool calls.

4.1 INPUT Phase
Player sends a message (e.g., “I want to buy the shortsword”).

`GameEngine._execute_input_phase` wraps it as player_text.

4.2 INTERPRETATION Phase
DMChatHandler uses AI to interpret intent. If intent is a merchant action, it returns a structured action:

json
{
  "intent": "merchant_action",
  "action": "buy",
  "parameters": {"item_id": "shortsword_123", "merchant_id": "grom"}
}
4.3 AUTHORITY Phase
Validate the action:

Is the merchant present?

Does the character have enough gold? (for buy)

Does the merchant have the item? (respect visibility rules)

Is the action allowed by constraints? (e.g., barter allowed)

For haggle/steal, perform skill checks (Persuasion, Stealth) using the AuthoritySystem.

Return ruling: {"valid": bool, "price": int, "message": str, ...}

4.4 MUTATION Phase
Apply state changes:

For buy: deduct gold, add item to character inventory.

For sell: add gold, remove item.

For steal: if successful, add item; update relationship (fear, trust).

For haggle: modify temporary price (stored in context, not permanent).

Update MerchantRelationship (affinity, trust, fear, flags).

Store changes in GameContext phase data.

4.5 CONSEQUENCE Phase
Generate narration (AI or template) describing the outcome.

Update global events (e.g., if theft fails, guards may be called).

Emit SocketIO events if other clients need to see inventory changes.

Optionally update UnifiedContext.mood and UnifiedContext.event (e.g., mood = "tense" on theft detection).

4.6 PERSISTENCE Phase
Save updated MerchantRelationship to database.

Save character inventory and gold changes.

Save any merchant state changes (e.g., quantity decreased, or DM override flags).

4.7 VIEW Phase
Prepare UI updates:

Refresh inventory tab (HTMX) to show new items/gold.

Refresh merchant visible items (if in subhex view).

Return narrative for chat.

5. AI DM Tool Functions
Registered in WorldController.tool_registry:

merchant_buy(merchant_id, item_id, character_id)

merchant_sell(merchant_id, item_id, character_id)

merchant_haggle(merchant_id, item_id, offered_price)

merchant_steal(merchant_id, item_id, character_id, stealth_roll)

merchant_reveal(merchant_id, character_id)

merchant_barter(merchant_id, offered_item_id, desired_item_id)

Each tool function calls into the GameEngine phases (or directly into the mutation phase) to ensure consistency.

6. DM Override Layer
Explicit hooks for the AI DM to override normal behavior:

python
class DMOverride:
    force_inventory: Optional[List[MerchantItem]]
    force_price: Optional[int]
    auto_reveal: Optional[List[str]]  # item ids
    narrative_event: Optional[str]
These can be set via a special command or AI internal reasoning. They override the computed values during authority phase.

7. UI Integration
Inventory tab – read‑only list of character items and gold. No buy/sell/steal buttons.

Merchant interaction – when in a settlement or encountering a traveling merchant, the player types “I want to buy something” or “Show me your wares”. The AI DM will respond and, if appropriate, call merchant_reveal and display the visible items (in chat or a temporary modal). The player then types “I buy the shortsword” to complete the transaction.

Optional merchant modal – may be added later to show visible items with buy buttons, but that would duplicate the AI flow. We’ll start with AI‑only.

8. State Persistence
MerchantRelationship stored in CampaignState.merchant_relationships (dict keyed by (merchant_id, character_id)).

PartyMerchantState stored optionally in CampaignState.party_merchant_state (keyed by merchant_id).

Merchant inventory is static (from 05_equipment.json) except for quantity changes (which are stored per merchant in CampaignState.merchant_inventory_state).

9. Event Hooks
On affinity change: if crosses a threshold, trigger AI narrative (“The merchant seems friendlier now.”)

On trust change: may reveal new items (visibility rules re‑evaluated).

On fear change: may affect pricing or willingness to negotiate.

On steal failure: may trigger a global event (guards summoned, faction reputation change).

10. Implementation Phases
Data models – add Merchant, MerchantRelationship, etc. to world/campaign.py.

Pricing engine – implement compute_price and unit tests.

Phase integration – extend GameEngine to handle merchant actions (buy/sell first).

Tool functions – register tools for AI DM.

UI – read‑only inventory tab, merchant item display (optional).

DM overrides – implement hooks.

Event hooks – add triggers for affinity/trust changes.

11. Open Questions
How to represent traveling merchants? They appear in hexes based on random encounter or DM placement. Their location is “traveling” and they may not have a fixed shop.

Should merchants have a limited stock that replenishes over time? (We can add a restock_interval and last_restock timestamp.)

How to handle barter? The player offers an item; the merchant evaluates its barter value (maybe 0.5× price) and accepts/rejects.

These will be addressed during implementation.

12. UnifiedContext Integration (Simplified)
Merchant interactions may temporarily set UnifiedContext.mood and UnifiedContext.event (e.g., on theft detection, mood = "tense", event = "theft_alert"). Long‑term effects are already captured by MerchantRelationship axes. No additional specialized fields are needed.