# Aspirational Design Intent

This document captures the substantive aspirations and non-negotiable constraints
of the dj2 system in a form intended to inform coding decisions over time.

It is NOT a spec or an ordered plan. It is a compass.

Use it when deciding where something goes, whether a shortcut is acceptable,
or whether a new capability fits the vision. Items here represent things we
want to remain true about the system as it grows — aspirational but load-bearing.

It is also intended to be machine-readable eventually: the Determined analysis
tool should be able to ingest this and cross-reference structural findings
against these constraints to catch architectural drift before it becomes habit.

Last updated: 2026-06-26

---

## A. The Core Experience Goal

A persistent, living world where:
- NPCs have schedules and goals that evolve without player presence
- Factions gain and lose influence from events, not from scripted triggers
- Events ripple naturally through the escalation system
- Players can leave and return to a world that continued without them
- Multiple players can inhabit the same world simultaneously
- The AI DM feels curious and investigative, not omniscient
- Every outcome is traceable to a deterministic causal chain

**Why this matters for coding decisions:** Features that work in isolation but
break replayability, traceability, or multi-player consistency are wrong even
if they work in demos.

---

## B. Authority Boundaries (Non-Negotiable)

These are the hardest constraints. Any code that violates them is a bug,
regardless of whether it produces correct output in testing.

### B1. Mutation authority
Only adjudication-like systems mutate canonical WorldState.
Only EscalationEngine propagates event depth.
Only ContextBuilder determines final visibility for a build cycle.
Only EventLog defines causal history.
AI systems never become authoritative simulation actors.

### B2. Single source of identity
HTTP cookie session_id is the sole identity authority.
No query parameter fallback. No request body injection.
`world_controller.session_players[session_id]` is the sole runtime binding.
UI never constructs identity state.

### B3. EventLog integrity
Events are immutable after emission.
No system may rewrite prior events.
No system may emit events that bypass EventLog.
Depth > 0 means the event originated from escalation. Nothing else increases depth.

### B4. ContextBuilder is a consumer
ContextBuilder does not re-resolve entities.
ContextBuilder does not evaluate escalation rules.
ContextBuilder does not mutate world state.
Visibility is computed exactly once per build cycle. No retroactive changes.
Escalation effects are applied as pre-computed inputs, before visibility derivation.

### B5. AI layer boundary
AI receives only what ContextBuilder provides or what it explicitly queries.
AI narrates, summarizes, and interprets. It does not invent canonical facts.
Structured adjudication outputs pass through AI layer unchanged (lossless).
AI tool calls are read-only queries. Mutations require adjudication.

### B6. EscalationEngine boundary
May: emit derived events, inject contextual overlays, flag entities/events, influence perception.
Must not: mutate WorldState directly, modify EntityResolver indices, rewrite canonical entity data,
override computed visibility results, alter salience inclusion results post-derivation.

---

## C. The AI DM Vision

The model is not the game engine. It is the voice of a DM who consults
authoritative sources rather than inventing from memory.

### C1. Curious investigator, not omniscient narrator
The model requests information when it needs it, not from a pre-assembled dump.
Tool calls into the world engine: look(), get_lighting(), get_exits(),
inspect(target), query_recent_events(), query_character_knowledge(npc_id).
Each answer comes from the authoritative simulation. The model reasons over
those facts, decides what else it needs, then narrates.

### C2. EventLog as memory
The model does not receive conversation history as its primary memory.
It queries: what happened recently? what does this NPC know? what changed here?
EventLog is the authoritative history. The model reads it; it does not replace it.

### C3. Structured intent output
The model produces typed intent, not free text that requires parsing.
`{"intent": "search", "target": "oak_desk"}` enters adjudication as a typed request.
If the action is invalid, the engine says so. The model narrates the failure.
World stays authoritative. Model never invents outcomes.

### C4. NPCs as state, LLM as renderer
NPC goals, relationships, knowledge, schedule, mood, faction are deterministic.
LLM is only invoked when the NPC speaks.
Prompt: current NPC state + relevant EventLog facts + player utterance → one response.
The LLM renders the NPC's current state into dialogue. It does not become the NPC.

