# dj2 TRACKER

Active game work items. Finished items get deleted; history goes to HISTORY.md if one exists.

---

## Dependency chain (build order)

World (decorated, navigable, events wired)
  → Conversational Character Creation
  → World Exploration
  → Dungeon (destination within world)

---

## Open items

---

### G1. Fill the world event chain — wire existing modules end-to-end

The world/ directory has escalation_engine.py, event_log.py, narrative_system.py,
overlay.py, context_builder.py, travel_system.py and more. The design docs (01-09
in docs/design/) define what each should do. The gap is not missing code — it is
missing connections and incomplete implementations.

**Goal:** Walk the chain from player input → event → escalation → consequence →
narrative → view. Identify every link that is a stub or disconnected. Fix them in
design-doc order (event log → escalation → context builder → entity resolution →
dialog → quest → perception).

**Use Determined** to map the actual call graph and surface stubs once Determined
analysis is ready to direct this work.

**Wiring model to follow — Truth Transformers:** each system declares what events
it consumes and what it produces. Nothing calls systems directly. The scheduler
sees a new event, finds all systems that consume it, runs them, collects their
output events, repeats. Example:
```python
class VisibilitySystem:
    consumes = [LightingChanged, PlayerMoved]
    produces = [VisibilityChanged]
```
Nobody calls VisibilitySystem. The scheduler does, when its inputs arrive.
Use this pattern when wiring the modules in this item.

**Scheduler not Planner:** a deterministic game doesn't need a planner ("what
should I do?"). It needs a scheduler ("what work is now eligible to run?").
The escalation engine IS the scheduler. Keep it that way.

**No-chat architecture:** the runtime loop is not request/response. It is:
`while alive: listen → update world → run tools → queue scheduler → stream answer
→ continue listening → cancel if interrupted → repeat`. Events, not conversation.
("queue scheduler" not "queue planner" — see Scheduler not Planner note above.)

**Verify:** A player moves on the world map, an event fires, the escalation engine
reacts, narrative output appears.

---

### G2. World decoration / overlay system

From: docs/design ideas — dungeon and world decoration and overlays.txt

**Core rule (commit to this):**
- Overlay = visual annotation only. Does not change passability or connectivity.
- Replacement = topology change. Must update passability, adjacency, pathfinding.

**Door state model** — orthogonal flags, not separate types:
```python
class Door:
    kind: str          # wood, stone, portcullis, hidden
    is_open: bool
    is_locked: bool
    is_broken: bool
    is_trapped: bool
    is_hidden: bool
```
Rendering is state projection from these flags, not sprite lookup. Prevents
combinatorial explosion.

**Wall destruction:** WALL → BREACHED_WALL → FLOOR. BREACHED_WALL is a
replacement tile (passable, reads visually as former wall). Only update local
adjacency neighbors, not whole map.

**World hex:** same system at larger scale. overlay = camp/ruins/tracks,
replacement = settlement/dungeon entrance.

