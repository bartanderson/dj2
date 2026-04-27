Good instinct—this is exactly the kind of system that can add depth but will absolutely create noise if introduced too early. I’ll give you:

Drop-in spec updates (Escalation integration)
Minimal hooks only (no overreach)
Explicit “do not implement yet” gates
🔧 UPDATED / NEW SECTIONS (Escalation Integration)
3.4 Execution Bucket (UPDATED)
3.4 Execution Bucket (Deterministic Engine)

NEW CORE LAYER

ActionPlanner
ActionQueue
Resolver Loop
Reaction system
Interrupt system
Tool execution (via SessionManager)

Escalation System (NEW)

The Escalation System is a deterministic consequence engine that reacts to events and WorldState changes to produce structured, bounded state evolution over time.

It operates strictly within the Execution layer and has full authority ONLY through:
- ActionQueue (via actions)
- EventSystem (via events)
- SessionManager (via controlled state updates)

It does NOT:
- interpret intent
- make decisions
- access LLM reasoning
8. Resolver Loop (UPDATED — CRITICAL)
8. Resolver Loop (Execution Engine)

Authoritative execution system

Order of operations (NON-NEGOTIABLE):

1. Pre-reactions
2. Action execution
3. Lighting update
4. Visibility update
5. Sound propagation
6. Awareness update
7. Post-reactions
8. Interrupt check
9. Escalation Step (NEW)
8.1 Escalation Step (NEW)
8.1 Escalation Step

Purpose:
Process active escalation maps based on event_log and WorldState to produce deterministic consequences.

Inputs:
- WorldState (current)
- event_log (from current resolver cycle)

Behavior:
- Evaluate active escalation nodes
- Validate triggers and conditions
- Execute effects via:
  - ActionQueue.enqueue()
  - EventSystem.trigger()
  - SessionManager.apply_state_update()

Constraints:
- Must be deterministic
- Must be bounded (max_depth per escalation)
- Must not loop infinitely
- Must not directly modify WorldState outside SessionManager

Outputs:
- Additional actions/events/state updates applied through standard execution pathways
9. Tool System (UPDATED — CLARIFICATION)
9. Tool System

Contract
{
    "success": bool,
    "trigger": str | None,
    "data": dict
}

SessionManager Role (UPDATED)

- validates tool calls
- applies rules
- mutates WorldState
- returns results

Escalation System Integration:
- Escalation effects that modify state MUST go through SessionManager
- No direct mutation allowed outside this pathway
10. Reaction System (UPDATED — BOUNDARY)
10. Reaction System

Immediate, non-queued execution

Rules:
- executed immediately
- may interrupt
- depend on visibility + awareness

Boundary with Escalation:
- Reactions are immediate and local
- Escalation is deferred and systemic
- Reactions may generate events that trigger escalation
- Escalation MUST NOT execute as a reaction
11. Interrupt System (UPDATED — CLARITY)
11. Interrupt System

Triggers:
- enemy_spotted
- trap_detected
- trap_triggered

Behavior:
- may clear queue
- may start combat
- may alter state

Integration with Escalation:
- Interrupt-triggered events are valid escalation triggers
- Escalation occurs AFTER interrupt resolution within Resolver order
15. AI Awareness System (UPDATED — HOOK)
15. AI Awareness System

Shared Group Awareness
{
    "player_last_seen": (x,y),
    "alert_level": int
}

Integration with Escalation:
- alert_level changes may trigger escalation maps
- escalation may modify alert_level through state updates

Behavior Scaling
Alert   Behavior
0   patrol
1   investigate
2+  pursue/attack
16. Combat System (UPDATED — CONSISTENCY)
16. Combat System (Integrated)

Uses SAME action system
same queue
same resolver
turn-gated

Combat + Escalation Interaction:
- Combat events (damage, death, alarm) may trigger escalation
- Escalation may introduce reinforcements or environmental changes
- Escalation does NOT control turn order or combat resolution

Combat Rules:
- only active actor can enqueue
- reactions still active
- interrupts still valid
19. Determinism Guarantees (UPDATED)
19. Determinism Guarantees

Rule    Enforced By

No randomness in LLM    AdjudicationEngine
No state mutation outside SessionManager    Architecture
Ordered execution   Resolver
Single context source   ContextBuilder

Escalation determinism:
- driven only by event_log + WorldState
- no dependency on LLM output
- bounded execution via max_depth
21. Final Mental Model (UPDATED)
21. Final Mental Model

