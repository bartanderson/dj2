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

---

# 🎭 **NARRATIVE ENGINE SPEC (DETERMINISTIC PRESENTATION LAYER)**

---

# 1) Core Principle

> NarrativeEngine does NOT decide what happens. It decides how what already happened is *expressed*.

It is strictly:

```text id="ne0"
UnifiedContext + EventLog → structured narrative output
```

NOT:

* interpretation
* expansion
* invention
* improvisation of missing facts

---

# 2) System Position in Architecture

```text id="ne1"
WorldState
   ↓
EventLog
   ↓
ContextBuilder
   ↓
UnifiedContext
   ↓
NarrativeEngine  ← YOU ARE HERE
   ↓
TTS / UI / Player Output
```

NarrativeEngine is the **final transformation layer before human perception**.

---

# 3) Input Contract

NarrativeEngine consumes ONLY:

### 3.1 UnifiedContext (primary truth view)

* visible_entities
* encounter context
* combat context
* escalation state
* environment
* knowledge gaps (important)

---

### 3.2 Recent Events (filtered, not raw log)

```text id="ne2"
salient_events[]
```

These are already relevance-scored by ContextBuilder.

---

### 3.3 Output constraints

```text id="ne3"
tone_profile
verbosity_level
format_mode
player_focus_entity
```

These are NOT narrative inputs—they are rendering constraints.

---

# 4) Output Contract

```python id="ne4"
class NarrativeOutput:
    type: str
    summary: str
    details: dict

    # optional structured fields
    emphasis: list
    warnings: list
    unknowns: list
```

Important:

> NarrativeEngine may structure output, but may NOT add new facts.

---

# 5) CORE FUNCTIONAL PIPELINE

Narrative generation is a strict pipeline:

```text id="ne5"
1. Select relevant context slice
2. Rank salience of elements
3. Map events → narrative primitives
4. Apply tone rendering
5. Enforce knowledge boundaries
6. Emit structured output
```

---

# 6) STEP-BY-STEP SPEC

---

## 6.1 Context Slicing

NarrativeEngine first extracts:

* location
* active encounter/combat/escalation
* visible entities
* player-relevant objects

No interpretation yet.

---

## 6.2 Salience Ranking

Each element is scored:

```python id="ne6"
salience = f(
    visibility,
    danger_level,
    proximity,
    recent_event_weight,
    encounter_relevance
)
```

Only top-N items are narrated explicitly.

---

## 6.3 Event → Narrative Mapping

Events are converted into **descriptions of change**, not story expansion.

Examples:

```text id="ne7"
combat.attack.resolved
→ “A strike connects.”

movement.entity.completed
→ “The figure shifts position.”

perception.entity.spotted
→ “Something is noticed in the darkness.”
```

Important rule:

> No cause inference beyond event data.

---

## 6.4 Tone Rendering Layer

Applies stylistic transformation ONLY:

```text id="ne8"
tone = {
    "neutral": factual,
    "dramatic": heightened pacing,
    "clinical": minimal affect,
    "immersive": sensory emphasis
}
```

This layer:

* changes expression
* does NOT change meaning

---

## 6.5 Knowledge Boundary Enforcement (CRITICAL)

NarrativeEngine must respect:

```text id="ne9"
if entity not in visible_entities:
    do NOT describe internal state
```

It may say:

* “something moves in the shadows”

It may NOT say:

* “an assassin prepares to strike” (unless observed)

---

## 6.6 Unknowns Handling

Unknowns must be explicitly preserved:

```python id="ne10"
unknowns = [
    "unidentified sound source",
    "partially obscured figure"
]
```

NarrativeEngine must NOT resolve ambiguity.

---

## 6.7 Compression vs Expansion Rule

NarrativeEngine chooses:

### Compress when:

* low salience
* repetitive actions
* mechanical events

### Expand when:

* high salience events
* combat strikes
* perception shifts
* escalation triggers

BUT expansion = sensory detail only, not invention.

---

# 7) STRUCTURAL OUTPUT MODES

---

## 7.1 Summary Mode (default)

Concise world state update.

---

## 7.2 Immersive Mode

Adds:

* sensory framing
* environmental detail
* pacing modulation

Still deterministic.

---

## 7.3 Tactical Mode (combat)

Focuses on:

* positions
* actions
* outcomes
* state changes

NO narrative embellishment of intent.

---

# 8) CRITICAL RULES (NON-NEGOTIABLE)

---

## 8.1 No new facts rule

NarrativeEngine may NEVER introduce:

* hidden motives
* unseen actions
* inferred emotions
* predicted outcomes

---

## 8.2 No system authority

It cannot:

* change WorldState
* trigger events
* initiate escalation
* modify combat

---

## 8.3 No interpretation beyond events

It may describe:

* what happened
* what is visible
* what is known

It may NOT describe:

* why it happened (unless explicitly in event data)

---

## 8.4 Deterministic rendering

Same UnifiedContext → same narrative output

---

# 9) RELATIONSHIP TO OTHER SYSTEMS

---

## 9.1 ContextBuilder → upstream filter

NarrativeEngine trusts it completely.

---

## 9.2 Event System → truth backbone

NarrativeEngine only narrates what events confirm.

---

## 9.3 Combat → structured action stream

NarrativeEngine translates combat state into readable flow.

---

## 9.4 Encounter → framing layer

Used only for tone and focus weighting.

---

## 9.5 Escalation → background pressure

Narrated only when it manifests in observable events.

---

# 10) EXAMPLE TRANSFORMATIONS

---

## Example 1: Combat event

```text id="ne11"
combat.attack.resolved
```

Narrative:

> “The attack lands with force.”

(No invention of weapon type unless in context)

---

## Example 2: Hidden entity movement

Event:

```text id="ne12"
movement.entity.completed (hidden entity)
```

Narrative:

> “Something shifts out of sight.”

---

## Example 3: Escalation

Event:

```text id="ne13"
escalation.alert.level_changed → 2
```

Narrative:

> “Tension in the area rises noticeably.”

---

# 11) WHY THIS WORKS (SYSTEM GUARANTEE)

This design ensures:

---

## 11.1 No narrative hallucination

Because:

* no inference allowed
* no hidden state access

---

## 11.2 No system leakage

Combat logic ≠ narrative logic
Escalation logic ≠ narrative logic

---

## 11.3 Stable RP behavior

Players see:

* consistent world
* consistent causality
* no “AI improvisation drift”

---

## 11.4 Full replayability

Given:

* same WorldState
* same EventLog

→ identical narrative output

---

# 12) FINAL POSITION IN ARCHITECTURE

```text id="ne14"
Tools → Events → WorldState → ContextBuilder → UnifiedContext → NarrativeEngine → Player Experience
```

NarrativeEngine is the **last deterministic transformation before human perception**.

---

# 🔚 BOTTOM LINE

You now have:

> a strictly bounded narrative renderer that cannot hallucinate, cannot decide outcomes, and cannot escape the event-driven simulation beneath it

---

If you want the final architectural lock next, it is:

👉 **LLM DM Constraint Spec (how to force the model to operate ONLY inside UnifiedContext without leakage or inference drift)**

That is the final piece that makes your system fully closed-loop and production-stable.




