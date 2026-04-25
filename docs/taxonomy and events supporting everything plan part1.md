You were right to push back. Single-purpose tools like “buy/sell/haggle” short-circuit your architecture and quietly reintroduce exactly what you designed out: hidden authority, duplicated logic, and brittle flows.

What you want is **event-driven resolution over domain-specific verbs**. That keeps everything flowing through your pipeline instead of bypassing it.

Let me make that concrete in your system.

---

# 1) Why “buy/sell/haggle tools” are structurally wrong

Those tools implicitly do all of this in one step:

* interpret intent
* decide outcome
* mutate state
* skip intermediate conditions (visibility, awareness, reputation, inventory constraints, etc.)

That violates your separation:

```text
Adjudication → Execution → State Mutation
```

Instead, those tools collapse it into:

```text
Tool → outcome
```

That’s where fragility comes from.

---

# 2) What replaces them (correct model)

You don’t model **actions as tools**
You model **actions as intents → planned actions → events**

---

## Example: “I try to haggle”

### ❌ Bad (tool-based)

```python
Action("haggle", {...}) → result
```

---

### ✅ Correct (your system)

#### Step 1 — Intent

```python
IntentFrame(
    action="negotiate",
    target="merchant",
    params={"approach": "price_reduction"}
)
```

---

#### Step 2 — Adjudication

Determines:

* this is a **social check**
* influenced by:

  * merchant relationship
  * reputation
  * tension
  * recent events

Produces:

```python
AdjudicationDecision(
    type="check",
    skill="persuasion",
    difficulty=14,
    parameters={...}
)
```

---

#### Step 3 — ActionPlanner

```python
Action("perform_check", {...})
```

---

#### Step 4 — Execution → Event emission

```text
interaction.negotiation.started
check.persuasion.resolved
interaction.negotiation.outcome
state.price_adjusted
```

---

#### Step 5 — Everything else reacts

* merchant attitude shifts
* escalation might trigger (e.g., insult → hostility)
* future prices affected

---

# 3) The deeper principle you’re enforcing

> **Tools should represent atomic capabilities, not domain concepts**

---

## Good tools (atomic, reusable)

* `move_party`
* `apply_damage`
* `transfer_item`
* `update_relationship`
* `perform_check`

---

## Bad tools (domain-specific shortcuts)

* `buy_item`
* `sell_item`
* `haggle`
* `intimidate_npc`

Those embed:

* logic
* rules
* outcomes

They belong in:

* adjudication
* event flow
* state systems

---

# 4) Why your approach is stronger (system-level effects)

## 4.1 Composability

“Haggle” becomes:

```text
perception + social + economy + relationship + events
```

Not a single hardcoded path.

---

## 4.2 Emergence

You get outcomes like:

* merchant refuses due to prior insult
* guards intervene mid-negotiation
* hidden faction interest affects pricing

None of that requires new tools.

---

## 4.3 Escalation compatibility

Because everything emits events:

```text
interaction.negotiation.failed → escalation trigger
```

You get systemic consequences automatically.

---

## 4.4 Latent expansion compatibility

Latent layer can infer:

* merchant desperation
* hidden motives
* off-screen pressures

Which shape adjudication—without breaking determinism.

---

# 5) The rule you should formalize in your spec

You should explicitly add this (it will save you later):

```text
Tool Design Rule:

Tools must represent atomic, domain-agnostic operations.

Tools must NOT:
- encode multi-step interactions
- determine outcomes
- bypass adjudication or execution flow

All complex interactions must emerge from:
Intent → Adjudication → Actions → Events → State
```

---

# 6) What this means for your economy / merchants

You don’t need:

* buy system
* sell system
* haggle system

You need:

---

## State

* inventory
* prices
* relationship
* scarcity
* faction modifiers

---

## Events

```text
interaction.trade.initiated
interaction.trade.offer_made
interaction.trade.accepted
interaction.trade.rejected
state.inventory.changed
state.gold.transferred
```

---

## Checks

* persuasion
* deception
* intimidation

---

## Effects

* price shifts
* attitude changes
* future availability

---

# 7) Where most people fail here

They get uncomfortable and reintroduce:

> “just one helper tool”

That becomes:

* the most used path
* the least flexible
* the hardest to remove later

---

# 8) The real tradeoff (be honest about it)

Your approach:

### Costs

* more upfront structure
* more events
* more plumbing

### Gains

* system coherence
* extensibility
* true emergence
* no rewrites later

Given your goals, this is the correct trade.

---

# 9) Final mental model adjustment

Instead of:

```text
Player action → tool → result
```

You are building:

```text
Player intent
    ↓
Adjudication (what is attempted)
    ↓
Execution (what actually happens)
    ↓
Events (what occurred)
    ↓
Systems react (awareness, escalation, etc.)
    ↓
WorldState evolves
```

---

# Bottom line

You’re not avoiding tools—you’re **refining what a tool is allowed to be**.

And that’s exactly what prevents your system from collapsing into a scripted RPG with an LLM on top.

---

If you want, the next high-leverage step is:

→ I can write a **Tool Taxonomy + Event Contract section** that formally enforces this across your entire system so you don’t regress later.




Good—this is exactly the point where you want to “freeze the physics” before you start building higher-level behavior. If the tool layer is wrong, everything above it inherits the mistake.

Below is a **drop-in specification section** that enforces your design philosophy across the entire system.

---

# 🔧 **NEW SECTION — TOOL TAXONOMY + EVENT CONTRACT (SYSTEM CORE RULE)**

---

# **9.X Tool Taxonomy & Execution Contract (NEW CORE STANDARD)**

```text id="9xcore"
9.X Tool Taxonomy & Execution Contract

This system enforces strict separation between:
- Tools (atomic execution primitives)
- Events (system observations)
- Adjudication (decision-making)
- State (World truth)

Tools are NOT gameplay verbs.
Tools are NOT domain logic.
Tools are NOT outcomes.

Tools are atomic execution capabilities used ONLY by the Resolver and SessionManager.
```

---

# 9.X.1 Tool Design Principle (NON-NEGOTIABLE)

```text id="9xprinc"
Tools must be:
- atomic
- domain-agnostic
- deterministic
- composable

Tools must NOT:
- encode game rules
- determine narrative outcomes
- resolve multi-step interactions
- bypass Adjudication or Event flow
```

---

# 9.X.2 Correct Tool Categories (ALLOWED)

## 1. State Mutation Primitives

```text id="tcat1"
- apply_state_update
- set_flag
- modify_attribute
```

---

## 2. Entity Actions (Physical / Mechanical Only)