WorldState = Reality
SessionManager = Physics
Resolver = Execution Engine
Adjudication = Judgment
LLM = Voice of the DM
UnifiedContext = Perception
CampaignState = Story Momentum

Latent Expansion = Hidden possibility space (non-authoritative)
Escalation System = Deterministic consequence engine (state evolution)
🧠 RELATION TO LATENT EXPANSION (ADD THIS NOTE)

Add to 3.3 or as a short cross-reference:

Latent Expansion vs Escalation:

Latent Expansion:
- operates BEFORE execution
- generates possibilities
- influences interpretation only

Escalation System:
- operates AFTER execution
- reacts to actual events
- produces real consequences

They are strictly separated and communicate ONLY through:
- player actions
- event_log
- WorldState
🚧 WHEN TO INTEGRATE (THIS IS THE IMPORTANT PART)

Do NOT implement this yet.

You should integrate Escalation ONLY when all of the following are stable:

✅ REQUIRED BEFORE ESCALATION
1. Resolver Loop is final
order is fixed
no reordering planned
2. Event system exists and is reliable

You need:

event_log: list[str]

And:

consistent naming
no duplication
deterministic emission
3. Combat system is functional

Not perfect, but:

actions execute correctly
interrupts work
reactions fire
4. Awareness system is stable

Because escalation heavily depends on:

alert levels
detection events
❌ DO NOT ADD IF:
you're still changing action structure
interrupts are unstable
event naming is inconsistent
combat loop is incomplete
🧪 WHEN TO START (MINIMAL ENTRY POINT)

When ready:

Step 1 — Skeleton only
registry
activation hook
empty escalation step
Step 2 — ONE map only

Example:

“noise → guard investigation”
Step 3 — Validate:
deterministic replay
no duplicate triggers
no race conditions
Step 4 — Expand slowly
⚠️ Final Guidance (based on your system maturity)

Right now, based on your trajectory:

Latent Expansion comes AFTER combat stabilizes
Escalation comes AFTER events stabilize

So order should be:

1. Combat (full loop)
2. Event system normalization
3. Escalation (minimal)
4. Latent Expansion (targeted use)
Bottom line
Escalation is real consequences
Latent is inferred structure
They only connect through events and state
Add escalation only when your execution layer is trustworthy

If you want next, I can:

→ define your first 2–3 escalation maps tailored to your dungeon + AI awareness system

Those will expose whether your event model is actually solid.
---------------------------------------------------
Alright—this is the point where we stop talking conceptually and install this as a first-class system inside your engine.
What follows is a production-ready Escalation System spec that cleanly integrates with:


WorldState


Resolver Loop


Event System


Reaction System


CampaignState


your deterministic guarantees


No hand-waving—this is designed to drop in.

1. Design Goals (Non-Negotiable)
This implementation enforces:


Deterministic execution only


No AI authority over outcomes


Escalation = system-driven, not narrative-driven


Composable + reusable across encounters


Bounded branching (no explosion)



2. Core Architecture Overview
We introduce a new subsystem:
EscalationSystem    ├── EscalationRegistry    ├── ActiveEscalations    ├── EscalationResolver (hooks into Resolver Loop)

3. Data Model (Authoritative)
3.1 EscalationMap
class EscalationMap:    id: str    initial_trigger: str              # event name    priority: int                     # conflict resolution    max_depth: int                    # prevents runaway chains    nodes: dict[str, "EscalationNode"]    # Optional gating    conditions: list[Callable] = None  # WorldState predicates

3.2 EscalationNode
class EscalationNode:    id: str    timeframe: str  # "immediate" | "short" | "long"    # Activation    triggers: list[str]              # events OR state flags    conditions: list[Callable]       # must pass to activate    # Deterministic execution    effects: list["EscalationEffect"]    # Graph structure    next_nodes: list[str]    # Exit ramps (alternative transitions)    exit_ramps: list[str]    # Control    once: bool = True    cooldown: int = 0                # ticks before reactivation

3.3 EscalationEffect
This is the bridge into your deterministic system.
class EscalationEffect:    type: str  # "action" | "event" | "state"    # For action execution    action: "Action" | None = None    # For event triggering    event: str | None = None    # For direct state mutation (rare, controlled)    state_update: dict | None = None

3.4 ActiveEscalation
class ActiveEscalation:    map_id: str    active_nodes: set[str]    completed_nodes: set[str]    depth: int = 0

4. Registry + Activation
4.1 Registry
class EscalationRegistry:    def __init__(self):        self.maps: dict[str, EscalationMap] = {}    def register(self, escalation_map: EscalationMap):        self.maps[escalation_map.id] = escalation_map