### C5. Context retrieval on demand
ContextBuilder can return full UnifiedContext (for UI) or specific slices (for AI tool calls).
The model asks for what it needs. It does not receive everything every turn.
Token cost decreases. Focus increases. Hallucination surface shrinks.

---

## D. World Architecture Aspirations

### D1. Two-scale world
World hex grid (large scale travel, terrain, faction territory, POIs).
Sub-hex grid (61 cells per hex, axial coordinates, lazy generation, exploration).
Dungeon grid (tile-based, room+corridor generation, full simulation).
All three scales share the same entity identity and event systems.

### D2. Persistent simulation
The world continues evolving when no player is connected.
NPC schedules advance. Faction influence shifts. Events escalate.
Session reconnect returns the player to the world as it now is, not as they left it.

### D3. Knowledge-gated rendering
The player sees only what their character could legitimately perceive.
Lighting, line-of-sight, stealth, and NPC awareness all constrain what is shown.
Hidden doors, secret passages, trap locations: rendered only after discovery.
AI receives the same filtered view, not the full simulation truth.

### D4. State-driven rendering (not sprite tables)
Visual state is projected from simulation state, not looked up from tables.
Door: kind + is_open + is_locked + is_broken + is_trapped + is_hidden → render.
Tile: type + passable + overlay_list → render.
No combinatorial sprite explosion. No hardcoded appearance-per-state mappings.

### D5. Overlay vs replacement discipline
Overlay: cosmetic damage, interaction residue, known state markers. Does not change topology.
Replacement: passability change, line-of-sight change, adjacency change. Changes topology.
Breach, destruction, secret passage reveal → replacement tiles, not overlays.
Cracks, scorch marks, blood → overlays.

---

## E. Audio Vision

Reactive Audio System (RAS): state-driven, layered, stochastic.
World state + narrative output → AudioContext → scored layer selection → variation engine → playback.
Never hardcode environment → sound mappings. Always go through scoring.
Layer limits prevent chaos: base ≤ 2, character ≤ 2, activity ≤ 2, accent ≤ 3.
Variation history prevents repetition. Silence pockets are intentional, not bugs.
Combat audio overlays base environment; it does not replace it.

---

## F. Reactive World Aspirations

### F1. Escalation as consequence engine
Player actions emit events. Rules evaluate. Consequences propagate.
"Guard attacked" → "witness present?" → "REPORT_CRIME" → "wanted status" → "rumors spread"
Nothing is hardcoded. Reactions emerge from rules + world state.

### F2. Faction and reputation
Faction standing changes from events, not from scripted triggers.
NPC behavior is influenced by faction standing without requiring per-NPC scripting.

### F3. Emergent narrative
Story momentum comes from event chains, not from authored scripts.
The DM narrates what the simulation determined, not what was pre-written.
Surprising outcomes are valid outcomes if the causal chain is traceable.

---

## G. What This Means for Coding Decisions

When adding any feature, ask:
1. Which layer does this belong to? Does it respect the authority boundaries in B?
2. Does it preserve determinism? Can identical inputs produce identical outputs?
3. Does it advance the experience goal in A, or just solve a local problem?
4. If the AI is involved, is it narrating/querying or mutating/deciding?
5. Does it scale to persistent multi-player, or does it assume single-session?

A shortcut that works in testing but violates B is not a shortcut — it is debt
that will require architectural surgery later. The constitution exists because
these lessons were learned the hard way in earlier designs.

---

## H. For the Determined Tool

When this project is analyzed, the tool should eventually be able to:
- Flag code that violates constraints in section B (authority boundary violations)
- Identify symbols that appear to mutate state outside approved flows
- Surface calls from AI/presentation layer into simulation layer that bypass adjudication
- Detect duplicate identity resolution paths (see B2)
- Flag event emissions that don't go through EventLog
- Cross-reference ContextBuilder code against B4 constraints

This requires the Determined tool to understand design intent, not just structure.
See Determined TRACKER item 19.