```text id="tcat2"
- move_entity
- apply_damage
- spawn_entity
- remove_entity
```

---

## 3. Inventory / Resource Primitives

```text id="tcat3"
- transfer_item
- add_item
- remove_item
- modify_resource
```

---

## 4. Check / Resolution Primitives

```text id="tcat4"
- perform_check
- roll_resolution (if required by deterministic engine, not LLM)
```

---

## 5. System Tools

```text id="tcat5"
- emit_event
- schedule_action
- queue_reaction
```

---

# 9.X.3 FORBIDDEN TOOL TYPES (CRITICAL)

These MUST NOT exist as tools:

```text id="tbad"
- buy_item
- sell_item
- haggle
- negotiate_trade
- intimidate_npc
- persuade_npc
- resolve_combat
- resolve_encounter
```

### Why they are forbidden:

They collapse multiple systems into one opaque outcome step, bypassing:

* Adjudication
* Event generation
* Reaction system
* Escalation system
* ContextBuilder

---

# 9.X.4 Correct Interaction Model (MANDATORY FLOW)

All complex actions MUST follow this pipeline:

```text id="flow1"
IntentFrame
    ↓
AdjudicationDecision
    ↓
ActionPlanner
    ↓
ActionQueue
    ↓
Resolver Execution (Tools)
    ↓
Event Emission
    ↓
System Reactions (Escalation / Awareness / Combat / etc.)
    ↓
WorldState Update
```

---

# 9.X.5 EVENT CONTRACT (CORE SYSTEM LANGUAGE)

## 9.X.5.1 Event Structure

```python id="event1"
class Event:
    id: str
    type: str
    timestamp: int

    source_id: str | None
    target_id: str | None

    data: dict

    parent_id: str | None
```

---

## 9.X.5.2 Event Naming Convention

```text id="event2"
<domain>.<object>.<phase>
```

Examples:

```text id="eventex"
combat.attack.declared
combat.attack.resolved
combat.damage.applied

interaction.trade.offer_made
interaction.trade.rejected

movement.entity.started
movement.entity.completed

perception.entity.spotted
sound.event.generated
```

---

## 9.X.5.3 Event Domains (EXTENSIBLE ROOTS ONLY)

Allowed top-level domains:

```text id="domains"
combat
movement
interaction
perception
sound
state
system
```

New domains may be added ONLY at system evolution boundaries, not ad hoc.

---

## 9.X.5.4 Event Emission Rules

Events MUST:

* be emitted only by Resolver or tools
* be deterministic
* be appended in strict execution order
* never be retroactively inserted

Events MUST NOT:

* be generated by LLM reasoning
* be inferred post hoc
* replace state updates

---

## 9.X.6 EVENT → SYSTEM RESPONSIBILITY MAPPING

```text id="map1"
Event Log drives:
- Reaction System
- Interrupt System
- Escalation System
- Awareness System
- Latent Expansion (as input only)
```

No system may bypass event_log.

---

# 9.X.7 TOOL ↔ EVENT RELATIONSHIP RULE

Every tool execution MUST produce one or more events.

```text id="rule1"
Tool Execution → Event(s) → System Reaction
```

If a tool does not generate events:

* it is invalid in this architecture

---

# 9.X.8 DESIGN INTENT (IMPORTANT ALIGNMENT RULE)

This system enforces:

> Tools describe “how reality is changed”
> Events describe “what happened”
> Adjudication describes “what was intended”

They must never collapse into each other.

---

# 🧠 **WHY THIS LOCKS YOUR SYSTEM CORRECTLY**

This gives you:

### 1. Structural safety

No hidden logic inside tools

### 2. Emergence

Trade, combat, persuasion all emerge from same primitives

### 3. Stability

No domain-specific rewrites later

### 4. AI control boundary clarity

LLM cannot bypass system layers anymore

---

# ⚠️ **IMPORTANT IMPLEMENTATION NOTE**

You should apply this rule immediately:

> If you feel tempted to create a “shortcut tool,” it belongs in Adjudication or Event composition—not the tool layer.

---

# 🧭 **HOW THIS CONNECTS TO YOUR EARLIER DESIGN**

* Latent Expansion → informs Adjudication only
* Adjudication → produces intent, not outcomes
* Tools → execute atomic effects only
* Events → represent truth of execution
* Escalation → reacts to events only

---

# 🔚 **BOTTOM LINE**

You now have a clean separation:

```text id="finalmodel"
Intent → Decision → Atomic Execution → Event → System Reaction → State
```

No shortcuts. No domain leakage. No hidden logic.

---

If you want the next step, I can help you:

→ define a **minimal starter toolset (10–15 tools max)** that supports *everything in your system including combat, trading, stealth, and escalation without ever adding new tools again*

That’s the point where your architecture becomes “closed under extension”—which is where these systems stop breaking later.




Good—this is the right moment to lock the tool layer. If you get this wrong now, everything above it (combat, escalation, economy, latent inference) will eventually fragment into one-off systems again.

What you want is a **closed, minimal, composable tool set** that can express *any* game action without encoding game logic.

---

# 🔧 **MINIMAL TOOLSET (SYSTEM-LEVEL PRIMITIVES ONLY)**

This is your canonical tool layer.

---

# **9.X.9 Core Toolset (FINALIZED BASE PRIMITIVES)**

```text id="coretools"
This system uses a fixed, minimal set of atomic tools.

No additional domain-specific tools may be added without explicit system revision.
```

---

# 🧱 **A. STATE MUTATION PRIMITIVES**

These are the ONLY ways the world changes.

## 1. apply_state_update

```python id="t1"
apply_state_update(world_state, patch: dict)
```

### Purpose:

Generic structured mutation of WorldState.

### Examples:

* alert_level changes
* faction hostility shifts
* flags toggled

---

## 2. set_flag

```python id="t2"
set_flag(entity_id, flag_name, value)
```

### Purpose:

Binary / categorical world state markers.

---

## 3. modify_attribute

```python id="t3"
modify_attribute(entity_id, attribute, delta)
```

### Purpose:

Numeric adjustments (health, morale, stamina, reputation).

---

# 🚶 **B. ENTITY MANIPULATION PRIMITIVES**

## 4. move_entity

```python id="t4"
move_entity(entity_id, destination)
```

### Purpose:

Spatial transitions.

Supports:

* party movement
* NPC movement
* environmental repositioning

---

## 5. spawn_entity

```python id="t5"
spawn_entity(entity_type, location, properties)
```

### Purpose:

Introduce new agents or objects.

Used for:

* guards
* traps
* items
* environmental hazards

---

## 6. remove_entity