**Overlay vocabulary (keep it weak — overlays suggest, don't declare):**
cracks, debris, damage marks, moss, scorch, blood stain, snow, mud.

**Implement in order:**
1. Add BREACHED_WALL tile type + directional breach rendering
2. Convert door system to state-based
3. Add 3 overlays: crack, debris, damage marks
4. Add knowledge-gated rendering (hidden things render as normal until discovered)
   — Truth/Observation split: Truth is `Door.Hidden = True`. Observation is what
   the player's character actually perceives given their skills/position/light.
   The renderer draws from the Observation layer, never directly from Truth.
5. World hex overlay rules (camp, ruins, tracks, settlement)

---

### G3. NarrativeService — constrained LLM narration layer

From: Gaia RAG and Narration.txt

**Two distinct modes — do not conflate:**

**Runtime narration (CONSEQUENCE phase):** Single-shot, constrained LLM call.
LLM gets already-resolved game state and describes it — never decides anything.
No critic loop here. Latency matters.

**Offline content generation (batch):** Campaign hooks, NPC creation, world-building,
encounter design. This is where the Critic quality loop (Storyteller → Rules Lawyer
→ Critic → re-run until quality threshold) belongs. This may route through
Determined rather than being rebuilt in dj2 — Determined's evaluate/reason_about/
synthesize pipeline IS a generalized Critic. Same architecture: deterministic
foundations (game rules / world state) as oracle, AI as reasoning layer on top.
Decision deferred: implement offline critic in dj2 first if needed, migrate to
Determined when that pipeline matures enough to accept game content as input.

Sits at the CONSEQUENCE phase. LLM gets already-resolved game state and
describes it — never decides anything.

**Pattern:**
- `describe_room(room, party)` — max 3 sentences, only describe provided elements
- `describe_combat_result(event)` — max 2 sentences, outcome only
- `describe_event(event)` — max 2 sentences, no new facts

**Three-layer model the narrator must respect:**
- Truth: raw world state (`Torch.Intensity = 0.28`, `Door.Open = False`)
- Derived: deterministic transformations of truth (`Room is dim`, `Door is closed`)
- Observation: what the player's character perceives given position/skills/light

The narrator receives **observations only** — never truth, never raw state.
A FactAggregator sits between the simulation and the narrator: it collects
post-event derived facts, runs deterministic perception transforms (darkvision
range check, current light level, character Perception skill result, stealth
contest outcome), and packages the resulting observation bundle. These transforms
are pure functions over character stats and world state — no LLM involved.
The narrator cannot invent facts because it never sees the underlying truth layer.

Hallucination guard: extract allowed terms from source dict, reject output
containing unknown 4+ letter words (with common filler whitelist). Fallback:
"You see what lies before you, unchanged."

RAG context: query by room type + tags for flavor from knowledge base.
Cache RAG results per room. Cache descriptions after first generation.

**LLM constraints in prompt:**
- No new entities, no decisions, no system control, tight verbosity
- Temperature ~0.3 to keep deterministic-ish

**Plug-in points:**
- Room entry → describe_room
- After combat resolution → describe_combat_result  
- Generic world event → describe_event

---

### G4. Conversational character creation

Text-first. Voice is a rendering layer added later — do not add voice complexity
to this item.

**Flow (3-5 turns max, hardcoded for MVP):**
1. "Who were you before all this?"
2. "What drives you now?"
3. "What do you fear?"
Plus 1-2 follow-up clarifications as needed.

**Architecture (fits 7-phase runtime):**
- INPUT: text (voice later as VIEW PROJECTION rendering)
- INTERPRETATION: STT (later) + LLM interviewer extracts structured data
- AUTHORITY: validate character against rules (class/level constraints)
- STATE MUTATION: SessionSystem creates character record
- CONSEQUENCE: NarrativeService generates "So you are..." confirmation
- PERSISTENCE: character JSON + vector embedding of full backstory
- VIEW PROJECTION: text (TTS later)

**LLM interviewer persona:** warm, asks follow-ups, suggests but never imposes,
builds character sketch iteratively. Does NOT interrogate or use form-like language.

**Character record stores:**
- Structured: class, background, stats (from dnd-character or existing schema)
- Narrative: full backstory text
- Vector embedding: semantic search for DM to surface relevant hooks later
- Tags: trauma type, motivations, fears, relationships — for encounter/quest hooks
- Dramatic hooks: filed for DM to use in world/dungeon events

**Character → world integration:**
- "Former city guard" → tag relevant city locations, guard NPCs know of player
- "Searching for sister's killer" → DM encounter hook for clue placement
- "Afraid of fire" → dungeon generator: occasional fire traps (dramatic irony)

---

### G5. Semantic Genome — visual and audio recipe library

From: DnD addition.md (long design conversation)

This is the long-game rendering architecture. Do not implement the full renderer
yet — design the schema and build the first 20-30 recipes. Implementation follows
after G1-G4 are stable.

**Core idea:** AI is the Asset Librarian, not the artist. LLM authors YAML recipes.
Renderer composes them. No PNGs for game-truth objects.

**Two renderer split:**
- Semantic renderer: game truth (where is the chair, is the door open, which wall
  collapsed). Deterministic, state-driven. Answers "what is that?"
- Mood renderer: atmosphere (image generation for village establishing shots,
  dungeon area mood). Generated once or occasionally. Never needs real-time updates.

**Primitive domains:**
- Geometry: line, arc, bezier, circle, ellipse, polygon
- Material: wood, stone, iron, leather, glass, bone, fabric, crystal, water, fire
- Decoration: cracks, moss, rust, dust, roots, snow, blood, ash, mud, scorch
- Motion: swing, rotate, shake, flutter, glow, pulse, smoke, ripple, spark, drip
- Lighting: torch, sunlight, moonlight, magic, fire, reflection, shadow, fog
- Sound: wind, water, fire, footsteps, metal, wood, voices, birds, echo, magic

**Recipe format (YAML):**
```yaml
# example: chair.yaml
inherits: Furniture
components: [seat, legs, back]
materials: [oak, pine, iron]
states: [broken, overturned, burned]
decorations: [cushion, carving, moss]
sounds: [scrape, crack]
interactions: [sit, push, burn]
shadow: medium
```

**Sound is the same system:**
- Room type defines base sound layer (cave = wind + drip + echo)
- Entering new biome = add/remove/adjust layers (crypt: remove bats, add whispers,
  add chains, increase echo)
- Exactly parallel to visual composition

**AI primitive discipline rule:**
When adding a new object, AI must answer:
1. Can this be expressed from existing primitives?
2. If not, what is the smallest new primitive needed?
3. Will that primitive enable many future objects, or is it too specific?

Gargoyle example: don't add gargoyle primitive. Discover wing, claw,
stone_carving, weathering — these are reusable for griffin, statue, dragon,
decorative architecture.

**First session deliverable:** schema spec + 20 seed recipes for dungeon objects
(door, chest, torch, barrel, table, chair, wall section, floor section, pillar,
debris pile, cracks overlay, moss overlay, scorch overlay, portcullis, staircase,
statue, bookshelf, weapon rack, bed, firepit).

---

### G6. Voice pipeline — deferred, add after G4 is working

From: Game NPC Voice AI - Kimi.txt

**Local stack:**
- STT: faster-whisper (medium) — 200-400ms
- TTS: Kokoro (small, CPU-only) preferred — don't assume GPU on the far end.
  In multiplayer, players run on hardware we don't control. Kokoro stays off
  the GPU entirely, which avoids contention with the LLM on the host machine
  and works on player machines of unknown spec.
- Orchestration: custom asyncio, no Pipecat needed

**Semantic Recovery layer** (sits between STT output and LLM/verb registry):
Raw transcript is noisy. Don't feed it directly to the DM. Instead, a recovery
step extracts structured intent before the LLM sees anything:
```
"I sort of sneak over there quietly maybe..."
  → Intent(action=MOVE, mode=stealth, target=door, confidence=0.91)
```
The LLM maps recovered intent to verb registry tokens (G10), not raw speech.
This means the DM never sees noise — only structured facts with confidence scores.
Uncertain parts are flagged for clarification, not guessed.

**Background tasks / perceived latency:** emit an acknowledgment immediately
("Looking around..."), then run workers in parallel. Player can interrupt
mid-task and the partial result is discarded cleanly via InterruptManager.
This is what makes a voice agent feel responsive even when work takes 2-3s.

**Priority dispatcher:** sits in front of all workers. Categorizes incoming
requests by tier, manages queues, handles graceful degradation when workers are
swamped. Rules: drop stale Social-tier items (>2s old, player moved on), hold
Tactical items (still relevant), never drop Instinct or Dramatic. The dispatcher
is lightweight (comparison + queue ops) — copapy/Mojo not needed here. Workers
(Whisper, LLM, TTS) are where load lives; those are IO-bound or parallelizable.

Architecture:
  All inputs → Dispatcher (fast, categorize + route)
                 ↓ priority queues by tier + staleness
    [Whisper workers] [LLM workers] [TTS workers]
                 ↓
             Outputs

The Dramatic Director response tiers ARE the dispatch priority rules — same
design, not two things to build separately.

**Response tier model (Dramatic Director):**
| Tier | Trigger | Latency target | Technique |
|------|---------|---------------|-----------|
| Instinct | Combat bark, pain, surprise | <300ms | Pre-generated audio pool |
| Social | Greeting, shop talk | <800ms | Cached phrases + light LLM |
| Tactical | Combat strategy | <1s | Streaming LLM, interruptible |
| Dramatic | Plot revelation | 2-5s | Full LLM, player sees "thinking" |
| Refactor | Campaign rewrite | 5-30s | Pause + dramatize the wait |

**Key insight:** interruptibility deferred until core conversation flow is solid
and we know where the cancel points are. Don't model it speculatively.

**NPC mind model (for when this is built):**
- Immediate: emotional_state, current_goal, attention_target
- Short-term: conversation_history, recent_events
- Long-term: relationship_map, memory_vectors, agenda
- Dramatic: plot_hooks, dramatic_function (comic relief, tragic hero, mentor...)

**Social turn adjudication:** NPCs bid for speaking rights by urgency + social rank
+ player attention + agenda importance. Adjudicated as a priority queue, not
fought in the audio channel.

**Crosstalk recovery / DM reset:** When multiple players talk over each other the
audio layer will produce garbage. The DM needs a deterministic interrupt path:
detect overlapping audio (energy + VAD on multiple streams simultaneously), discard
partial transcripts, and emit a DM_RESET event that interrupts all pending speech
and plays a pre-generated reset phrase ("Hold on — who has advantage here?" /
"Everyone roll a d20, highest goes first."). This is not an AI decision — it is a
rule: overlap detected → reset phrase chosen from a small authored pool → requeue
players by some fair rule (initiative order, d20 roll, oldest-waiting-first).
The reset phrase pool lives in a flat file so Bart can author them without code
changes. The interrupt itself maps to the existing InterruptManager design above.

**FastRTC** (fastrtc.org): for multi-user audio streaming when that becomes relevant.

---

### G8. MCTS for game decision-making — future, design only

Mojo/Mimic watch item from session 28. MCTS is in Determined (RM9) for code
reasoning. The parallel in the game is anywhere branching futures need evaluation.

**Strong candidates:**
- Combat tactics: NPC choosing attack/retreat/ability/call-for-help. Native MCTS
  problem — branch, simulate, evaluate, converge.
- Encounter balancing: simulate N outcomes before placing encounter, check TPK risk.
- NPC agenda pursuit: NPC with goals + social graph, acting across interactions to
  advance agenda without revealing it. MCTS with social evaluation function.
- Campaign branching: DM selecting which plot thread to advance given player state.

**The hard design problem:** evaluation function. MCTS is only as good as how leaf
nodes are scored. In Determined = code quality signals. In the game = party survival
probability + narrative coherence + player agency preserved. Scoring "feels like
good D&D" is the unsolved part.

**High-performance routing (copapy/Mojo watch):** The real justification is not
dice math but concurrent load — multiple Whisper STT streams in, multiple LLM
responses generating simultaneously (DM + NPCs), multiple TTS streams out, game
state + escalation rules all firing at once. Python's GIL becomes the bottleneck
at that scale. Decision point when voice is running with multiple players:
- If bottleneck is CPU-bound (parallel Whisper transcription) → copapy/multiprocessing
- If bottleneck is IO-bound (waiting on LLM responses) → asyncio already handles this
Don't decide now. Measure first.

**Status:** keep watching. Don't implement until evaluation function is designed.
Relationship to Determined's RM9 (Q4 MCTS): same pattern, different domain.

---

### G9. Escalation engine: Exit Ramps + Risk Assessment

From: Plot Engineering Blueprint (Edariad)

Two concepts that extend the existing escalation_engine.py design (ECA rules):

**Exit Ramps** — currently missing from the escalation engine design.
The engine fires consequences but has no de-escalation paths. Exit Ramps are
pre-authored ways for a situation to recover or redirect at each time horizon
before it reaches maximum escalation. They're not escape hatches — they're
story opportunities. Each ECA rule should optionally carry exit ramp alternatives
alongside its escalation consequences.

Time horizon structure (add to escalation chain model):
- Immediate (minutes/turns): direct participants, standard procedures
- Short-term (hours): information spreads, new parties involved, factions react  
- Long-term (days+): power groups adjust, precedents set, relationships change permanently

Exit ramp design rule: present clear immediate consequences while hinting at
longer-term implications so players can make informed decisions. Escalation is
an opportunity, not a problem — interrupted peace talks can expose needed corruption.

**Risk Assessment Matrix** — party behavior profile that weights ECA rule priority.
Rate party tendencies 1-5: Combat Style, Rules Lawyer, Party Cohesion, Problem
Solving, Story Investment. Rate plot element criticality 1-5: NPC Survival,
Locations, Timeline, Information, Resources. Multiply to score risk intersections.
Score 16-25 = high risk, needs contingency ECA rules pre-authored.

This becomes the AI DM's party profile — it informs which escalation triggers
to weight more heavily when deciding whether to fire or hold a rule. A combat-
heavy party (Combat Style=5) near a critical NPC (NPC Survival=5) = score 25,
AI DM should have exit ramps ready before the encounter even starts.

**Implementation note:** Exit Ramps belong in escalation_engine.py alongside
existing ECA rules. Risk Assessment Matrix is a party profile in the campaign/
session state that the AI DM reads when evaluating which rules to prioritize.
Neither requires new subsystems — both extend what's already designed.

**Reference:** docs/design/02 escalation engine v1.3.md, world/escalation_engine.py

---

### G10. Verb registry — actions as first-class entities

From: architecture discussion 2026-07-07 (Ragel/beagle-ext ideas session)

Currently player actions are handled as ad hoc strings or implicit code paths.
The idea: make every action in the game a named, registered verb object with
declared structure. Not a command parser — a canonical vocabulary the whole
system shares.

**What a verb object carries:**
- Name and aliases (attack, strike, hit → ATTACK)
- Preconditions (has_weapon, target_in_range, not_stunned)
- Semantic tokens it emits to the event log (ATTACK_INITIATED, DAMAGE_DEALT, etc.)
- Effects on world state (target.hp -= damage)
- Context it requires (who, what, how, where)

**Why this pays off:**
- LLM interpretation layer has a bounded vocabulary to map to (not open-ended)
- Event log references canonical tokens, not freeform strings
- Semantic sensors (G11) subscribe to verb tokens, not text patterns
- New actions are added in one place; all subscribers pick them up automatically
- Determined can analyze the verb registry as a first-class surface

**What this is NOT:** a command parser. Players still speak freely.
The LLM maps "I quietly ease the door open with my shield up" → OPEN(door, stealth=True).
The verb registry defines what OPEN means and what it emits — not how to recognize it.

**Build order:** verb registry schema → seed with 20-30 core verbs → wire into
LLM interpretation output → wire event log to consume verb tokens.

**Reference:** G11 (semantic sensors) depends on this; build G10 first.

---

### G11. Semantic sensor layer — DFA pattern detection over event stream

From: architecture discussion 2026-07-07 (Ragel/beagle-ext ideas session)

The escalation engine (G9) currently fires rules based on individual events.
This item adds a layer that recognizes *patterns across multiple events* —
higher-level semantic facts that emerge from sequences, not single triggers.

**Core idea:** each gameplay concept (Ambush, Suspicion, TacticalWithdrawal,
TrapNeutralized, CoordinatedAssault) is a declarative pattern spec that gets
compiled into an executable detector. The detector watches the event stream and
emits a higher-level semantic event when the pattern completes.

**Pattern spec format (declarative, not code):**
```yaml
concept: Ambush
pattern:
  - PLAYER_ENTERS_AREA
  - ENEMY_HIDDEN
  - ENEMY_ATTACKS
  - PLAYER_UNAWARE
emit: AMBUSH_OCCURRED
```

**Why not just more ECA rules in escalation_engine.py:**
ECA rules handle one event → one consequence. Semantic sensors handle
N events across time → one recognized fact. They're a recognition layer,
not a reaction layer. The escalation engine subscribes to sensor output
the same way it subscribes to raw events.

**Implementation path:**
1. Define a SemanticSensor class: pattern (ordered/unordered event list with
   wildcards), emit token, optional time window
2. SensorRegistry: load from YAML specs, subscribe to event log
3. EventLog feeds each new event to all registered sensors
4. Sensor fires emit token back into event log when pattern completes
5. Seed with 10-15 sensors covering combat, stealth, social, trap scenarios

**Tooling note:** Ragel (C DFA compiler) is overkill for this use case.
A Python dict-of-dicts state machine or the `transitions` library is the
right implementation. The *conceptual model* from Ragel (declarative spec →
compiled recognizer) is what we're borrowing, not the C codegen.

**Depends on:** G10 (verb registry provides the canonical token vocabulary).
**Feeds into:** G9 (escalation engine subscribes to sensor output),
G3 (narrative layer gets richer semantic context).

---

### G12. AttentionManager — working memory over facts, not conversation history

Instead of growing a conversation transcript and stuffing it into the model
context window, keep a structured working memory:
- Current audio buffer
- Current transcript (short-lived, discarded after semantic recovery)
- Current semantic graph: the structured intent output from Semantic Recovery
  (G6) currently being processed — e.g. `Intent(action=MOVE, mode=stealth,
  target=door, confidence=0.91)` plus any unresolved ambiguities flagged for
  clarification
- Current world state snapshot (relevant slice, not whole world)
- Long-term memories (vector store, retrieved by relevance)
- Pending tasks (background workers in flight)
- Event log (authoritative, append-only)

Older events decay out of active attention by recency — recent events stay hot,
older ones drop to long-term memory unless re-referenced (a new event names the
same entity, a player explicitly asks about it, or a completing background task
links back to it). Long-term memories live in the vector store and are retrieved
by semantic similarity to the current world state slice + active intent. This
prevents ever-growing context without losing important state.

**Why this matters for DJ2 specifically:** the game is long-running. A
multi-hour session will produce hundreds of events. Naive conversation history
bloats context fast. The event log already IS the authoritative record — the
AttentionManager just decides which slice of it is currently in working memory.

**Depends on:** G10 (verb tokens give it a clean vocabulary), G11 (semantic
sensors give it higher-level events to track). Not urgent — design when G3
narration is working and context window pressure becomes real.

---

### G7. Multi-user session identity — deferred

From: enhancements to add to world-dungeon project.txt (ZeroTier section)

ZeroTier already in code and tested. Identity manager pattern: separate Connection
(ZeroTier IP) from Player identity from Active Character.

Commands: `/claim CharacterName`, `/switch CharacterName`

Deferred until single-player flow is solid.

---
