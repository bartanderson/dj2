
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