```python id="t6"
remove_entity(entity_id)
```

### Purpose:

Despawn / destruction / death.

---

## 7. apply_damage

```python id="t7"
apply_damage(target_id, amount, damage_type)
```

### Purpose:

Standardized harm application.

(No combat logic inside—just effect.)

---

# 🎒 **C. RESOURCE & INVENTORY PRIMITIVES**

## 8. transfer_item

```python id="t8"
transfer_item(from_id, to_id, item_id, quantity)
```

### Purpose:

Movement of goods between entities.

---

## 9. modify_resource

```python id="t9"
modify_resource(entity_id, resource_type, delta)
```

### Purpose:

Gold, mana, supplies, ammo, etc.

---

# ⚖️ **D. RESOLUTION PRIMITIVES (NO GAME LOGIC)**

## 10. perform_check

```python id="t10"
perform_check(entity_id, skill, difficulty, modifiers)
```

### Purpose:

Generic resolution engine hook.

### IMPORTANT:

* Does NOT decide outcomes
* Only produces result event

---

# 📡 **E. EVENT SYSTEM PRIMITIVES**

## 11. emit_event

```python id="t11"
emit_event(event)
```

### Purpose:

ONLY way to introduce system truth.

Everything important becomes an event.

---

## 12. schedule_action

```python id="t12"
schedule_action(action, delay)
```

### Purpose:

Deferred execution (turn-based, delayed reactions).

---

## 13. queue_reaction

```python id="t13"
queue_reaction(reaction)
```

### Purpose:

Immediate or near-immediate reactive behaviors.

---

# 🧠 **F. SYSTEM CONTROL PRIMITIVE**

## 14. update_ai_memory (LIMITED USE)

```python id="t14"
update_ai_memory(entity_id, memory_patch)
```

### Purpose:

Non-authoritative memory tracking (NPC awareness, suspicion, knowledge).

---

# 🔁 **EVENT REQUIREMENT RULE (CRITICAL)**

Every tool MUST emit at least one event:

```text id="req1"
Tool Execution → Event(s) → System Reaction
```

Examples:

* move_entity → movement.entity.completed
* apply_damage → combat.damage.applied
* spawn_entity → system.entity.spawned

If a tool does not generate events:
→ it is invalid in this architecture

---

# 🧩 **WHY THIS TOOLSET WORKS (DESIGN RATIONALE)**

## 1. No domain logic embedded

There is:

* no “combat tool”
* no “trade tool”
* no “stealth tool”

Everything is composition of primitives.

---

## 2. Everything becomes event-driven

Instead of:

```text id="bad"
buy_item() → result
```

You get:

```text id="good"
transfer_item → modify_resource → emit_event → escalation reacts
```

---

## 3. Escalation becomes universal

Because everything emits events:

* combat escalation
* social escalation
* dungeon escalation
* faction escalation

All unified.

---

## 4. Latent Expansion becomes safe

It only observes:

* events
* state
* context

Never tools.

---

## 5. Combat becomes emergent, not special-cased

Combat is just:

* move_entity
* apply_damage
* perform_check
* emit_event

No separate system logic needed at tool level.

---

# 🚫 **FORBIDDEN EXTENSIONS (IMPORTANT)**

You must NEVER add tools like:

* `buy_item`
* `sell_item`
* `negotiate_trade`
* `resolve_combat`
* `stealth_action`
* `persuade_npc`

If you feel the need for them:
→ they belong in Adjudication + Event composition, not tools

---

# 🧠 **FINAL SYSTEM MODEL (UPDATED)**

```text id="final"
IntentFrame
  ↓
Adjudication (LLM)
  ↓
ActionPlanner
  ↓
Atomic Tools (this list only)
  ↓
Event Emission
  ↓
Resolver Effects
  ↓
Escalation / Reaction / Awareness
  ↓
WorldState Update
```

---

# ⚠️ **IMPORTANT IMPLEMENTATION ADVICE**

Start with ONLY these 5 first:

### Phase 1 (safe bootstrap):

* apply_state_update
* move_entity
* emit_event
* perform_check
* apply_damage

Then expand to full set once stable.

---

# 🔚 **BOTTOM LINE**

You now have:

> a closed, minimal, composable physics layer for your game world

Everything else—combat, trade, diplomacy, stealth—is now:

> emergent behavior from shared primitives + event-driven reactions

---

If you want next step, I recommend:

→ I map your **combat system entirely onto this toolset (no new tools needed)**

That’s where you validate whether the architecture is truly complete.




Good—this is the right moment to lock the tool layer. If you get this wrong now, everything above it (combat, escalation, economy, latent inference) will eventually fragment into one-off systems again.

What you want is a **closed, minimal, composable tool set** that can express *any* game action without encoding game logic.

---

# 🔧 **MINIMAL TOOLSET (SYSTEM-LEVEL PRIMITIVES ONLY)**

This is your canonical tool layer.

---

# **9.X.9 Core Toolset (FINALIZED BASE PRIMITIVES)**

```text id="coretools"
This system uses a fixed, minimal set of atomic tools.

No additional domain-specific tools may be added without explicit system revision.
```

---

# 🧱 **A. STATE MUTATION PRIMITIVES**

These are the ONLY ways the world changes.

## 1. apply_state_update

```python id="t1"
apply_state_update(world_state, patch: dict)
```

### Purpose:

Generic structured mutation of WorldState.

### Examples:

* alert_level changes
* faction hostility shifts
* flags toggled

---

## 2. set_flag

```python id="t2"
set_flag(entity_id, flag_name, value)
```

### Purpose:

Binary / categorical world state markers.

---

## 3. modify_attribute

```python id="t3"
modify_attribute(entity_id, attribute, delta)
```

### Purpose:

Numeric adjustments (health, morale, stamina, reputation).

---

# 🚶 **B. ENTITY MANIPULATION PRIMITIVES**

## 4. move_entity

```python id="t4"
move_entity(entity_id, destination)
```

### Purpose:

Spatial transitions.

Supports:

* party movement
* NPC movement
* environmental repositioning

---

## 5. spawn_entity

```python id="t5"
spawn_entity(entity_type, location, properties)
```

### Purpose:

Introduce new agents or objects.

Used for:

* guards
* traps
* items
* environmental hazards

---

## 6. remove_entity

```python id="t6"
remove_entity(entity_id)
```

### Purpose:

Despawn / destruction / death.

---

## 7. apply_damage

```python id="t7"
apply_damage(target_id, amount, damage_type)
```

### Purpose:

Standardized harm application.

(No combat logic inside—just effect.)

---

# 🎒 **C. RESOURCE & INVENTORY PRIMITIVES**

