What actually drives outcomes is relationship + context + leverage, and most of that is per actor, not per merchant.

Below is a structured teardown of issues and a revised model that aligns with how play actually unfolds at the table (and how your AI DM would need to reason).

1) Core Design Problems
1.1 Misplaced Reputation Axis

Current flaw:

reputation: int  # -10 to +10
relationship: str

This treats reputation as a property of the merchant, which implies:

All players are treated the same
Social context is flattened into a number
Relationship is redundant / underspecified

Reality:

A merchant doesn’t have “a reputation with you”—they have:
Memory of interactions
Bias (appearance, race, faction, rumors)
Emotional state (recent theft, rescue, betrayal)
Two party members can get radically different prices simultaneously
1.2 Party vs Individual State Conflict

You introduced:

party_merchant_state = {
    merchant_id: { ... }
}

This contradicts your stated goal:

“It is per adventurer.”

Right now:

Theft is tracked at party level → destroys stealth gameplay
Reputation is shared → eliminates role specialization (face vs brute)
Haggle attempts are global → removes negotiation tactics
1.3 Price Model is Too Static
base_price
current_price

Problems:

Implies price is precomputed and stored
Doesn’t encode why the price changes
No hooks for dynamic conditions (urgency, scarcity, mood)
1.4 Visibility System is Underpowered
visibility: str
visibility_conditions: Dict
revealed: bool

Issues:

Binary reveal doesn’t capture progressive disclosure
Doesn’t support “soft hints” (e.g., “I might have something… for the right person”)
Conditions are passive, not evaluated in context
1.5 Inventory is Too Deterministic
quantity: int

This is dangerous for gameplay:

Removes illusion flexibility
Prevents DM from “finding one more item” when needed
Encourages players to meta-exploit stock
1.6 No Concept of Merchant Intent

You’re missing:

Risk tolerance (will they sell stolen goods?)
Greed vs honor
Fear (guards nearby? recent theft?)

Without this, behavior becomes mechanical instead of narrative.

1.7 No Temporal Dynamics

You track:

last_interaction

But you don’t model:

Memory decay
Mood carryover
Inventory refresh cycles
Market shifts
2) Revised Conceptual Model
2.1 Split the Axes Properly
Merchant = Static + Personality + Constraints
Relationship = Per Character
Transaction Context = Per Interaction
3) Proposed Data Model
3.1 Merchant (Reworked)
class Merchant:
    id: str
    name: str
    location: str  # region, settlement, traveling

    inventory: List[MerchantItem]

    personality: MerchantPersonality
    constraints: MerchantConstraints

    faction: Optional[str]
    schedule: Optional[MerchantSchedule]

    global_bias: int  # baseline attitude toward strangers (-5 to +5)
3.2 MerchantPersonality (NEW)

This is what actually drives behavior.

class MerchantPersonality:
    greed: int          # affects markup
    paranoia: int       # affects theft suspicion
    honor: int          # affects fairness
    sociability: int    # willingness to talk/reveal
    risk_tolerance: int # deals with shady players
3.3 MerchantConstraints (NEW)

Hard limits the DM enforces.

class MerchantConstraints:
    max_discount: float
    max_markup: float
    refuses_if_hostile: bool
    guards_present: bool
    barter_allowed: bool
    credit_allowed: bool
3.4 Character-Specific Relationship (CRITICAL FIX)
class MerchantRelationship:
    merchant_id: str
    character_id: str

    affinity: int       # -10 to +10 (core axis)
    trust: int          # willingness to reveal / extend credit
    fear: int           # affects pricing, compliance
    respect: int        # heroic actions, status

    last_interaction: datetime

    flags: Set[str]     # "saved_life", "caught_stealing", etc.

This replaces:

merchant.reputation
party_merchant_state.reputation
3.5 Party Overlay (Optional, Not Primary)
class PartyMerchantState:
    merchant_id: str

    shared_flags: Set[str]   # "party_caught_stealing"
    heat_level: int          # how alert merchant is to the group

    last_visit: datetime

Use sparingly—this is ambient tension, not identity.

3.6 MerchantItem (Reworked)
class MerchantItem:
    id: str
    item: InventoryItem

    quantity: Optional[int]  # None = abstract/elastic

    base_price: int

    visibility_rules: List[VisibilityRule]

    steal_dc: int
    barter_value: int

    tags: Set[str]  # "rare", "illegal", "quest_item"
3.7 VisibilityRule (Replace current system)
class VisibilityRule:
    type: str  # "affinity", "trust", "quest", "flag"
    threshold: int | str
    hint: Optional[str]  # what the merchant says if close

This allows:

Partial reveal
Narrative hooks
AI DM prompting
4) Pricing Engine (THIS IS WHERE PLAYABILITY LIVES)

Remove current_price.

Replace with:

def compute_price(item, merchant, relationship, context) -> int:
Inputs:
Merchant personality
Relationship (affinity, trust, fear)
Context (urgency, scarcity, time of day)
Player behavior (haggle, intimidation, charm)
Example Model:
```
price = base_price

price *= (1 + merchant.personality.greed * 0.05)
price *= (1 - relationship.affinity * 0.03)
price *= (1 - relationship.trust * 0.02)
price *= (1 + relationship.fear * 0.04)

if context.is_desperate:
    price *= 1.25
```

Now price is:

Explainable
Adjustable
Narrative-driven
5) Critical Gameplay Improvements
5.1 Multi-Character Interaction
Face character negotiates
Rogue steals
Warrior intimidates

Each modifies different axes:

Affinity
Fear
Trust
5.2 Soft Failure Instead of Binary Failure

Instead of:

“Item not visible”

You get:

“I might have something… but not for you.”

This feeds your AI DM narrative layer.

5.3 Elastic Inventory (Important)

Replace rigid:

quantity: int

With:

Optional quantity
DM override capability

This allows:

“Last one” tension
“Actually I found another…” moments
5.4 Theft System Becomes Meaningful

Because now:

Theft affects trust + fear
Not just a flag

Example:

Clean theft → trust drops slightly
Failed theft → fear spikes, guards called
5.5 Memory Decay (Add This)
```def decay_relationship(rel, days_passed):
    rel.affinity *= 0.98 ** days_passed
    rel.fear *= 0.95 ** days_passed
```

Prevents permanent lock-in states.

6) DM Override Layer (You Explicitly Wanted This)

Add a formal hook:

class DMOverride:
    force_inventory: Optional[List[MerchantItem]]
    force_price: Optional[int]
    auto_reveal: Optional[List[item_id]]
    narrative_event: Optional[str]

This supports:

“Sword under blanket”
Sudden rare item
Scripted encounters
7) What This Fixes
Problem	Fix
Merchant reputation incorrect	Per-character relationship model
Party flattening	Individual + optional party overlay
Static pricing	Dynamic compute function
Binary visibility	Rule-based progressive reveal
Rigid inventory	Elastic + DM override
No personality	Personality + constraints
No narrative hooks	Visibility hints + flags
No agency	Player actions affect different axes
8) Key Insight (This Is the Core Principle)

You don’t want:

“A merchant system”

You want:

A negotiation + trust simulation with narrative affordances

Merchants are just the container.

9) If You Want to Push This Further

Next layer would be:

Rumor propagation system (merchants share info)
Faction economy (prices vary by region control)
Supply chains (war affects inventory)
AI-driven dialogue hooks tied to state

If you want, I can:

Wire this directly into your existing campaign engine (WorldState / SessionManager hooks)
Or define the exact function signatures and state transitions for your AI DM tool-calling layer

That’s where this becomes powerful instead of just “well-modeled.”