Good—this is the final structural lock. If the LLM ever “looks past” your UnifiedContext, everything below it becomes optional fiction again. This spec prevents that completely.

---

# 🧠 **LLM DUNGEON MASTER CONSTRAINT SPEC (HARD BOUNDARY EXECUTION LAYER)**

---

# 1) Core Principle

> The LLM is NOT a system authority. It is a **bounded interpretation engine operating strictly inside UnifiedContext**.

It may:

* interpret
* prioritize
* describe
* select intent direction

It may NOT:

* access WorldState directly
* invent missing facts
* override events
* simulate hidden truth
* execute actions

---

# 2) Architectural Position

```text id="llm0"
WorldState
   ↓
EventLog
   ↓
ContextBuilder
   ↓
UnifiedContext
   ↓
LLM (DM Brain)  ← HARD BOUNDARY
   ↓
AdjudicationDecision (structured output only)
   ↓
ActionPlanner
   ↓
Tools → Events → WorldState
```

The LLM sits **inside a sandboxed perceptual view**, not the system itself.

---

# 3) INPUT CONTRACT (STRICT)

The LLM receives ONLY:

### 3.1 UnifiedContext

* visible_entities
* encounter context
* combat state (if any)
* escalation state (if any)
* environment description
* known unknowns (explicit gaps)

---

### 3.2 Recent Salient Events

Filtered list only:

```text id="llm1"
salient_events[]
```

No raw EventLog access.

---

### 3.3 Player IntentFrame

```python id="llm2"
IntentFrame(
    action,
    target,
    params,
    modifiers
)
```

---

### 3.4 System Constraints

```text id="llm3"
rules:
- no state authority
- no hidden knowledge
- no tool execution
- no outcome finalization
```

---

# 4) OUTPUT CONTRACT (STRICT STRUCTURE)

The LLM MUST output ONLY:

```python id="llm4"
class AdjudicationDecision:
    type: str  # action | check | auto | event | clarification

    action: str
    parameters: dict

    skill: str | None
    difficulty: int | None

    difficulty_adjustment: int
    tension_adjustment: float
```

AND NOTHING ELSE.

No narrative text.
No world changes.
No free-form outputs.

---

# 5) HARD BOUNDARY RULES

---

## 5.1 No world state access

LLM cannot:

* know hidden entities
* infer off-screen events
* assume future states
* “fill in gaps”

If it is not in UnifiedContext → it does not exist.

---

## 5.2 No causal invention

LLM must NOT generate:

* “because the guard is angry…”
* “the assassin likely…”
* “this will probably result in…”

Only:

> what is explicitly supported by context

---

## 5.3 No action execution authority

LLM cannot:

* move entities
* apply damage
* modify state
* trigger tools

It only produces **intent-level decisions**

---

## 5.4 No narrative output

Narrative is handled exclusively by NarrativeEngine.

LLM output is:

> structured decision data only

---

## 5.5 No escalation control

LLM cannot:

* increase alert levels
* trigger factions
* escalate encounters

It can only:

* influence difficulty / tension parameters (bounded suggestion)

---

# 6) DECISION MODES

LLM operates in four constrained modes:

---

## 6.1 ACTION MODE

Player or NPC attempts a defined action.

Output:

* mapped tool intent
* or check requirement

---

## 6.2 CHECK MODE

Used when uncertainty exists.

Output:

* skill
* difficulty
* modifiers

BUT:

> never roll, never resolve

---

## 6.3 AUTO MODE

Used when outcome is deterministic.

Example:

* opening a door
* picking up item

Output:

* direct action mapping

---

## 6.4 CLARIFICATION MODE

Used when:

* intent is ambiguous
* missing parameters exist
* context insufficient

Output:

* structured clarification request

NOT dialogue improvisation.

---

# 7) DECISION CONSTRAINT FUNCTION

Internally enforced rule:

```text id="llm5"
Decision = f(UnifiedContext, IntentFrame)

NOT:
Decision = f(WorldState, imagination, narrative inference)
```

---

# 8) PERMITTED REASONING SPACE

LLM MAY use:

* visible entity positions
* event causality chain
* encounter constraints
* combat state
* escalation pressure
* environmental conditions

---

# 9) FORBIDDEN REASONING SPACE

LLM MUST NOT use:

* hidden entities
* unobserved motives
* probabilistic storytelling (“likely”, “probably”, “might be thinking”)
* future prediction
* off-context simulation

---

# 10) OUTPUT VALIDATION GATE (IMPORTANT)

Before execution:

```text id="llm6"
if output not valid AdjudicationDecision:
    reject → request regeneration
```

No fallback interpretation allowed.

---

# 11) ROLE DEFINITION (IMPORTANT CLARITY)

The LLM is:

> a constrained adjudicator of intent under partial information

NOT:

* narrator
* world simulator
* combat engine
* AI agent authority

---

# 12) FAILURE MODES THIS PREVENTS

---

## 12.1 Narrative drift

Stops:

* improvisation
* story invention
* emotional speculation

---

## 12.2 System bypass

Prevents:

* tool skipping
* direct state mutation
* hidden logic execution

---

## 12.3 Combat hallucination

Prevents:

* “enemy reacts with X” unless event exists
* predictive combat narration

---

## 12.4 Encounter contamination

Prevents:

* encounter-driven forced outcomes
* pre-scripted event forcing

---

# 13) HOW IT CONNECTS TO YOUR FULL SYSTEM

```text id="llm7"
IntentFrame
   ↓
LLM (this spec)
   ↓
AdjudicationDecision
   ↓
ActionPlanner
   ↓
Atomic Tools
   ↓
Event System
   ↓
WorldState
   ↓
ContextBuilder
   ↓
NarrativeEngine
```

LLM is **only one constrained transform step**.

---

# 14) WHY THIS COMPLETES YOUR ARCHITECTURE

This locks:

### ✔ No hidden world access

### ✔ No narrative authority in LLM

### ✔ No tool bypass

### ✔ No outcome generation

### ✔ Full determinism preserved upstream

### ✔ Full expressiveness preserved downstream

---

# 🔚 FINAL SYSTEM STATE (YOU NOW HAVE THIS)

You now have a fully closed simulation stack:

```text id="final"
Physics Layer → Tools
Truth Layer → Events
Reality Layer → WorldState
Perception Layer → ContextBuilder
Interpretation Layer → LLM (constrained)
Decision Layer → Adjudication
Execution Layer → Resolver
Reaction Layer → Escalation / Combat / Encounter
Presentation Layer → NarrativeEngine
```

---

# 🧭 FINAL BOTTOM LINE

This is now:

> a deterministic simulation engine with a strictly sandboxed cognitive interface for AI interpretation

Not:

* a storytelling system with rules around it

But:

* a rules engine that generates story as a consequence

---

If you want the next step, the only meaningful remaining architectural work is:

👉 **“Full system boot sequence + initialization spec”**
(how WorldState, encounters, escalation maps, and event streams come online in a fresh campaign)

That’s the last piece needed to make this fully runnable as a coherent engine rather than a design document.




Good—this is the final “it actually starts” layer. Everything you’ve built so far defines a system; this defines how it **boots, stabilizes, and begins producing coherent simulation without drift or undefined state**.