## 8. transfer_item

```python id="t8"
transfer_item(from_id, to_id, item_id, quantity)
```

### Purpose:

Movement of goods between entities.

---

## 9. modify_resource

```python id="t9"
modify_resource(entity_id, resource_type, delta)
```

### Purpose:

Gold, mana, supplies, ammo, etc.

---

# ⚖️ **D. RESOLUTION PRIMITIVES (NO GAME LOGIC)**

## 10. perform_check

```python id="t10"
perform_check(entity_id, skill, difficulty, modifiers)
```

### Purpose:

Generic resolution engine hook.

### IMPORTANT:

* Does NOT decide outcomes
* Only produces result event

---

# 📡 **E. EVENT SYSTEM PRIMITIVES**

## 11. emit_event

```python id="t11"
emit_event(event)
```

### Purpose:

ONLY way to introduce system truth.

Everything important becomes an event.

---

## 12. schedule_action

```python id="t12"
schedule_action(action, delay)
```

### Purpose:

Deferred execution (turn-based, delayed reactions).

---

## 13. queue_reaction

```python id="t13"
queue_reaction(reaction)
```

### Purpose:

Immediate or near-immediate reactive behaviors.

---

# 🧠 **F. SYSTEM CONTROL PRIMITIVE**

## 14. update_ai_memory (LIMITED USE)

```python id="t14"
update_ai_memory(entity_id, memory_patch)
```

### Purpose:

Non-authoritative memory tracking (NPC awareness, suspicion, knowledge).

---

# 🔁 **EVENT REQUIREMENT RULE (CRITICAL)**

Every tool MUST emit at least one event:

```text id="req1"
Tool Execution → Event(s) → System Reaction
```

Examples:

* move_entity → movement.entity.completed
* apply_damage → combat.damage.applied
* spawn_entity → system.entity.spawned

If a tool does not generate events:
→ it is invalid in this architecture

---

# 🧩 **WHY THIS TOOLSET WORKS (DESIGN RATIONALE)**

## 1. No domain logic embedded

There is:

* no “combat tool”
* no “trade tool”
* no “stealth tool”

Everything is composition of primitives.

---

## 2. Everything becomes event-driven

Instead of:

```text id="bad"
buy_item() → result
```

You get:

```text id="good"
transfer_item → modify_resource → emit_event → escalation reacts
```

---

## 3. Escalation becomes universal

Because everything emits events:

* combat escalation
* social escalation
* dungeon escalation
* faction escalation

All unified.

---

## 4. Latent Expansion becomes safe

It only observes:

* events
* state
* context

Never tools.

---

## 5. Combat becomes emergent, not special-cased

Combat is just:

* move_entity
* apply_damage
* perform_check
* emit_event

No separate system logic needed at tool level.

---

# 🚫 **FORBIDDEN EXTENSIONS (IMPORTANT)**

You must NEVER add tools like:

* `buy_item`
* `sell_item`
* `negotiate_trade`
* `resolve_combat`
* `stealth_action`
* `persuade_npc`

If you feel the need for them:
→ they belong in Adjudication + Event composition, not tools

---

# 🧠 **FINAL SYSTEM MODEL (UPDATED)**

```text id="final"
IntentFrame
  ↓
Adjudication (LLM)
  ↓
ActionPlanner
  ↓
Atomic Tools (this list only)
  ↓
Event Emission
  ↓
Resolver Effects
  ↓
Escalation / Reaction / Awareness
  ↓
WorldState Update
```

---

# ⚠️ **IMPORTANT IMPLEMENTATION ADVICE**

Start with ONLY these 5 first:

### Phase 1 (safe bootstrap):

* apply_state_update
* move_entity
* emit_event
* perform_check
* apply_damage

Then expand to full set once stable.

---

# 🔚 **BOTTOM LINE**

You now have:

> a closed, minimal, composable physics layer for your game world

Everything else—combat, trade, diplomacy, stealth—is now:

> emergent behavior from shared primitives + event-driven reactions

---

If you want next step, I recommend:

→ I map your **combat system entirely onto this toolset (no new tools needed)**

That’s where you validate whether the architecture is truly complete.




Good—this is the real validation step. If combat cannot be expressed using your primitive toolset, the architecture is incomplete. The good news: it *can* be, cleanly, and without introducing any new tools.

Below is a **fully system-compliant combat model** built entirely on your 14-tool primitive set + event-driven resolver logic.

---

# ⚔️ **COMBAT SYSTEM (PURE TOOLSET IMPLEMENTATION)**

---

# 1) Core Principle

Combat is NOT a subsystem.

> Combat is an **emergent state machine driven by events + atomic tools inside the Resolver Loop**.

No special combat tools. No hidden combat logic.

---

# 2) Combat State Model (NO NEW TOOLS)

Combat exists only as structured WorldState + events:

```python id="cstate1"
combat_state = {
    "active": bool,
    "participants": list,
    "turn_order": list,
    "current_actor": entity_id,
    "round": int,
    "initiative_seed": int,
}
```

---

# 3) Combat Initiation (EVENT-DRIVEN)

## Trigger Events

Combat starts ONLY via events such as:

```text id="ce1"
combat.initiation.triggered
perception.enemy_spotted
interaction.attack_declared
```

---

## Resolver Response

When detected:

### Step 1 — Spawn combat state

```text id="cstep1"
apply_state_update → combat_state.active = true
```

---

### Step 2 — Determine participants

```text id="cstep2"
emit_event: combat.participants.identified
```

(No tool creates combat logic—just state + event)

---

### Step 3 — Initiative via check tool

```text id="cstep3"
perform_check(entity_id, "initiative", difficulty=None)
```

Then:

```text id="cstep4"
apply_state_update → turn_order sorted deterministically
```

---

# 4) TURN LOOP (RESOLVER-DRIVEN)

Each turn is just:

```text id="tloop"
1. select current_actor (state)
2. generate IntentFrame
3. adjudicate action
4. execute atomic tools
5. emit events
6. resolve reactions
7. advance turn
```

---

# 5) CORE COMBAT ACTIONS (NO SPECIAL TOOLS)

Everything is composed from primitives:

---

## 5.1 Attack

### Flow:

```text id="atk1"
Intent: "attack target"
```

---

### Adjudication:

Produces:

```text id="atk2"
perform_check(attacker, "attack", target_defense)
```

---

### Execution:

If hit:

```text id="atk3"
apply_damage(target, amount, type)
emit_event(combat.damage.applied)
```

If miss:

```text id="atk4"
emit_event(combat.attack.missed)
```

---

# 5.2 Movement in Combat

