# AI Layer Opportunities (Post-Architecture Review)

This document captures concrete opportunities identified during a 2026-06-26 review
of how modern AI capabilities align with the existing dj2 architecture. Nothing here
requires changing the constitution or authority boundaries. These are implementation
refinements that the architecture was already shaped to support.

Captured from a ChatGPT + Claude review session. Worth acting on when AI layer
implementation begins (Session 3+).

---

## 1. Tool-Calling DM: Curious Investigator, Not Omniscient Narrator

**The old shape:** Build a large context dump (room + inventory + quests + NPCs +
lighting + events + ...) and send it to the model every turn.

**The better shape:** Expose world engine capabilities as tools. The model requests
only what it needs.

Example tool surface:
- `look()` — visible entities in current location
- `get_lighting()` — current lighting state
- `get_exits()` — available movement options
- `inspect(target)` — examine a specific object/entity
- `talk_to(npc_id)` — initiate dialogue
- `query_recent_events(limit)` — pull from EventLog
- `query_character_knowledge(npc_id)` — what does this NPC know?
- `get_inventory()` — player inventory
- `get_quest_state()` — active quests

**Why this fits:** The model behaves like a human DM consulting notes and maps as
needed, rather than holding the entire campaign in working memory. ContextBuilder
already computes these slices deterministically — the tools just expose them.

**Authority boundary:** All tools are read-only queries. No tool mutates WorldState.
Mutations still flow through adjudication → SessionManager → WorldController only.

---

## 2. EventLog as AI Memory

**The old shape:** Stuff recent events into every prompt as context.

**The better shape:** Let the model query the EventLog directly via tool calls when
it needs historical context.

```
"What happened in this room before?"
→ query_recent_events(location="crypt_3", limit=5)
→ [torch extinguished, guard alerted, idol stolen]
```

```
"What does the innkeeper know?"
→ query_character_knowledge("innkeeper_maren")
→ [heard rumor of missing merchant, saw party enter last night]
```

**Why this fits:** EventLog is already the authoritative causal history. This just
makes it queryable by the AI layer instead of pre-assembled into prompts.

---

## 3. Structured Outputs for Intent/Adjudication

**The old shape:** Parse free-text player intent from LLM output.

**The better shape:** Model produces structured intent directly.

```json
{ "intent": "search", "target": "oak_desk" }
{ "intent": "move", "direction": "north" }
{ "intent": "attack", "target": "guard_01", "method": "sword" }
```

Adjudication engine receives a typed AdjudicationRequest, not parsed text.
If the action is invalid (no iron door exists), the engine returns:
```json
{ "success": false, "reason": "No iron door visible from current position." }
```
Model narrates the failure. World stays authoritative.

**Why this fits:** Your adjudication engine was already designed to receive validated
intent. Structured outputs close the gap between model output and engine input without
any architectural change.

---

## 4. NPCs as Deterministic State, LLM as Renderer

**The old shape:** Consider giving each NPC its own AI instance or large personality prompt.

**The better shape:** NPC state is fully deterministic:
- goals
- relationships
- knowledge (from EventLog)
- schedule
- current mood/emotional state
- faction standing
- inventory

The LLM is only invoked when the NPC needs to speak. The prompt becomes:

```
You are [NPC name], a blacksmith in Thornwall.

Your current state:
- Goals: sell the damascus blade, avoid the tax collector
- Mood: suspicious (stranger in town after the robbery)
- Known facts: [from query_character_knowledge()]
- Recent relevant events: [from EventLog query]

Player just said: "I'm looking for work."

Generate one response in character. Do not invent facts not listed above.
```

**Why this fits:** Keeps NPC behavior deterministic and consistent. The LLM renders
the NPC's state into dialogue — it doesn't become the NPC. Cheaper, faster, more
consistent across sessions.

---

## 5. Dynamic Context Retrieval in ContextBuilder

**The old shape:** ContextBuilder always assembles the full UnifiedContext.

**The better shape:** ContextBuilder can respond to specific retrieval requests from
the AI layer, returning only the requested slices.

This doesn't change ContextBuilder's authority or determinism — it just adds a
query interface alongside the existing full-build path. Full build still used for
UI rendering. Slice queries used for AI tool calls.

**Implementation note:** Low priority — full build is fine for v1. Add slice queries
when context window cost becomes measurable.

---

## 6. Persona (or similar) for UI Layer

Persona (https://github.com/runtypelabs/persona) is a drop-in streaming chat UI
widget. Zero framework dependencies, SSE-based, includes voice I/O, artifact panels,
tool approval dialogs, and markdown rendering.

**What it replaces:** Weeks of building chat window, streaming renderer, markdown,
voice controls, panel management, loading states.

**What it doesn't touch:** Everything else. Your simulation, EventLog, adjudication,
ContextBuilder, WorldState — none of it.

**Fit assessment:** Strong. Your backend already produces streaming outputs. Persona
sits above your DM presentation layer and below the browser. Evaluate seriously when
UI layer work begins (Session 4).

**Caveat:** Don't adopt because it's AI-adjacent. Adopt because it saves UI build
time. The game engine is the interesting part.

---

## 7. Trust Boundary Reminder (Constitutional)

Tool-calling puts the model in an active loop rather than at the end of a pipeline.
Before implementing:

- All AI-invokable tools must be **read-only queries** — no world mutation
- Mutation path remains: adjudication → SessionManager → WorldController → EventLog
- Structured intent output from model enters adjudication as an AdjudicationRequest,
  not as a direct world action
- Model never calls a tool that bypasses the authority hierarchy

This is compatible with 00A. State it explicitly in the AI layer design doc when
that subsystem gets its own spec.

---

## When to Act On This

- Items 1-4 (tool-calling, EventLog memory, structured outputs, NPC rendering):
  Address when implementing the AI/DM layer. These change how you structure the
  AI integration, not the layers below it.

- Item 5 (dynamic ContextBuilder queries): Defer until context window cost is
  measured in practice.

- Item 6 (Persona UI): Evaluate at Session 4 (UI contract). Don't build custom
  chat UI before checking if Persona fits.

- Item 7 (trust boundary): Document explicitly when the AI layer gets its own
  design spec.