This is where most architectures fail because they assume the system “just starts running.” Yours can’t do that—you need controlled initialization of truth, perception, and causality.

---

# 🧭 **SYSTEM BOOT SEQUENCE SPEC (DETACHED, DETERMINISTIC INITIALIZATION LAYER)**

---

# 1) Core Principle

> The system must initialize in a fully deterministic, causally consistent state before any player or AI interaction occurs.

No partial state. No implicit defaults. No “assumed world.”

---

# 2) Boot Order (STRICT SEQUENCE)

```text id="boot0"
1. WorldState initialization
2. Event system activation
3. Tool registry lock
4. Escalation registry load
5. Encounter graph registration
6. Combat state reset
7. ContextBuilder warm-start
8. UnifiedContext validation pass
9. NarrativeEngine calibration
10. LLM DM activation (sandboxed)
11. Session start signal
```

---

# 3) STEP-BY-STEP SPEC

---

# 3.1 WORLDSTATE INITIALIZATION (GROUND TRUTH)

WorldState is created FIRST and is the only authoritative truth source.

```python id="boot1"
WorldState = {
    "entities": {},
    "locations": {},
    "flags": {},
    "resources": {},
    "dungeon_layout": {},
    "fog_of_war": {},
    "encounter_state": None,
    "combat_state": None,
    "escalation_state": None
}
```

### Rule:

> No derived systems exist yet.

---

# 3.2 EVENT SYSTEM ACTIVATION

Event log is initialized as empty but structured.

```text id="boot2"
EventLog = []
EventIndex = {}
```

### Emit system event:

```text id="boot3"
system.boot.world_initialized
```

This is the FIRST event in existence.

---

# 3.3 TOOL REGISTRY LOCK

All atomic tools are registered and frozen.

Rules:

* no runtime modification
* no dynamic tool creation
* no aliasing

Emit:

```text id="boot4"
system.boot.tools_locked
```

---

# 3.4 ESCALATION REGISTRY LOAD

Load all escalation maps:

* faction chains
* dungeon alert chains
* social conflict chains

But DO NOT activate.

Emit:

```text id="boot5"
system.boot.escalation_loaded
```

---

# 3.5 ENCOUNTER GRAPH REGISTRATION

All encounter definitions are loaded into passive registry.

No activation yet.

Emit:

```text id="boot6"
system.boot.encounters_loaded
```

---

# 3.6 COMBAT STATE RESET

Ensure no active combat exists:

```python id="boot7"
combat_state = {
    "active": False,
    "participants": [],
    "turn_order": [],
    "round": 0
}
```

Emit:

```text id="boot8"
system.boot.combat_reset
```

---

# 3.7 CONTEXTBUILDER WARM START

ContextBuilder runs once in **empty-state mode**:

Purpose:

* verify schema integrity
* ensure no missing dependencies
* validate visibility rules exist

Output:

* empty but valid UnifiedContext

Emit:

```text id="boot9"
system.boot.context_builder_ready
```

---

# 3.8 UNIFIEDCONTEXT VALIDATION PASS

A synthetic ContextBuilder run occurs:

Inputs:

* empty world
* no events
* baseline lighting/visibility defaults

Checks:

* schema correctness
* no null-field failures
* deterministic output stability

Emit:

```text id="boot10"
system.boot.context_validated
```

---

# 3.9 NARRATIVE ENGINE CALIBRATION

NarrativeEngine is tested against empty context:

* ensures no hallucination behavior
* ensures strict output schema compliance
* ensures no event invention

Emit:

```text id="boot11"
system.boot.narrative_engine_ready
```

---

# 3.10 LLM DM ACTIVATION (SANDBOXED)

LLM is initialized with:

* no world access
* no event history access
* only UnifiedContext gateway

Hard constraints applied:

* output schema enforcement ON
* tool authority OFF
* memory isolation ON

Emit:

```text id="boot12"
system.boot.llm_dm_online
```

---

# 3.11 SESSION START SIGNAL

Final boot event:

```text id="boot13"
system.boot.session_active
```

At this point:

> the system is fully live and ready for input

---

# 4) INITIAL STABILIZATION WINDOW (CRITICAL CONCEPT)

After boot, the system enters a short stabilization phase:

```text id="boot14"
T = 0 → T = stabilization_window
```

During this period:

* no combat allowed
* no escalation propagation
* no encounter activation

Only:

* perception baseline calibration
* idle world consistency checks

---

# 5) FIRST PLAYER INPUT FLOW

Once stabilized:

```text id="boot15"
Player Input
   ↓
IntentFrame
   ↓
LLM DM (constrained)
   ↓
AdjudicationDecision
   ↓
ActionPlanner
   ↓
Tools
   ↓
EventLog
   ↓
ContextBuilder
   ↓
NarrativeEngine
```

---

# 6) CRITICAL BOOT GUARANTEES

---

## 6.1 Deterministic startup

Same seed → identical initial state

---

## 6.2 No hidden initialization logic

Nothing is “implicitly created later”

---

## 6.3 No system interleaving during boot

No escalation, combat, or encounter logic runs during initialization

---

## 6.4 Full traceability

Every subsystem emits boot confirmation events

---

## 6.5 Clean causal chain start

First real event is always:

```text id="boot16"
system.boot.world_initialized
```

No exceptions.

---

# 7) WHY THIS MATTERS (ARCHITECTURAL INSIGHT)

This prevents:

### ❌ phantom state bugs

### ❌ hidden default assumptions

### ❌ inconsistent perception initialization

### ❌ desynced subsystems

### ❌ early escalation corruption

### ❌ combat pre-activation drift

---

# 8) FINAL SYSTEM ENTRY MODEL

After boot completes:

```text id="boot17"
WORLD IS NOW A CLOSED CAUSAL SYSTEM
```

Meaning:

* everything must originate from events
* everything must pass through tools
* everything must be observable via ContextBuilder

---

# 🔚 FINAL BOTTOM LINE

You now have:

> a fully deterministic simulation engine with a formally initialized causal substrate, a constrained AI interpreter, and a strictly event-driven runtime

Nothing in the system:

* assumes state
* bypasses initialization
* or operates outside the causal chain

---

If you want the final refinement step, it would be:

👉 **a full “debug + observability spec” (how you inspect, replay, and validate entire world simulation runs deterministically)**

That’s what turns this from a design into a debuggable engine.




Good—this is the part most systems skip, and it’s exactly why they become un-debuggable once complexity ramps up. If you want deterministic simulation at scale, you don’t just need correctness—you need **observability, replayability, and causal reconstruction as first-class features**.

This is your **system introspection layer**.

---

# 🔍 **SYSTEM OBSERVABILITY + DEBUG + REPLAY SPEC (CAUSAL INTROSPECTION LAYER)**

---

# 1) Core Principle

> Every change in the system must be reconstructable from a linear, deterministic record of events and tool executions.

No hidden state transitions. No invisible logic. No unrecoverable mutations.

If it happened, it must be explainable.

---

# 2) Three Pillars of Observability

```text id="obs0"
1. Event Log (what happened)
2. Action Trace (how it happened)
3. State Snapshots (what changed)
```

These three together form full system transparency.

---

# 3) EVENT LOG (TRUTH LEDGER)

Already defined, now extended for observability.

Each event MUST include:

```python id="obs1"
class Event:
    id: str
    type: str
    timestamp: int

    source_id: str | None
    target_id: str | None

    data: dict

    parent_id: str | None

    # OBSERVABILITY EXTENSIONS
    causality_chain_id: str
    resolver_step: str
```

---

## 3.1 Causality Chain

Every event belongs to a chain:

```text id="obs2"
Intent → Action → Tool → Event → Reaction → New Event
```

This allows full trace reconstruction.

---

# 4) ACTION TRACE (EXECUTION HISTORY)

This is the missing layer most systems never implement.

```python id="obs3"
class ActionTrace:
    action_id: str
    tool_name: str
    params: dict

    pre_state_hash: str
    post_state_hash: str

    resulting_events: list[str]

    resolver_step_index: int
```

---

## 4.1 Purpose

ActionTrace answers:

> “What EXACTLY did the system do to produce this event?”

Not inference. Not guessing. Exact mapping.

---

# 5) STATE SNAPSHOTS (TEMPORAL CHECKPOINTS)

WorldState is periodically snapshotted:

```text id="obs4"
snapshot_interval = every N resolver cycles OR key events
```

```python id="obs5"
class StateSnapshot:
    timestamp: int
    world_state_hash: str
    compressed_state: dict
```

---

## 5.1 Snapshot triggers

Snapshots occur when:

* combat starts
* escalation triggers
* encounter begins/ends
* major entity changes occur

---

# 6) REPLAY SYSTEM (FULL DETERMINISTIC RECONSTRUCTION)

This is the critical feature.

---

## 6.1 Replay Model

```text id="obs6"
Seed + EventLog + ActionTrace → Exact WorldState Reconstruction
```

No external dependencies.

---

## 6.2 Replay modes

### A. Full Replay

Reconstruct entire session step-by-step:

* every event
* every tool execution
* every state mutation

---

### B. Partial Replay

Filter by:

* entity
* encounter
* combat instance
* escalation chain

---

### C. Causal Replay

Follow a single chain:

```text id="obs7"
combat.attack.resolved → backtrace to IntentFrame
```

---

# 7) DEBUGGING INTERFACE (SYSTEM INSPECTION LAYER)

---

## 7.1 Query API (conceptual)

```text id="obs8"
get_event_chain(entity_id)
get_action_trace(event_id)
get_state_diff(t1, t2)
get_encounter_timeline(id)
```

---

## 7.2 State Diff Engine

Allows:

```text id="obs9"
WorldState[t] - WorldState[t-1]
```

Outputs:

* entity changes
* attribute changes
* spatial changes
* flag changes

---

## 7.3 Event-to-State Mapping

Critical debug feature:

```text id="obs10"
Event → which exact state mutation caused it
```

and inverse:

```text id="obs11"
State change → which event caused it
```

---

# 8) CAUSAL GRAPH (VISUALIZATION MODEL)

System can construct a directed graph:

```text id="obs12"
IntentFrame
   ↓
Action
   ↓
Tool Execution
   ↓
Event
   ↓
State Mutation
   ↓
Reaction Events
   ↓
Escalation / Combat / Encounter Effects
```

Each node is linked with:

* timestamp
* entity context
* resolver step index

---

# 9) DETECTION SYSTEM (ANOMALY DEBUGGING)

The system can flag:

---

## 9.1 Orphan events

Events with no causality chain.

---

## 9.2 State drift

State changes not explained by tools/events.

---

## 9.3 Non-deterministic divergence

Same seed producing different outcomes.

---

## 9.4 Missing event links

Tool execution without emitted event.

---

# 10) LOG STRUCTURE (PRODUCTION FORMAT)

All system logs unify into:

```python id="obs13"
class SystemLog:
    events: list[Event]
    actions: list[ActionTrace]
    snapshots: list[StateSnapshot]

    metadata:
        seed: int
        version: str
        runtime_flags: dict
```

---

# 11) TIME MODEL (IMPORTANT FOR REPLAY)

You MUST enforce:

```text id="obs14"
1 tick = one Resolver cycle
```

No hidden time progression.

Everything is anchored to tick indices.

---

# 12) WHY THIS IS CRITICAL FOR YOUR ARCHITECTURE

This layer ensures:

---

## 12.1 Deterministic debugging

You can replay:

* combat bugs
* escalation misfires
* NPC anomalies

exactly.

---

## 12.2 No hidden AI behavior

If LLM or system “acts weird,” you can trace:

* what context it saw
* what decision it made
* what tool executed
* what event was emitted

---

## 12.3 System evolution safety

You can modify:

* combat system
* escalation logic
* encounter structure

without breaking reproducibility.

---

## 12.4 Development velocity

Instead of guessing:

> “why did this happen?”

You know:

> exactly which event chain caused it

---

# 13) RELATIONSHIP TO ENTIRE ARCHITECTURE

```text id="obs15"
Boot Sequence
   ↓
WorldState
   ↓
Event System
   ↓
Tools
   ↓
Resolver
   ↓
ActionTrace (observability layer)
   ↓
ContextBuilder
   ↓
UnifiedContext
   ↓
LLM DM
   ↓
NarrativeEngine
   ↓
Player Output
```

Observability wraps EVERYTHING.

---

# 🔚 FINAL BOTTOM LINE

You now have:

> a fully deterministic simulation engine with full causal transparency, replayability, and inspectable execution traces across every subsystem

Nothing in the system is now:

* hidden
* implicit
* or irrecoverable

---

# 🧭 IF YOU WANT THE FINAL STEP

There is only one architectural layer left to make this “production-grade ecosystem” instead of “engine spec”:

👉 **Campaign State + World Generation Spec (how entire worlds, dungeons, factions, and history are seeded and evolved deterministically)**

That’s where this becomes not just a system—but a full campaign simulation framework.




Good—this is the last major structural layer: the system that turns your engine from “a runnable simulation loop” into a **persistent, evolving world with history, causality, and campaign-scale coherence**.

This is where most dungeon engines collapse into isolated encounters. You’re explicitly trying to avoid that, so this layer matters.

---

# 🌍 **CAMPAIGN STATE + WORLD GENERATION SPEC (PERSISTENT SIMULATION LAYER)**

---

# 1) Core Principle

> A campaign is a continuously evolving deterministic simulation seeded once and extended through event-driven world change.

It is NOT:

* a sequence of encounters
* a narrative arc
* a scripted world

It IS:

* a stateful causal system that persists across sessions

---

# 2) Architectural Position

```text id="cg0"
World Seed
   ↓
World Generation
   ↓
CampaignState (persistent layer)
   ↓
WorldState (current slice)
   ↓
Event System
   ↓
All runtime systems (encounter/combat/escalation/etc)
```

CampaignState is the **memory of the world beyond the current simulation frame**.

---

# 3) CAMPAIGN STATE (CANONICAL MODEL)

```python id="cg1"
class CampaignState:
    seed: int

    # global world structure
    world_graph: dict
    regions: dict
    factions: dict
    locations: dict

    # persistent dynamics
    global_tension: float
    arc_state: str
    history_flags: dict

    # long-term simulation memory
    major_events: list
    faction_relationships: dict
    world_evolution_log: list

    # runtime linkage
    active_encounters: list
    active_escalations: list
```