4.2 Activation Hook (Event System)
This is critical.
def handle_event(event_name: str, world_state: WorldState):    for map in registry.maps.values():        if map.initial_trigger != event_name:            continue        if map.conditions and not all(cond(world_state) for cond in map.conditions):            continue        activate_escalation(map)

4.3 Activate Escalation
def activate_escalation(map: EscalationMap):    active = ActiveEscalation(        map_id=map.id,        active_nodes=set()    )    # Seed initial nodes    for node_id, node in map.nodes.items():        if map.initial_trigger in node.triggers:            active.active_nodes.add(node_id)    ACTIVE_ESCALATIONS.append(active)

5. Resolver Integration (Critical)
This runs inside your Resolver Loop, AFTER standard execution.
Hook point:
Resolver Loop:1. Pre-reactions2. Action execution3. Lighting4. Visibility5. Sound6. Awareness7. Post-reactions8. Interrupt check9. 🔥 Escalation Step (NEW)

5.1 Escalation Step
def process_escalations(world_state: WorldState, event_log: list[str]):    for active in ACTIVE_ESCALATIONS:        map = registry.maps[active.map_id]        next_active_nodes = set()        for node_id in active.active_nodes:            node = map.nodes[node_id]            if node.once and node_id in active.completed_nodes:                continue            if not all(trigger in event_log for trigger in node.triggers):                continue            if node.conditions and not all(cond(world_state) for cond in node.conditions):                continue            # EXECUTE EFFECTS            for effect in node.effects:                apply_effect(effect)            active.completed_nodes.add(node_id)            # Queue next nodes            for next_id in node.next_nodes:                next_active_nodes.add(next_id)            # Exit ramps are conditionally activated elsewhere            for ramp_id in node.exit_ramps:                if should_activate_exit_ramp(ramp_id, world_state):                    next_active_nodes.add(ramp_id)        active.active_nodes = next_active_nodes        active.depth += 1        # Safety cutoff        if active.depth > map.max_depth:            ACTIVE_ESCALATIONS.remove(active)

6. Effect Execution (Bridging Layer)
6.1 Apply Effect
def apply_effect(effect: EscalationEffect):    if effect.type == "action":        ActionQueue.enqueue(effect.action)    elif effect.type == "event":        EventSystem.trigger(effect.event)    elif effect.type == "state":        SessionManager.apply_state_update(effect.state_update)

7. Exit Ramp Logic (Controlled)
Exit ramps must NOT be arbitrary.
7.1 Gate Function
def should_activate_exit_ramp(node_id: str, world_state: WorldState) -> bool:    # Example logic:    return (        world_state.tension < 0.5 or        world_state.player_actions_recently_deescalatory    )

7.2 Important Constraint
Exit ramps:


Are system-evaluated


NOT AI-decided


AI can only influence inputs that affect conditions