```text id="mov1"
move_entity(entity_id, tile)
emit_event(movement.entity.completed)
```

---

# 5.3 Item Use

```text id="item1"
transfer_item(user, target/self, item)
modify_resource(...)
emit_event(interaction.item.used)
```

---

# 6) REACTIONS (CRITICAL COMBAT DEPTH LAYER)

Reactions are what make combat feel alive—NOT new tools.

Triggered by events:

---

## Example: enemy enters sight

```text id="r1"
event: perception.enemy_spotted
```

Triggers:

```text id="r2"
queue_reaction → "raise_weapon"
queue_reaction → "retreat"
```

Which become:

* move_entity
* modify_attribute
* emit_event

---

# 7) INTERRUPTS (EVENT-ONLY CONTROL)

Interrupts are triggered by events:

```text id="i1"
combat.attack.declared
trap.triggered
entity.downed
```

Effect:

```text id="i2"
apply_state_update → combat.current_actor = None
emit_event(system.turn.interrupted)
```

---

# 8) DAMAGE & DEATH FLOW

## Damage

```text id="d1"
apply_damage → emits combat.damage.applied
```

---

## Death resolution

```text id="d2"
if hp <= 0:
    remove_entity(target)
    emit_event(combat.entity.killed)
```

---

# 9) ESCALATION IN COMBAT (IMPORTANT INTEGRATION)

Escalation listens ONLY to events:

### Examples:

```text id="e1"
combat.entity.killed
combat.damage.heavy
combat.turns_prolonged
```

Escalation can then:

* spawn reinforcements
* increase alert level
* alter environment

BUT NEVER:

* control combat flow directly
* override turn system

---

# 10) LATENT EXPANSION IN COMBAT

Latent layer only influences:

* interpretation of intent
* perception of battlefield

Example:

Player listens:

Latent generates:

* “reinforcements arriving”
* “enemy morale breaking”
* “hidden archer present”

But:

> only becomes real if confirmed through events + checks

---

# 11) COMBAT TERMINATION

Combat ends ONLY via state + event agreement:

```text id="end1"
apply_state_update → combat.active = false
emit_event(combat.ended)
```

Triggered when:

* one side eliminated
* flee conditions met
* narrative resolution event occurs

---

# 12) FULL COMBAT LOOP (COMPLETE SYSTEM)

```text id="loop"
EVENT: combat.initiation.triggered
  ↓
apply_state_update (activate combat)
  ↓
perform_check (initiative)
  ↓
turn loop begins
  ↓
IntentFrame (actor)
  ↓
AdjudicationDecision
  ↓
Atomic tools execute:
    - move_entity
    - apply_damage
    - perform_check
    - transfer_item
  ↓
emit_event(s)
  ↓
Reactions fire
  ↓
Interrupt check
  ↓
Escalation processes events
  ↓
WorldState updates
  ↓
Next turn
```

---

# 13) WHY THIS WORKS (IMPORTANT)

## 1. No combat system exists as a tool

Combat is not a subsystem—it is a **pattern of event interpretation**

---

## 2. Fully composable

Every combat action is:

* movement
* state change
* check
* event

---

## 3. Fully extensible

You can add:

* new weapons
* new statuses
* new behaviors

WITHOUT changing tools

---

## 4. Fully deterministic

Because:

* all outcomes flow through resolver
* all randomness is isolated in checks
* all state changes are explicit

---

# 14) FINAL ALIGNMENT WITH YOUR ARCHITECTURE

```text id="final"
Latent Expansion → perception bias layer
Adjudication → intent shaping
Tools → atomic reality changes
Events → truth ledger
Escalation → systemic consequences
Combat → emergent event-driven state machine
```

---

# 🔚 Bottom line

You now have:

> a combat system that does NOT exist as a subsystem, but emerges from your core engine without any special cases or new tools

---

If you want the next step, the natural progression is:

→ I map **encounter design on top of this same event + tool system**

That’s where your “world simulation layer” becomes fully unified instead of layered systems.




Good. Encounters are where most systems quietly fall apart because they accidentally become *mini-games with their own rules*. We’re not doing that. We’re treating encounters as **structured slices of simulation state + event-driven constraints**, not a parallel system.

This keeps everything you’ve built (events, tools, escalation, combat) unified under one execution model.

---

# 🧭 **ENCOUNTER SYSTEM (EVENT-DRIVEN, NO SPECIAL LOGIC)**

---

# 1) Core Principle

> An encounter is a **bounded interpretation window over WorldState + event history**, not a separate subsystem.

Encounters do NOT:

* own combat
* own AI behavior
* own rules
* override simulation

Encounters DO:

* define context boundaries
* constrain participant scope
* seed escalation pathways
* guide interpretation density

---

# 2) Encounter = Data Container, Not Logic Engine

```python id="enc0"
class Encounter:
    id: str

    # scope definition
    participants: list[str]
    location: str | None

    # state modifiers (applied via WorldState, not directly)
    initial_conditions: dict

    # optional structure hints
    tags: list[str]  # "ambush", "social", "dungeon", "escort"

    # escalation bindings
    escalation_maps: list[str]

    # lifecycle tracking
    active: bool
```

---

# 3) Encounter Activation (EVENT-DRIVEN ONLY)

Encounters begin ONLY from events:

```text id="enc1"
movement.entity.entered_area
perception.group_detected
interaction.dialogue_started
system.trigger.encounter
```

---

## Activation Flow

```text id="enc2"
EVENT → Encounter match → apply_state_update → emit_event(encounter.started)
```

No LLM decision required.

---

# 4) Encounter DOES NOT CONTROL COMBAT

This is the most important boundary.

| System       | Responsibility                  |
| ------------ | ------------------------------- |
| Encounter    | defines context + scope         |
| Combat       | executes conflict state machine |
| Escalation   | reacts to events                |
| Adjudication | interprets intent               |

Encounters NEVER:

* start combat directly
* spawn enemies directly
* resolve outcomes

They only:

* allow combat initiation events to matter

---

# 5) Encounter State Model (MINIMAL ADDITION TO WORLDSTATE)

```python id="enc3"
world_state.encounter_context = {
    "active_encounter_id": str | None,
    "allowed_entities": list[str],
    "visibility_bias": float,
    "tension_modifier": float
}
```

---

# 6) Encounter Lifecycle

---

## 6.1 Start

Triggered by event match:

```text id="enc4"
encounter.started
```

Actions:

```text id="enc5"
apply_state_update → set active_encounter_id
emit_event(encounter.context.established)
```

---

## 6.2 Active Phase

During this phase:

Encounters only influence:

* perception weighting
* escalation sensitivity
* available interaction space

NOT:

* actions
* outcomes
* combat logic

---

## 6.3 Transition to Combat (IMPORTANT)

Combat is NOT started by encounter.

Combat starts ONLY if:

```text id="enc6"
event: combat.initiation.triggered
```

Encounter merely provides context:

* who is involved
* where it occurs
* what escalation maps apply

---

## 6.4 End

Triggered when:

* participants leave area
* conflict resolved
* escalation clears

```text id="enc7"
apply_state_update → active_encounter_id = None
emit_event(encounter.ended)
```

---

# 7) ENCOUNTER ↔ ESCALATION BINDING

Encounters define *what escalation maps are valid here*.

```python id="enc8"
encounter.escalation_maps = [
    "dungeon_alert_chain",
    "merchant_conflict_chain"
]
```

Escalation system:

* only evaluates maps allowed by encounter context

BUT:

* still triggered ONLY by events

---

# 8) ENCOUNTER ↔ LATENT EXPANSION RELATION

Encounters influence latent interpretation ONLY via context:

```text id="enc9"
ContextBuilder → includes encounter modifiers
```

Effects:

* tighter interpretation space
* more relevant candidate generation
* reduced global noise

But:

* no direct control
* no outcome injection

---

# 9) ENCOUNTER ↔ EVENTS (CRITICAL LINK)

Encounters DO NOT emit behavior.

They only:

### Filter event relevance

Example:

```text id="enc10"
combat.damage.applied
```

Inside encounter:

* high relevance
  Outside encounter:
* low narrative weight

---

### Enhance event interpretation

Same event, different context:

* ambush encounter → “critical threat”
* town encounter → “isolated incident”

---

# 10) ENCOUNTER ↔ COMBAT RELATIONSHIP (STRICT BOUNDARY)

This is the clean separation:

```text id="enc11"
Encounter = WHERE and WHO
Combat = HOW conflict resolves
Events = WHAT happened
Escalation = WHAT it becomes
```

Encounter only provides:

* participant set
* spatial constraints
* narrative framing

Combat uses:

* full event + tool system

---

# 11) ENCOUNTER FLOW (FULL SYSTEM TRACE)

```text id="flowenc"
Event triggers encounter
    ↓
Encounter context activated
    ↓
WorldState updated (scope + modifiers)
    ↓
Player/NPC actions occur
    ↓
Tools execute
    ↓
Events emitted
    ↓
Combat system (if triggered) runs
    ↓
Escalation reacts
    ↓
Encounter context modulates perception
    ↓
Encounter ends or persists
```

---

# 12) WHAT MAKES THIS DESIGN WORK

## 12.1 Encounters are NOT authority

They:

* do not decide outcomes
* do not run logic
* do not spawn systems

They only shape:

> interpretation + relevance + scope

---

## 12.2 Everything still flows through events

No bypass paths exist:

* no encounter shortcuts
* no encounter-owned combat
* no hidden logic

---

## 12.3 Systems remain orthogonal

| System     | Role                  |
| ---------- | --------------------- |
| Encounter  | context boundary      |
| Combat     | execution of conflict |
| Escalation | world evolution       |
| Latent     | inference layer       |
| Tools      | atomic physics        |

---

# 13) WHY THIS IS THE RIGHT LEVEL OF DETAIL (IMPORTANT)

You deliberately avoided:

* encounter AI logic
* encounter outcome rules
* encounter-specific tools

Because those would:

* duplicate combat logic
* fragment escalation
* create hidden authority layers

Instead you defined:

> a context-aware boundary system that constrains interpretation but not execution

That’s exactly the right abstraction level.

---

# 14) FINAL UNIFIED MODEL (UPDATED)

```text id="finalmodel"
WorldState = Reality
Tools = Physics primitives
Events = Truth ledger
Resolver = Execution engine
Combat = Conflict state machine
Escalation = World evolution engine
Latent Expansion = Inference layer
Encounter = Context boundary layer
Adjudication = Intent shaping layer
```

---

# 🔚 Bottom line

You now have a fully consistent architecture where:

* Encounters don’t compete with combat
* Escalation doesn’t duplicate encounter logic
* Latent doesn’t influence outcomes
* Tools remain atomic
* Events remain the only truth interface

Everything is cleanly separated by **authority, not function**.

---

If you want the next step, the real structural milestone is:

→ defining a **unified Event Taxonomy map across Encounter + Combat + Escalation so nothing diverges later**

That’s the point where the system becomes self-consistent at scale instead of just well-designed in parts.



Good—this is the point where you prevent future drift. If your event vocabulary isn’t unified across Encounter, Combat, and Escalation, the system will slowly fracture into “almost compatible” subsystems that are painful to debug.

What follows is your **canonical Event Taxonomy Map (system-wide contract)**. This is not flavor text—it is the *shared physics language* of your entire engine.

---

# 📡 **UNIFIED EVENT TAXONOMY (SYSTEM-WIDE CONTRACT)**

---

# 1) Core Principle

> All systems (Encounter, Combat, Escalation, World Simulation) share a single event ontology.

No system is allowed to invent private event meanings.

---

# 2) Event Structure (unchanged baseline)

```python id="ev0"
class Event:
    id: str
    type: str
    timestamp: int

    source_id: str | None
    target_id: str | None

    data: dict

    parent_id: str | None
```

---

# 3) GLOBAL EVENT HIERARCHY

All events follow:

```text id="ev1"
<domain>.<entity>.<phase>
```

Where:

* domain = system of origin
* entity = object type
* phase = lifecycle stage

---

# 4) SYSTEM DOMAINS (LOCKED)

These are the ONLY valid top-level domains:

```text id="dom"
movement
perception
interaction
combat
sound
state
system
encounter
escalation
```

No others may be introduced without versioned migration.

---

# 5) CANONICAL EVENT MAP (CROSS-SYSTEM)

This is the critical alignment layer.

---

# 🚶 MOVEMENT DOMAIN

Used by Encounter, Combat, Escalation equally.

```text id="mov"
movement.entity.started
movement.entity.completed
movement.entity.interrupted
movement.party.repositioned
```

### Usage:

* Encounter: scope shifts
* Combat: positioning + tactics
* Escalation: pursuit / escape chains

---

# 👁️ PERCEPTION DOMAIN

Shared visibility + awareness backbone.

```text id="per"
perception.entity.spotted
perception.entity.lost
perception.suspicion.increased
perception.suspicion.decreased
```

### Usage:

* Encounter: context awareness
* Combat: targeting + interrupts
* Escalation: alert propagation

---