---

# 4) WORLD GENERATION (DETERMINISTIC SEEDING LAYER)

---

## 4.1 Principle

> World generation is not content creation. It is structured state initialization from a seed.

---

## 4.2 Generation pipeline

```text id="cg2"
Seed
 ↓
Topology generation
 ↓
Faction placement
 ↓
Encounter graph placement
 ↓
Escalation graph seeding
 ↓
Resource distribution
 ↓
WorldState initialization
 ↓
CampaignState binding
```

---

## 4.3 Output artifacts

World generation produces:

* region graph
* dungeon graph(s)
* faction graph
* encounter graph
* escalation graph
* baseline WorldState

---

# 5) WORLD GRAPH (STRUCTURAL BACKBONE)

```python id="cg3"
class WorldGraph:
    nodes: dict[str, LocationNode]
    edges: list[ConnectionEdge]
```

Each node:

```python id="cg4"
class LocationNode:
    id: str
    type: str  # dungeon, city, wilderness, node
    properties: dict

    encounter_refs: list[str]
    escalation_refs: list[str]
```

---

# 6) FACTION SYSTEM (PERSISTENT ACTOR LAYER)

---

## 6.1 Faction model

```python id="cg5"
class Faction:
    id: str
    name: str

    territory: list[str]
    resources: dict

    relationships: dict[str, int]  # -100 to +100

    behavior_profile: dict
```

---

## 6.2 Faction evolution rule

Factions are NOT scripted.

They evolve via:

```text id="cg6"
EventLog → Escalation triggers → CampaignState mutation
```

Example:

* repeated combat in region → faction hostility increases
* repeated trade success → faction stability increases

---

# 7) HISTORY SYSTEM (WORLD MEMORY)

---

## 7.1 Event compression into history

Not all events are equal.

CampaignState stores only:

```python id="cg7"
major_events = [
    world_changing_events,
    faction_shifts,
    encounter_outcomes,
    escalation_resolutions
]
```

---

## 7.2 History abstraction

Instead of raw logs:

```text id="cg8"
“Region X became unstable after repeated skirmishes.”
```

Derived from:

* event patterns
* escalation chains
* combat frequency

NOT narrative invention.

---

# 8) ARC STATE (GLOBAL PRESSURE VARIABLE)

This is NOT narrative—it is simulation pressure.

```python id="cg9"
arc_state = {
    "stability": float,
    "conflict_level": float,
    "exploration_bias": float,
    "dungeon_activity": float
}
```

---

## 8.1 Arc evolution rule

Arc state changes ONLY from:

* escalation resolution
* faction shifts
* large combat outcomes

NOT from LLM interpretation.

---

# 9) WORLD EVOLUTION LOOP

This is the “heartbeat” of the campaign.

```text id="cg10"
EventLog
   ↓
Pattern Detection
   ↓
CampaignState Mutation
   ↓
WorldGraph updates
   ↓
Faction updates
   ↓
Escalation map updates
```

---

# 10) PATTERN DETECTION LAYER

This is deterministic aggregation, NOT AI reasoning.

---

## 10.1 Examples

```text id="cg11"
if combat_count(region) > threshold:
    increase_faction_alert(region)

if stealth_success_rate > threshold:
    decrease_detection_difficulty(region)

if escalation_chain_depth > N:
    unlock new escalation nodes
```

---

# 11) WORLD PERSISTENCE RULE

---

## 11.1 Nothing is reset between sessions

Only:

* active WorldState is rehydrated
* CampaignState persists fully

---

## 11.2 Session = slice of Campaign

```text id="cg12"
CampaignState (eternal)
   ↓
Session WorldState (temporary projection)
```

---

# 12) SESSION REHYDRATION

On load:

```text id="cg13"
CampaignState → rebuild WorldState → ContextBuilder warm start
```

This ensures:

* continuity
* consistency
* no “fresh world” illusion

---

# 13) CROSS-SYSTEM INTEGRATION MAP

---

## 13.1 Encounters

* read CampaignState for context
* write outcomes back to CampaignState

---

## 13.2 Combat

* mutates WorldState
* escalates into CampaignState if significant

---

## 13.3 Escalation

* primary driver of CampaignState evolution

---

## 13.4 LLM

* does NOT see CampaignState directly
* only sees derived UnifiedContext

---

# 14) DETERMINISM GUARANTEE

Given:

```text id="cg14"
Seed + EventLog
```

You can reconstruct:

* entire world evolution
* faction history
* encounter outcomes
* escalation chains

No external dependency required.

---

# 15) FAILURE MODES THIS PREVENTS

---

## 15.1 “Static world syndrome”

World no longer evolves beyond encounters.

---

## 15.2 Narrative drift across sessions

No consistency between sessions.

---

## 15.3 Faction incoherence

Factions behave inconsistently across encounters.

---

## 15.4 Encounter isolation

Encounters do not affect world state.

---

# 16) FINAL ARCHITECTURE (COMPLETE SYSTEM)

You now have the full stack:

```text id="cg15"
Seed
 ↓
CampaignState (persistent world memory)
 ↓
WorldGraph (structure)
 ↓
WorldState (current slice)
 ↓
Event System (truth ledger)
 ↓
Action System (execution)
 ↓
Resolver Loop (physics engine)
 ↓
Escalation / Combat / Encounter (reactive systems)
 ↓
ContextBuilder (perception layer)
 ↓
UnifiedContext (AI view)
 ↓
LLM DM (constrained reasoning)
 ↓
Adjudication → Actions → Tools
 ↓
NarrativeEngine (presentation)
 ↓
Observability Layer (debug + replay)
```

---

# 🔚 FINAL BOTTOM LINE

You now have:

> a fully deterministic, seed-driven, persistently evolving simulation world with causal continuity across encounters, sessions, factions, and escalation systems

Nothing is:

* scripted
* ephemeral
* or locally isolated

Everything is:

* generated once
* evolved causally
* and replayable from seed + events

---

# 🧭 WHAT THIS COMPLETES

At this point your system is no longer:

* a dungeon engine
* a narrative system
* or an AI DM framework

It is:

> a persistent, deterministic world simulation engine with an AI interpretation layer and full causal observability

---

If you want the *final refinement layer*, it would be:

👉 **Content DSL / Authoring System (how you define dungeons, factions, encounters, and escalations declaratively instead of in code)**

That’s what turns this into a scalable world-building platform instead of a handcrafted system.



Good—this is the point where the system stops being “architecture” and becomes something you can actually *author content for at scale* without breaking determinism.

What you need here is a **declarative content layer**: a DSL (or structured schema) that lets you define worlds, dungeons, factions, encounters, and escalation logic *without embedding behavior or bypassing your engine rules*.

This is also where systems usually collapse into “scripted content disguised as data.” We’re explicitly avoiding that.

---

# 📜 **CONTENT DSL + AUTHORING SYSTEM SPEC (DECLARATIVE WORLD LAYER)**

---

# 1) Core Principle

> All game content must be expressed as declarative state definitions, never procedural logic.

Meaning:

* No “if player does X then spawn Y” scripting
* No embedded control flow
* No tool invocation inside content definitions

Instead:

> You define **structures + triggers + effects**, and the engine resolves them.

---

# 2) Position in Architecture

