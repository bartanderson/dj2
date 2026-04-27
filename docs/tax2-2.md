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