# 🤝 INTERACTION DOMAIN

All social / object interactions (NO domain logic embedded)

```text id="int"
interaction.dialogue.started
interaction.dialogue.ended

interaction.trade.offer_made
interaction.trade.rejected
interaction.trade.completed

interaction.request.made
interaction.request.denied
```

### Important:

No “haggle”, “persuade”, “intimidate” events.

Those are resolved via checks → result becomes event.

---

# ⚔️ COMBAT DOMAIN (PURE OUTCOME LAYER)

Combat is strictly *resolution events*, not action definitions.

```text id="com"
combat.initiation.triggered
combat.turn.started
combat.turn.ended

combat.attack.declared
combat.attack.resolved
combat.attack.missed

combat.damage.applied
combat.entity.downed
combat.entity.killed

combat.state.stabilized
combat.state.ended
```

### Key rule:

Combat events describe **what happened**, never **what was attempted**.

---

# 🔊 SOUND DOMAIN

Used for stealth, escalation, awareness.

```text id="snd"
sound.event.generated
sound.event.heard
sound.event.misidentified
```

### Usage:

* Encounter: ambient interpretation
* Combat: detection + interrupts
* Escalation: alert propagation

---

# 🧠 STATE DOMAIN

Direct world truth changes (rare, controlled)

```text id="st"
state.attribute.modified
state.flag.set
state.resource.changed
state.entity.spawned
state.entity.removed
```

### Important:

These are **effects of tools**, not decisions.

---

# ⚙️ SYSTEM DOMAIN

Meta-engine events.

```text id="sys"
system.turn.started
system.turn.ended

system.check.resolved
system.action.executed

system.interrupt.triggered
system.queue.flushed
```

---

# 🏕️ ENCOUNTER DOMAIN

Context boundary lifecycle only.

```text id="enc"
encounter.started
encounter.context.established
encounter.updated
encounter.ended
```

### Important:

Encounters do NOT define behavior.

Only scope + interpretation window.

---

# 🌋 ESCALATION DOMAIN

World evolution reactions.

```text id="esc"
escalation.node.triggered
escalation.node.completed
escalation.chain.progressed

escalation.alert.level_changed
escalation.faction.state_changed
```

### Rule:

Escalation only reacts to event_log.

Never initiates behavior directly.

---

# 6) CROSS-SYSTEM EVENT FLOW RULES

---

## 6.1 Event causality is strictly linear

```text id="flow1"
Tool → Event → Reaction → New Tool → New Event
```

No skipping steps.

---

## 6.2 Encounter does NOT emit combat events

Encounter only emits:

* encounter.started
* encounter.context.established

Combat emits its own lifecycle.

---

## 6.3 Combat is not aware of Encounter

Combat only sees:

* event_log
* WorldState
* participants list

Encounter is just context, not authority.

---

## 6.4 Escalation is event-driven ONLY

Escalation listens to:

* combat.damage.*
* perception.*
* sound.*
* interaction.*

It never:

* modifies combat flow directly
* bypasses tools

---

# 7) EVENT CONSISTENCY RULE (CRITICAL)

Every system MUST obey:

```text id="rule1"
If two systems describe the same phenomenon, they must use the same event type.
```

Example:

Bad:

* encounter says “enemy_detected”
* combat says “enemy_spotted”

Good:

* perception.entity.spotted

---

# 8) EVENT OWNERSHIP MATRIX

| Event Type    | Owned By                 | Consumed By                     |
| ------------- | ------------------------ | ------------------------------- |
| movement.*    | Resolver                 | Encounter / Combat / Escalation |
| perception.*  | Resolver                 | All                             |
| combat.*      | Combat layer (via tools) | Escalation / UI                 |
| interaction.* | Adjudication + tools     | Encounter / Escalation          |
| state.*       | Tools only               | All                             |
| encounter.*   | Encounter system         | ContextBuilder                  |
| escalation.*  | Escalation system        | WorldState                      |
| system.*      | Engine                   | All                             |

---

# 9) DESIGN GUARANTEE (WHY THIS HOLDS)

This structure ensures:

### 9.1 No duplicate meaning

One concept → one event type

---

### 9.2 No hidden authority

No system can “decide outcomes” outside events

---

### 9.3 Full traceability

Every world change is reconstructable from event_log

---

### 9.4 Cross-system compatibility

Combat, Encounter, Escalation all read the same “language”

---

# 10) FINAL UNIFIED MODEL (UPDATED)

```text id="final"
IntentFrame
  ↓
AdjudicationDecision
  ↓
ActionPlanner
  ↓
Atomic Tools
  ↓
Unified Event System (THIS SPEC)
  ↓
Reaction System
  ↓
Combat / Escalation / Encounter (consumers only)
  ↓
WorldState update
```

---

# 🔚 Bottom line

You now have:

> a single canonical event language that all systems speak, with no private dialects, no hidden control paths, and no subsystem divergence

This is what prevents your architecture from slowly fracturing as complexity grows.

---

If you want the next step, the natural continuation is:

→ a **ContextBuilder specification that shows exactly how Encounter + Combat + Escalation events are merged into a single unified perception layer (UnifiedContext)**

That’s where the system becomes fully coherent at runtime instead of just structurally clean.




Good—this is exactly the right next piece. If the event system is your “physics language,” then **ContextBuilder is your perception engine**: it decides what any subsystem (LLM, narration, UI, AI DM) is *allowed to know at any moment*, and how raw simulation becomes usable cognition.

If you get this wrong, everything above it collapses into “the LLM sees too much or too little reality.” If you get it right, you get stable narrative control without breaking determinism.

---

# 🧠 **UNIFIED CONTEXT BUILDER SPEC (SYSTEM PERCEPTION LAYER)**

---

# 1) Core Principle

> ContextBuilder is a **deterministic projection layer over WorldState + EventLog**, producing a *filtered, structured, role-aware perception snapshot*.

It does NOT:

* decide outcomes
* interpret intent
* generate narrative
* modify state

It ONLY:

* selects relevant information
* structures it consistently
* applies visibility + awareness constraints
* converts raw simulation into usable “perceptual truth”

---

# 2) Architectural Position

```text id="cb0"
WorldState + EventLog
        ↓
   ContextBuilder
        ↓
UnifiedContext (READ-ONLY)
        ↓
LLM / NarrativeEngine / UI / AI DM
```

ContextBuilder is the **only gateway to perception**.

---

# 3) Inputs

ContextBuilder consumes:

### 3.1 WorldState (current truth)

* positions
* entities
* flags
* combat state
* encounter context
* escalation state

---

### 3.2 Event Log (causal history window)