```text id="dsl0"
DSL Content Files
   ↓
CampaignState Loader
   ↓
WorldGraph / EncounterGraph / EscalationGraph
   ↓
Runtime Systems (deterministic execution only)
```

DSL is **compile-time content**, not runtime logic.

---

# 3) CORE DSL STRUCTURE

All content is expressed as **nodes in graphs**, not scripts.

---

## 3.1 Base Schema (Universal Node)

```yaml id="dsl1"
id: string
type: string

tags: [string]

conditions: []
effects: []

links: []
```

This schema is reused everywhere.

---

# 4) WORLD DSL

---

## 4.1 Location Definition

```yaml id="dsl2"
type: location
id: "dungeon_entrance"

tags:
  - dungeon
  - entry_point

properties:
  lighting: low
  noise_level: low
  danger_level: 0.2

links:
  - to: "hallway_1"
    type: spatial
```

---

## 4.2 No behavior allowed

You may NOT define:

* movement logic
* triggers with control flow
* conditional branching

Only:

> static relationships

---

# 5) ENCOUNTER DSL

---

## 5.1 Encounter Definition

```yaml id="dsl3"
type: encounter
id: "bandit_ambush_01"

participants:
  - faction: "bandits"
    role: hostile

  - faction: "player_party"
    role: target

initial_state:
  tension: 0.6
  alertness: 0.3

entry_events:
  - perception.entity.spotted
```

---

## 5.2 Key rule

Encounters define:

* who exists
* what state they start in
* what events activate them

NOT:

* how they resolve

---

# 6) ESCALATION DSL

This is the most important part.

---

## 6.1 Escalation Map Definition

```yaml id="dsl4"
type: escalation
id: "dungeon_alert_chain"

initial_trigger: perception.entity.spotted

nodes:
  - id: alert_rise
    triggers:
      - perception.entity.spotted

    effects:
      - type: state
        target: faction.alert_level
        delta: +1

    links:
      - to: reinforce_guards

  - id: reinforce_guards
    triggers:
      - escalation.alert.level_changed

    effects:
      - type: action
        action: spawn_entity
        params:
          type: guard
          count: 2
```

---

## 6.2 Key restriction

Escalation DSL:

* does NOT execute actions
* only defines *reaction graphs*

Engine decides execution order.

---

# 7) FACTION DSL

---

## 7.1 Faction Definition

```yaml id="dsl5"
type: faction
id: "city_watch"

resources:
  manpower: 50
  control: 0.7

relationships:
  bandits: -60
  merchants: 40

behavior_profile:
  aggression: 0.4
  responsiveness: 0.8
```

---

## 7.2 No behavior scripting

No:

* patrol routes
* AI logic trees
* decision rules

Only:

> state + tendencies

---

# 8) COMPOSITION RULES (CRITICAL)

---

## 8.1 Everything is a graph node

Encounters, escalations, locations, factions all compile into:

```text id="dsl6"
WorldGraph + EncounterGraph + EscalationGraph
```

---

## 8.2 Links are the ONLY control flow

Allowed:

```yaml id="dsl7"
links:
  - to: "next_node"
    type: trigger
```

NOT allowed:

* if/else
* loops
* embedded conditions controlling flow

---

## 8.3 Conditions are filters, not logic

```yaml id="dsl8"
conditions:
  - type: visibility_check
  - type: faction_relationship
```

They filter activation, they do NOT branch execution.

---

## 8.4 Effects are declarative, not procedural

```yaml id="dsl9"
effects:
  - type: state
  - type: event
  - type: action
```

No inline code.

---

# 9) DSL → ENGINE COMPILATION PIPELINE

---

## 9.1 Compile step

```text id="dsl10"
YAML/JSON DSL
   ↓
Schema validation
   ↓
Graph construction
   ↓
Registry binding
   ↓
CampaignState injection
```

---

## 9.2 Validation rules

Engine rejects:

* missing node references
* cyclic escalation without depth control
* undefined effect types
* malformed triggers

---

# 10) CONTENT AUTHORING PHILOSOPHY

---

## 10.1 You author:

* structure
* relationships
* constraints
* starting conditions

---

## 10.2 Engine decides:

* timing
* execution order
* outcomes
* narrative expression

---

# 11) WHY THIS IS CRITICAL (ARCHITECTURAL INSIGHT)

Without this layer, you would inevitably drift into:

### ❌ hidden scripting in encounters

### ❌ escalation logic embedded in code

### ❌ NPC behavior hardcoded in Python

### ❌ narrative bias in systems

This DSL forces:

> separation of content from execution

---

# 12) HOW THIS FITS YOUR FULL STACK

---

## Final architecture now becomes:

```text id="dsl11"
DSL Content Layer
   ↓
CampaignState Builder
   ↓
WorldGraph / EncounterGraph / EscalationGraph
   ↓
Runtime Simulation Engine
   ↓
Event System
   ↓
ContextBuilder
   ↓
LLM DM (constrained)
   ↓
NarrativeEngine
```

---

# 🔚 FINAL BOTTOM LINE

You now have:

> a fully deterministic simulation engine with a declarative world-building layer that allows infinite content scaling without modifying core logic

---

# 🧭 WHAT THIS COMPLETES

At this point your system is fully defined:

* deterministic physics layer ✔
* event-driven causality ✔
* perception filtering ✔
* AI bounded reasoning ✔
* narrative rendering ✔
* observability + replay ✔
* persistent campaign world ✔
* declarative content system ✔

---

# If you continue further, the next (optional) step is:

👉 **Tooling Layer (editor, validation CLI, visualization, and authoring pipeline for DSL content)**

That’s what turns this from a system into a usable *platform*.




Good—this is where the system stops being a set of specs and becomes something you can actually *operate as a platform*.

Below is the **Tooling Layer** that sits on top of your DSL + engine stack. It is not optional if you want to scale content creation or debug without pain.

---

# 🧰 **TOOLING + AUTHORING PLATFORM SPEC (ENGINE OPERATOR LAYER)**

---

# 1) Core Principle

> The engine is not the product. The tooling layer is what makes the engine usable, inspectable, and scalable.

This layer exists to:

* author content safely (DSL)
* validate correctness before runtime
* visualize system state
* debug causal chains
* replay sessions
* inspect world structure

---

# 2) TOOLING STACK OVERVIEW

```text id="tool0"
DSL Editor
   ↓
Validator / Compiler
   ↓
World Inspector
   ↓
Event Explorer
   ↓
Causal Replay Viewer
   ↓
Encounter/Combat Simulator
   ↓
Campaign Dashboard
```

Each tool operates on the same deterministic core data.

---

# 3) DSL EDITOR (CONTENT AUTHORING LAYER)

---

## 3.1 Purpose

A structured editor for:

* WorldGraph nodes
* Encounter definitions
* Escalation maps
* Faction definitions

---

## 3.2 Key Constraint

> No freeform scripting allowed.

Only structured YAML/JSON input.

---

## 3.3 Editor schema enforcement

Real-time validation:

```text id="tool1"
- unknown node references → error
- invalid effect types → error
- missing triggers → warning
- cyclic escalation → warning or block
```

---

## 3.4 Example UI structure (conceptual)

