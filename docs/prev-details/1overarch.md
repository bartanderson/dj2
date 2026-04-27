Good—this is exactly the right move. What you’re asking for is cross-system compatibility at the architectural level, not just “can these coexist.”

I’m going to do three things for each document:

Extract its implicit model
Map it into the same formal system as the Audio spec
Define integration contracts + friction points (where it will break or need adaptation)

The goal:

Any future AI can pick this up and build one coherent system, not three parallel ones.

0. Unifying Principle (applies to ALL systems)

Everything must map through:

WorldState → Normalized Context → System-Specific Projection

You now have three major systems:

System	Purpose
Narrative (GAIA RAG)	Text rendering
Subhex	Spatial simulation
Visual Overlay	Visual truth vs representation
Audio (previous spec)	Sound rendering

They must all consume the same normalized state.

1. Shared Canonical State (NEW — required for compatibility)

This is the missing glue across all documents.

class UnifiedContext:
    # Spatial
    domain: str            # dungeon / settlement / wilderness
    location: str          # tavern / crypt / road / etc.
    position: tuple        # (col,row,q,r)

    # Environmental
    terrain: str
    time_of_day: str
    indoors: bool

    # Activity
    activity: str          # idle / travel / combat / social

    # Narrative
    mood: str              # calm / tense / eerie / cozy
    tension: float         # 0–1
    event: str | None

    # Population
    presence: str          # alone / sparse / crowded

    # State modifiers
    danger: float
    fatigue: float

    # Knowledge layer
    knowledge: dict        # what player knows vs truth

    # Structural state (from overlay system)
    topology_changes: list
2. GAIA / Narrative System Integration
2.1 What it already does well

From your doc:

strict prompt constraints
validation layer
no state mutation

This is perfect for your architecture.

2.2 Required alignment with UnifiedContext
Replace:
room: Dict
event: Dict
With:
context: UnifiedContext
2.3 New Narrative Contract
class NarrativeInput:
    context: UnifiedContext
    focus: str   # "room" | "event" | "combat"
2.4 Prompt Upgrade (IMPORTANT)

Current prompts are too generic. They ignore system richness.

Replace with:
You are a narrative renderer.

RULES:
- Max 3 sentences
- Describe ONLY elements present in CONTEXT
- Reflect mood, environment, and activity
- Do NOT introduce new objects or events

CONTEXT:
{context}

FOCUS:
{focus}

OUTPUT:
Plain text only.
2.5 Integration Insight

Narrative should NOT:

describe hidden overlay states
override subhex truth
invent topology

It must respect:

knowledge layer from UnifiedContext
2.6 Difficulty / Risk
Problem:

Your validator is too strict:

if word not in allowed_terms → reject

This will:

kill descriptive richness
conflict with mood-based rendering
Fix:

Allow:

"soft vocabulary expansion"

Add:

ALLOWED_DESCRIPTORS = {
    "dark", "faint", "distant", "rough", "quiet", "low", "warm"
}
3. Subhex System Integration

This is your spatial authority layer.

3.1 What it provides
fine-grained position (q,r)
terrain truth
discovery state
POI anchoring
3.2 Required mapping to UnifiedContext
ctx.domain = "wilderness" | "dungeon" | "settlement"
ctx.location = subhex_cell.poi_id or terrain
ctx.terrain = subhex_cell.terrain
ctx.presence = infer_population(subhex_cell)
3.3 Critical addition (missing in your doc)

You need:

SubhexCell.sound_profile: Optional[str]
SubhexCell.mood_modifier: Optional[str]

Why:

Audio system needs it
Narrative needs it
Otherwise everything feels samey
3.4 Movement → System Updates

When player moves:

on_subhex_move():
    update UnifiedContext
    trigger:
        Audio update
        Narrative event (optional)
        Visual redraw
3.5 Fog of War → Knowledge Layer

You already track:

discovered / explored

Map to:

ctx.knowledge["visible_cells"]
ctx.knowledge["hidden_cells"]

This feeds:

Narrative restrictions
Visual overlay rules
Audio dampening (important)
3.6 Difficulty / Risk
Problem:

Subhex is deterministic, others are stochastic

→ mismatch risk

Solution:

Subhex = ground truth
All other systems = projection layers

4. Visual Overlay System Integration

This is your truth vs representation system.

4.1 What it already does correctly
separates overlay vs replacement
uses state-based door model
supports topology changes

This is excellent.

4.2 Required mapping to UnifiedContext
ctx.topology_changes = [
    "breached_wall",
    "door_open",
    "blocked_path"
]
4.3 Knowledge gating (CRITICAL)

From your doc:

hidden → revealed transitions

This must propagate:

ctx.knowledge["visible_topology"]
4.4 Audio integration (new insight)

This system directly affects sound:

State	Audio Impact
closed door	muffled sound
open door	full sound
breached wall	echo increase
hidden passage	no sound until discovered

So:

AudioContext.modifiers += topology_changes
4.5 Narrative integration

Narrative must obey:

if not knowledge.detected_secret:
    do NOT describe it
4.6 Difficulty / Risk
Problem:

Overlay system is directional (breach direction)

Other systems are not

Result:

Mismatch between:

visual hole
movement
audio directionality
Fix (required later):

Add:

directional_context: {
    "openings": ["north", "east"]
}
5. Audio System Alignment (tying it all together)

Now we connect everything.

5.1 AudioContext now derives from UnifiedContext
def build_audio_context(ctx: UnifiedContext):
    return {
        "domain": ctx.domain,
        "location": ctx.location,
        "mood": ctx.mood,
        "intensity": ctx.tension,
        "activity": ctx.activity,
        "presence": ctx.presence,
        "danger": ctx.danger,
        "modifiers": ctx.topology_changes
    }
5.2 Subhex → Audio
terrain drives base layers
POI drives character layers
discovery affects variation
5.3 Overlay → Audio
door states → filtering
breaches → echo
barricades → dampening
5.4 Narrative → Audio
tone → mood
pacing → intensity
events → stingers
6. Cross-System Interaction Matrix

This is what the next AI needs most.

Source	Affects	How
Subhex	Audio	terrain → layers
Subhex	Narrative	environment description
Subhex	Visual	rendering
Overlay	Visual	direct
Overlay	Audio	filtering / echo
Overlay	Narrative	gated visibility
Narrative	Audio	mood + events
Audio	(none)	output only
7. Global Update Loop (final unified model)
def game_tick():

    world_state = get_world_state()
    narrative_state = get_narrative_state()

    unified = build_unified_context(world_state, narrative_state)

    # Systems consume same context
    audio.update(unified)
    visual.render(unified)
    text = narrative.render(unified)

    ui.display(text)
8. Biggest Integration Risks (be aware)
8.1 Over-constraining narrative
current validator too strict
will conflict with mood-driven systems
8.2 State drift
subhex vs overlay vs narrative inconsistencies

Fix:
→ unified context is single source of truth

8.3 Overlapping responsibilities

Example:

subhex says “forest”
narrative says “stone chamber”

Fix:
→ narrative must NEVER override spatial truth

8.4 Audio desync

If updates are:

too frequent → noise
too rare → lag

Target:

2–5 updates per second
9. What is still hard (honest gaps)

These are non-trivial:

1. Directional audio (not solved yet)

Needed for:

breaches
doors
movement cues
2. Multi-cell POIs

Subhex doc flags this

→ affects:

audio scaling
narrative scope
rendering
3. Long-term variation memory

Across sessions:

tavern should feel different next visit

Requires:

persistent audio seeds
4. AI coherence over time

Narrative + audio must not drift stylistically

Final Instruction for Next AI

Treat UnifiedContext as the ONLY source of truth.
All systems must derive behavior from it and must NOT directly depend on each other.

If you want next step

Now that everything is aligned, the most valuable next move is:

I build you:
UnifiedContextBuilder
integrated with:
subhex movement
overlay updates
narrative inputs
audio output

That’s the actual “spine” of your system.