```text id="cb1"
last_n_events: N
or
event_window: time-based slice
```

Used for:

* momentum
* recent changes
* causality interpretation

---

### 3.3 Active Context Modifiers

From:

* Encounter
* Combat
* Escalation
* Lighting
* Sound
* Visibility

---

# 4) Output: UnifiedContext

```python id="cb2"
class UnifiedContext:
    timestamp: int

    # spatial perception
    visible_entities: list
    hidden_entities: list
    partially_known_entities: list

    # environment
    location: str
    terrain: str
    lighting: float
    sound_level: float

    # awareness layer
    known_threats: list
    known_allies: list
    unknown_threat_signals: list

    # narrative-relevant state
    encounter_context: dict
    combat_context: dict
    escalation_context: dict

    # recent events (filtered)
    salient_events: list

    # constraints
    visibility_map: dict
    knowledge_gaps: dict
```

---

# 5) CORE FUNCTIONAL PIPELINE

ContextBuilder runs in strict order:

```text id="cb3"
1. Slice WorldState
2. Apply visibility model
3. Apply perception rules
4. Merge event relevance
5. Apply encounter modifiers
6. Apply combat modifiers
7. Apply escalation modifiers
8. Construct UnifiedContext
```

---

# 6) STEP-BY-STEP SPEC

---

## 6.1 WorldState Projection

Extract raw facts:

* entities
* positions
* states
* flags

No filtering yet.

---

## 6.2 Visibility Filter (hard constraint)

```text id="cb4"
visible = f(line_of_sight, lighting, stealth, occlusion)
```

Outputs:

* visible_entities
* hidden_entities

IMPORTANT:
Hidden entities still exist in context but are **not fully described**

---

## 6.3 Perception Layer (soft knowledge)

Transforms visibility into awareness:

```text id="cb5"
if previously_seen(entity):
    partially_known_entities.append(entity)
```

This is where:

* memory
* suspicion
* prior encounters

affect perception.

---

## 6.4 Event Relevance Filtering

Only include events that pass:

```python id="cb6"
def is_relevant(event, context):
    return (
        event.type in perception_relevant_domains
        or event.source in visible_entities
        or event.type in escalation/combat/encounter domains
    )
```

Outputs:

* salient_events

NOT full log.

---

## 6.5 Encounter Context Injection

If active encounter:

Adds:

```text id="cb7"
- encounter_id
- participant scope
- encounter tags
- local modifiers (tension, constraints)
```

But DOES NOT:

* override visibility
* override events
* alter truth

Only *weights interpretation*

---

## 6.6 Combat Context Injection

If combat active:

Adds:

```text id="cb8"
- turn order (visible subset only)
- current actor
- combat state
- known combatants
```

Important constraint:
Hidden combatants remain hidden unless revealed by perception events.

---

## 6.7 Escalation Context Injection

Adds:

```text id="cb9"
- active escalation chains
- alert levels
- faction states
- environmental shifts in progress
```

But again:
NO control, only exposure.

---

## 6.8 Sound + Lighting Reconciliation

Derived perception modifiers:

```text id="cb10"
sound_map → awareness signals
lighting → visibility multiplier
```

Used to:

* bias interpretation
* not change truth

---

## 6.9 Knowledge Gap Construction

Critical for RP realism:

```python id="cb11"
knowledge_gaps = {
    "unknown_entities": [],
    "uncertain_events": [],
    "ambiguous_sounds": []
}
```

This is what prevents omniscience.

---

# 7) CONTEXT WEIGHTING SYSTEM

Each piece of information is assigned:

```python id="cb12"
relevance_score: float
certainty: float
visibility_confidence: float
```

Used by downstream systems:

* LLM prioritization
* narrative emphasis
* attention simulation

---

# 8) CRITICAL RULES (NON-NEGOTIABLE)

---

## 8.1 No inference beyond events + state

ContextBuilder must NOT:

* guess intentions
* predict outcomes
* simulate missing facts

Only:

> “what is supported by state or events”

---

## 8.2 No duplication of authority

If WorldState says X:

* ContextBuilder cannot contradict it

If EventLog says Y:

* ContextBuilder cannot rewrite it

---

## 8.3 No hidden narrative shaping

ContextBuilder does NOT:

* add tension
* add drama
* inject story arcs

That belongs to:
→ Escalation + NarrativeEngine only

---

## 8.4 Deterministic output

Same inputs → identical UnifiedContext always

---

# 9) HOW THIS CONNECTS TO YOUR FULL SYSTEM

---

## 9.1 Event System → feeds ContextBuilder

EventLog is raw truth history.

---

## 9.2 Encounter → biases perception only

Not control, just weighting.

---

## 9.3 Combat → structured visibility of conflict

Not resolution logic exposure.

---

## 9.4 Escalation → world pressure overlay

Not behavior control.

---

## 9.5 LLM (DM) → consumes ONLY UnifiedContext

This is critical:

> The LLM never sees WorldState directly.

Only:

```text id="cb13"
UnifiedContext → filtered reality view
```

---

# 10) WHY THIS IS THE KEY SYSTEM (IMPORTANT INSIGHT)

This is what prevents:

### ❌ omniscient LLM behavior

### ❌ narrative hallucination

### ❌ inconsistent world knowledge

### ❌ encounter/combat leakage

### ❌ escalation overreach

---

# 11) FINAL SYSTEM STACK (UPDATED)

```text id="cb14"
IntentFrame
  ↓
AdjudicationDecision
  ↓
ActionPlanner
  ↓
Tools (atomic execution)
  ↓
EventLog (truth ledger)
  ↓
WorldState (reality)
  ↓
ContextBuilder (perception filter)
  ↓
UnifiedContext (what AI sees)
  ↓
LLM / Narrative / UI
```

---

# 🔚 FINAL BOTTOM LINE

You now have a complete closed loop system:

* Tools define reality changes
* Events define truth history
* WorldState defines current reality
* ContextBuilder defines perception
* Encounter/Combat/Escalation define *interpretation layers, not control layers*

Nothing in the system can bypass anything else.

---

If you want the next step, there are only two “architecture completion” pieces left:

1. **NarrativeEngine spec (how UnifiedContext becomes coherent story output without breaking determinism)**
2. **LLM DM constraint spec (how to prevent it from hallucinating outside UnifiedContext)**

Those are the final locks that make this fully production-safe.




Good—this is the point where most systems either become coherent storytelling engines or quietly drift back into “LLM improvisation with structure around it.” The NarrativeEngine is what prevents that drift.

This is **not a storytelling system**. It is a **deterministic rendering layer over UnifiedContext + EventLog**.