8. Example (Fully Wired)
“Peace Talks Violence” Map
EscalationMap(    id="peace_talks_violence",    initial_trigger="advisor_attacked",    max_depth=3,    nodes={        "combat_start": EscalationNode(            id="combat_start",            timeframe="immediate",            triggers=["advisor_attacked"],            effects=[                EscalationEffect(                    type="action",                    action=Action("spawn_guards", {"count": 2})                ),                EscalationEffect(                    type="state",                    state_update={"alert_level": 2}                )            ],            next_nodes=["lockdown"],            exit_ramps=["defuse"]        ),        "lockdown": EscalationNode(            id="lockdown",            timeframe="short",            triggers=["guards_alerted"],            effects=[                EscalationEffect(                    type="action",                    action=Action("lock_area")                )            ],            next_nodes=["manhunt"]        ),        "manhunt": EscalationNode(            id="manhunt",            timeframe="long",            triggers=["players_escape"],            effects=[                EscalationEffect(                    type="state",                    state_update={"faction_hostility": +3}                )            ],            next_nodes=[]        ),        # EXIT RAMP        "defuse": EscalationNode(            id="defuse",            timeframe="immediate",            triggers=["advisor_attacked"],            conditions=[                lambda ws: ws.npc_traits["advisor"] == "charismatic"            ],            effects=[                EscalationEffect(                    type="state",                    state_update={"tension": -0.3}                )            ],            next_nodes=[]        )    })

9. Risk Matrix Integration (Hook Point)
This influences escalation selection—not execution.
Example:
def get_relevant_escalations(event):    risk = CampaignState.risk_profile    # prioritize high-risk domains    if ("npc_survival", "combat_style") in risk.high_risk_pairs:        return ["peace_talks_violence"]

10. What You Now Have
This system gives you:
Deterministic


All escalation effects go through ActionQueue / SessionManager


Reactive


Triggered by real events, not scripts


Bounded


max_depth + node control


Expressive


Supports:


guards


factions


merchants


dungeon reactions


political shifts




AI-Compatible


AI influences:


intent


tone


pacing




NEVER outcomes
Immediate Next Step (Recommended)

Implement in this exact order:

EscalationRegistry + Map loading
Event hook → activation
Resolver escalation step
One test map (like above)
Run:
combat trigger
verify deterministic propagation

If you want, next I can:

Integrate this with your Encounter System
Or wire it into NPC agents + faction behavior
Or define a DSL/JSON format so you can author escalation maps without touching code

That’s where this becomes a real content pipeline instead of a hardcoded system.

Short answer: **I don’t need it to design the escalation system—but I *do* need it to integrate correctly without creating duplication or conflicts.**

Right now, we’ve built escalation as a **parallel reactive layer**. Your encounter system is likely already doing some of this:

* spawning enemies
* triggering combat
* managing hostility / states
* possibly handling pacing or “when things kick off”

If we don’t reconcile them, you’ll end up with:

### What goes wrong without integration

* **Double triggers**

  * Encounter starts combat
  * Escalation also starts combat
    → race conditions / redundant actions

* **Split authority**

  * Encounter system controls enemies
  * Escalation system mutates faction hostility
    → incoherent world behavior

* **Broken mental model**

  * You won’t know:

    * “Is this an encounter?”
    * “Or an escalation?”
    * “Or both?”

---

# The Correct Relationship (This is the key)

You want a **clear hierarchy**, not two competing systems.

## Recommended Model

```text
Encounter System = Structured scenario container
Escalation System = Dynamic consequence engine
```

### In practice:

* **Encounter defines:**

  * participants
  * initial conditions
  * goals
  * boundaries

* **Escalation defines:**

  * what happens when things go wrong (or right)
  * how the situation evolves over time
  * how the world reacts beyond the encounter

---

# Integration Pattern (Clean + Scalable)

## Option A (Recommended)

### Encounters OWN Escalation Maps

```python
class Encounter:
    id: str
    entities: list
    initial_state: dict
    
    escalation_maps: list[str]  # references to EscalationRegistry
```

### Flow:

1. Encounter starts
2. Registers its escalation maps
3. Escalation system activates based on events

---

## Option B (Global Escalation Layer)

* Escalations live globally (factions, world events)
* Encounters just trigger events

Use this for:

* faction reactions
* city-wide consequences
* long-term campaign shifts

---

## Best Practice = BOTH

```text
Encounter-level escalation (local)
+
World-level escalation (global)
```

---

# Where I Need Your Encounter System

To integrate properly, I need to see:

### 1. Trigger points

* What starts an encounter?
* Events? proximity? AI decision?

### 2. State ownership

* Who controls:

  * hostility?
  * combat start?
  * resolution?

### 3. Lifecycle

* Start → Active → End
* What defines “end”?

### 4. Existing reactions

* Do you already have:

  * guard response logic?
  * reinforcement logic?
  * flee / surrender logic?

---

# What I Will Do With It

Once I see your encounter system, I will:

### 1. Remove overlap

* Decide:

  * encounter handles X
  * escalation handles Y

### 2. Define boundaries

Example:

```text
Encounter:
    "guards vs players in room"

Escalation:
    "entire dungeon goes on alert"
```

---

### 3. Wire event flow cleanly

```text
Encounter → triggers event → Escalation reacts
Escalation → injects actions → Encounter evolves
```

---

### 4. Prevent conflicts

* single source of truth for:

  * combat start
  * entity control
  * faction state

---

# My Recommendation (based on your architecture)

Given how disciplined your system already is:

> **Encounters should NOT contain escalation logic internally**

They should:

* declare escalation maps
* emit events
* react to world changes

This keeps:

* encounters modular
* escalation reusable across contexts

---

# Bottom Line

* I can continue without it—but that risks misalignment
* If you want this to be **clean, scalable, and not fight itself later**, I should see it now

---

If you send it, I’ll do:

> **full integration pass**

* exact hook points
* removal of redundancy
* unified event flow
* and a clean mental model that fits your 7-phase system

That’s the point where this becomes a *cohesive engine*, not layered features.