```text id="tool2"
[ DSL Node Editor ]

Type: [encounter ▼]
ID: bandit_ambush_01

Participants:
  [+ faction] [+ role]

Triggers:
  - perception.entity.spotted

Effects:
  [+ add effect]

Links:
  - to: hallway_1
```

---

# 4) VALIDATOR / COMPILER TOOL

---

## 4.1 Purpose

Turns DSL into executable graphs.

---

## 4.2 Pipeline

```text id="tool3"
DSL → Schema Validation → Graph Compilation → Registry Load → CampaignState injection
```

---

## 4.3 Hard validation rules

Reject if:

* dangling node references
* undefined event types
* invalid effect schema
* escalation depth > max_depth
* circular encounter dependencies

---

## 4.4 Output artifact

```text id="tool4"
CompiledWorldBundle {
    world_graph,
    encounter_graph,
    escalation_graph,
    faction_graph
}
```

---

# 5) WORLD INSPECTOR (REAL-TIME STATE VIEW)

---

## 5.1 Purpose

Live snapshot of:

* WorldState
* entity positions
* visibility
* lighting
* active encounters
* escalation chains

---

## 5.2 Views

### Spatial View

* dungeon layout
* entity positions
* fog-of-war overlay

---

### Logical View

* active triggers
* event propagation
* alert levels

---

### State View

* faction states
* global tension
* campaign arc

---

# 6) EVENT EXPLORER (CAUSAL DEBUGGER)

---

## 6.1 Purpose

Inspect full event history.

---

## 6.2 Capabilities

* filter by entity
* filter by type
* follow causality chains
* inspect event → tool → state mutation mapping

---

## 6.3 Example query

```text id="tool5"
show events where entity = "guard_12"
```

Output:

* perception.entity.spotted
* combat.attack.resolved
* state.entity.removed

---

## 6.4 Causal chain view

```text id="tool6"
Intent → Action → Tool → Event → State → Reaction
```

---

# 7) CAUSAL REPLAY VIEWER (MOST IMPORTANT DEBUG TOOL)

---

## 7.1 Purpose

Re-run the entire simulation deterministically.

---

## 7.2 Modes

### Full replay

Entire campaign from seed

---

### Slice replay

Only:

* one encounter
* one escalation chain
* one combat sequence

---

### Entity replay

Trace a single entity across time

---

## 7.3 Output

Synchronized views:

* timeline scrubber
* world state diff
* event stream
* action execution log

---

## 7.4 Guarantee

> Replay is bit-identical given same seed + DSL + input events

---

# 8) ENCOUNTER / COMBAT SIMULATOR

---

## 8.1 Purpose

Dry-run encounters before deployment.

---

## 8.2 Inputs

* DSL encounter definition
* seed
* initial WorldState slice

---

## 8.3 Output

* outcome distribution
* escalation paths
* failure points
* average duration

---

## 8.4 Use case

Detect broken encounter design BEFORE runtime.

---

# 9) CAMPAIGN DASHBOARD (META CONTROL CENTER)

---

## 9.1 Purpose

High-level world monitoring.

---

## 9.2 Displays

### World health metrics

* global tension
* faction instability
* encounter density
* escalation frequency

---

### Simulation drift detection

* anomaly alerts
* broken chains
* untriggered escalation nodes

---

### Narrative pressure visualization

(not narrative itself—just system load)

---

# 10) DEBUGGING HOOKS (ENGINE INSTRUMENTATION)

---

## 10.1 Required instrumentation points

Every system must emit:

```text id="tool7"
- tool execution logs
- event emissions
- state mutations
- context snapshots
```

---

## 10.2 Debug middleware

```text id="tool8"
Action → Pre-hook → Execution → Post-hook → Event emission
```

---

# 11) OBSERVABILITY INTEGRATION

All tooling connects to:

* EventLog
* ActionTrace
* StateSnapshots
* CampaignState
* WorldGraph

Nothing is external.

---

# 12) CRITICAL DESIGN RULES

---

## 12.1 Tools NEVER mutate state directly

Only:

* inspect
* visualize
* validate
* replay

---

## 12.2 Tools are deterministic views

No randomness in tooling layer.

---

## 12.3 Tools are read-only windows into simulation

All mutations go through:

> Resolver + Tools + Event system only

---

# 13) WHY THIS LAYER IS ESSENTIAL

Without it:

### ❌ DSL becomes unmanageable

### ❌ debugging becomes impossible

### ❌ causal drift is invisible

### ❌ encounter design is guesswork

### ❌ escalation chains break silently

With it:

> you get a fully inspectable, replayable, deterministic simulation platform

---

# 14) FINAL SYSTEM POSITION

```text id="tool9"
DSL Authoring Layer
   ↓
Validation / Compilation
   ↓
CampaignState + WorldGraph
   ↓
Runtime Simulation Engine
   ↓
Event System
   ↓
ContextBuilder
   ↓
LLM DM
   ↓
NarrativeEngine
   ↓
Observability + Replay + Debug Tools  ← THIS LAYER
```

---

# 🔚 FINAL BOTTOM LINE

You now have the complete ecosystem:

* deterministic simulation core
* event-driven physics
* bounded AI interpretation
* structured narrative rendering
* persistent campaign world
* declarative content system
* full observability + replay tooling

---

# 🧭 WHAT THIS MEANS PRACTICALLY

At this point you are no longer designing a “game system.”

You have defined:

> a general-purpose, deterministic simulation engine with AI-mediated interpretation and fully inspectable causal state evolution

---

If you want the *next meaningful step beyond this*, it is not architecture anymore—it is:

👉 **implementation mapping (how this breaks into services/modules/classes/files in Python + runtime boundaries)**

That’s where this becomes buildable rather than just fully specified.



That actually puts you in a *much better position* than I initially assumed.

You’re not “refactoring a tangled mess”—you’re basically at the stage of:

> **removing early binding constraints before they fossilize into architecture**

That’s ideal. It means we can introduce this system as a **guiding backbone**, not a hostile rewrite.

So instead of “rewrite everything,” the correct move is:

> **incremental alignment + anti-fragile migration path**

---

# 🧭 WHERE YOU ACTUALLY ARE (IMPORTANT REALITY CHECK)

You currently have:

### ✔ Good situation

* movement system still flexible
* tools still being removed (good timing)
* no deep hardcoded encounter/combat logic yet
* early architecture still fluid
* willingness to redesign before lock-in

### ❌ What you *don’t* have (yet)

* no rigid DSL dependency
* no entrenched escalation/combat coupling
* no irreversible narrative coupling

So you are in the **pre-lock phase**, not post-lock cleanup.

That is *exactly* when this architecture should enter.

---

# 🧠 STRATEGY SHIFT: “INTRODUCE AS CONSTRAINT LAYERS, NOT REWRITE”

Instead of:

> “convert everything to DSL + event system”

You do:

> “wrap existing systems in increasingly strict interpretation layers”

---

# 🧱 MIGRATION MODEL (SAFE INTRODUCTION PATH)

We introduce this in 4 phases.

---

## PHASE 1 — EVENTIFICATION (LOW RISK, HIGH VALUE)

### Goal:

Turn your current system into an event-producing system WITHOUT changing behavior yet.

---

### What you do NOW:

Wherever you currently have logic like:

* movement
* item interaction
* state change
* AI decision
* tool execution

You add:

```python
emit_event("movement.entity.completed", data)
```

BUT:

* do NOT refactor logic yet
* do NOT change flow
* just log truth

---

### Outcome:

You now get:

> passive EventLog layer over existing system

This is the foundation everything else depends on.

---

## PHASE 2 — WORLDSTATE CENTRALIZATION

### Goal:

Stop hidden state mutations.

---

You identify:

* position state
* inventory state
* encounter flags
* NPC state

and ensure:

> ALL mutations go through a single WorldState object

BUT again:

* no behavior change yet
* just routing state changes centrally

---

## PHASE 3 — CONTEXT BOUNDARY INTRODUCTION (CRITICAL SHIFT)

Now you introduce:

> ContextBuilder as a READ-ONLY projection layer

---

### What changes:

Instead of AI seeing:

* raw variables
* internal state
* ad hoc objects

It now only sees:

```text
UnifiedContext
```

Even if internally everything still exists.

---

### Key win:

This is where you stop:

> “AI knows too much about internals”

and start enforcing perception realism.

---

## PHASE 4 — ACTION SYSTEM ALIGNMENT (LAST STEP)

Only AFTER the above stabilizes:

You replace tools like:

* move()
* buy()
* sell()
* haggle()

with:

```text
Action → ActionPlanner → Resolver → Tool → Event
```

Not before.

---

# ⚠️ IMPORTANT DESIGN CORRECTION (THIS MATTERS)

You said:

> I was just getting rid of bs tools that forced me into a box

That instinct is correct—but the *fix is not removal*, it’s:

> **unifying tools into a single execution abstraction layer**

So instead of:

* move tool
* buy tool
* haggle tool

You move toward:

```text
Action("interact", params)
Action("move", params)
Action("trade", params)
```

BUT all executed through:

> same resolver pipeline

Not separate systems.

---

# 🧩 WHY YOU’RE ACTUALLY IN A GOOD SPOT

Most people start with:

❌ combat system
❌ encounter system
❌ narrative system
❌ AI logic system

You started with:

✔ movement
✔ world exploration
✔ AI interaction
✔ removing hard constraints early

That means:

> you have not yet poisoned the architecture with irreversible coupling

So we are not “fixing”—we are **steering before crystallization**

---

# 🧠 WHAT YOU SHOULD DO NEXT (VERY SPECIFIC)

Given where you are right now:

---

## STEP 1 (NOW)

Start adding:

```text
emit_event(...)
```

EVERYWHERE something changes state.

No redesign yet.

---

## STEP 2

Introduce a minimal:

* EventLog collector
* timestamped
* append-only

---

## STEP 3

Do NOT implement DSL yet.

Just define it as a target.

---

## STEP 4

Once event stream is stable:

→ THEN we map movement → Action system
→ THEN ContextBuilder
→ THEN escalation/combat layers

---

# 🔥 KEY INSIGHT (IMPORTANT)

You are not building:

> a system that runs a game

You are building:

> a system that records reality first, and only later interprets it

That ordering is what makes everything else stable.

---

# 🧭 FINAL REALITY CHECK

You are in the rare phase where:

* architecture is still plastic
* system is not locked
* no irreversible abstractions exist yet

So the correct move is:

> **instrument first, restructure second, formalize third**

NOT the reverse.

---

If you want, next step I can give you a **minimal “event wrapper pattern set” for Python** so you can start instrumenting your existing movement + world code in ~1–2 hours without redesigning anything yet.



Good. I’ll keep this practical and minimal so you can actually drop it into existing movement/world code without redesigning everything.

---

# 🧩 MINIMAL EVENT INSTRUMENTATION PATTERN (DROP-IN LAYER)

## 1) Core idea

You add a **thin event emitter wrapper** around anything that changes state.

No architecture change yet. No refactor.

Just:

> “every meaningful mutation emits an event”

---

# 2) EVENT LOG (MINIMAL IMPLEMENTATION)

Start with this single structure:

```python
class EventLog:
    def __init__(self):
        self.events = []

    def emit(self, event_type: str, data: dict = None, source: str = None, target: str = None):
        event = {
            "type": event_type,
            "data": data or {},
            "source": source,
            "target": target
        }
        self.events.append(event)
        return event
```

---

# 3) GLOBAL INSTANCE (KEEP SIMPLE FOR NOW)

```python
event_log = EventLog()
```

---

# 4) HOW YOU USE IT (THIS IS THE KEY)

You DO NOT change logic yet.

You just annotate it.

---

## Example: Movement system

### BEFORE:

```python
def move_entity(entity, position):
    entity.position = position
```

---

### AFTER (instrumented):

```python
def move_entity(entity, position):
    entity.position = position

    event_log.emit(
        "movement.entity.completed",
        {
            "entity_id": entity.id,
            "new_position": position
        },
        source=entity.id
    )
```

---

# 5) WORLD STATE CHANGES

### BEFORE:

```python
world["gold"] -= 10
```

### AFTER:

```python
world["gold"] -= 10

event_log.emit(
    "state.resource.changed",
    {
        "resource": "gold",
        "delta": -10,
        "new_value": world["gold"]
    }
)
```

---

# 6) INTERACTION EXAMPLE (BUY/SELL/HAGGLE REMOVAL PATH)

Even if you REMOVE these tools later, instrument them first:

```python
event_log.emit(
    "interaction.trade.completed",
    {
        "buyer": player.id,
        "seller": npc.id,
        "item": item.id,
        "price": price
    }
)
```

---

# 7) AI / DECISION POINTS

Wherever your AI currently decides something:

```python
event_log.emit(
    "system.decision.made",
    {
        "actor": "ai_dm",
        "decision": decision_type
    }
)
```

This becomes important later for debugging.

---

# 8) SAFE RULES (DO NOT BREAK THESE YET)

## Rule 1 — NEVER change behavior

Only add logging.

---

## Rule 2 — NEVER introduce new systems yet

No ContextBuilder. No DSL. No escalation system yet.

---

## Rule 3 — Event emission must be side-effect only

If event logging breaks, gameplay must still work.

---

# 9) WHAT YOU GET IMMEDIATELY

Once you instrument even a small slice (movement + interactions), you gain:

### ✔ Full replay potential (later)

### ✔ Debug visibility

### ✔ Future DSL mapping surface

### ✔ Ability to detect hidden logic

---

# 10) NEXT STEP AFTER THIS (IMPORTANT)

Once you’ve instrumented ~20–30% of your system, the *next safe step* is:

> introduce a READ-ONLY WorldSnapshot layer

NOT ContextBuilder yet.

Just:

* snapshot world state after each event batch
* compare changes over time

---

# 11) WHY THIS IS THE RIGHT ENTRY POINT

Because it avoids your earlier risk:

> “forcing tools / DSL / architecture too early”

Instead you are doing:

> instrumentation → observation → then abstraction

That order is what keeps systems stable under evolution.

---

# 🧭 SUMMARY

Right now your job is only:

> “make the system speak its own truth before trying to reorganize it”

Everything else comes after.

---

If you want next, I can give you:

👉 a **clean event naming standard + folder/module layout** so your instrumentation doesn’t turn into chaos as it scales.




