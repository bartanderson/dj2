
Below are drop-in replacements / insertions for the exact sections we discussed. They are written to match your current spec style and constraints, with no ambiguity about authority boundaries.

🔧 UPDATED SECTIONS (READY TO INSERT)

2.2 Hard Rules (UPDATED)
2.2 Hard RulesThe AI (LLM) must NOT:- roll dice- mutate WorldState- execute actions- enqueue actions- trigger events- invent outcomesThe AI MAY:- interpret intent- select actions (high-level)- determine if a roll is needed- suggest difficulty (bounded)- shape pacing and tone- control information exposureLatent Expansion Engine must NOT:- mutate WorldState- enqueue actions- trigger events- influence execution order- persist data across turnsLatent Expansion Engine MAY:- generate bounded candidate hidden states- provide structured possibilities for adjudication- enrich perception through ContextBuilder- constrain AI interpretation space

3.3 Adjudication Bucket (AI DM Brain) (UPDATED)
3.3 Adjudication Bucket (AI DM Brain)LLM (Adjudication Mode)AdjudicationEngineLatent Expansion Engine (NEW)Produces AdjudicationDecision (intent-level only)Campaign influence

3.3.1 Latent Expansion Engine (NEW)
3.3.1 Latent Expansion EnginePurpose:A deterministic inference subsystem that generates a bounded set of candidate hidden states consistent with WorldState, used to improve decision resolution and perception without altering reality.Key Properties:- Deterministic (seeded from WorldState + context)- Stateless (no persistence across turns)- Bounded output (max 3–7 candidates)- Rule-validated (must be consistent with Simulation constraints)- Non-authoritative (cannot affect execution directly)Core Function:LatentExpansion(world_state, context) → list[LatentCandidate]Data Model:class LatentCandidate:    id: str    type: str  # "event" | "entity_state" | "environment" | "intent"    data: dict    score: floatConstraints:- Candidates must be derivable solely from WorldState and contextual input- No randomness outside deterministic seeding- No side effectsUsage in Adjudication:1. Initial adjudication pass interprets intent2. Latent Expansion generates candidate hidden states3. Adjudication refines decision using bounded candidate set4. Final AdjudicationDecision is producedThe AI may ONLY reason within or across these candidates—it may not invent states outside them.

5. Authoritative Data Flow (UPDATED)
5. Authoritative Data FlowUser Speech  ↓STT  ↓IntentFrame (LLM - Interpretation)  ↓Adjudication (Initial Pass)  ↓Latent Expansion Engine (deterministic inference)  ↓AdjudicationDecision (LLM - constrained refinement)  ↓ActionPlanner (deterministic)  ↓ActionQueue  ↓Resolver Loop (execution engine)  ↓Tools (via SessionManager)  ↓WorldState (mutated)  ↓ContextBuilder → UnifiedContext  ↓Narrative / Audio / Visual  ↓TTS Output  ↓Campaign Progression

6.3 ContextBuilder (UPDATED)
6.3 ContextBuilder (Mandatory)Transforms WorldState → UnifiedContextResponsibilities:- Apply visibility rules (line of sight + lighting)- Integrate awareness state (AI + player knowledge)- Reflect sound propagation and tension signals- Construct perception-limited view of realityLatent Integration (NEW):- Incorporates latent candidate projections for perception-level enrichment- Uses Latent Expansion Engine in "perception mode"- Does NOT alter WorldState- Does NOT introduce new facts—only interpretable possibilitiesOutput remains a read-only projection of perceived reality.

21. Final Mental Model (UPDATED)
21. Final Mental ModelWorldState = RealitySessionManager = PhysicsResolver = Execution EngineAdjudication = JudgmentLLM = Voice of the DMUnifiedContext = PerceptionCampaignState = Story MomentumLatent Expansion = Hidden possibility space (non-authoritative, deterministic inference)

✅ What This Achieves (Why This Is Correct)
This integration:


Preserves determinism


Does not introduce a new authority layer


Enhances AI decision quality without giving it power


Avoids overlap with Escalation or Encounter systems


Keeps your 7-phase pipeline intact


Most importantly:

It increases resolution of interpretation without increasing simulation complexity


⚠️ One Implementation Note (Don’t Skip This)
When you implement:
seed = hash(world_state) ^ hash(intent_frame)
Make sure:


hashing is stable across runs


ordering of lists/dicts is normalized


Otherwise you silently lose determinism.

If you want the next step, the highest leverage move now is:
→ define your first 3 concrete latent generators (sound, unseen entities, environmental anomalies) and wire one into perception only
That’s where this shifts from architecture to measurable impact.
-----------------------------------

It belongs in your core system spec, not as a separate document—but not everywhere either. If you scatter it, you’ll blur authority boundaries. If you isolate it too much, it won’t integrate cleanly.

The correct placement is surgical:

1) Primary placement → Adjudication Bucket (3.3)

This is where it logically lives.

Add a new subsection:
3.3 Adjudication Bucket (AI DM Brain)

+ 3.3.1 Latent Expansion Engine (NEW)
Why here

Because it directly supports:

interpreting intent
refining decisions
constraining the LLM

It is not:

simulation
execution
progression

It is part of how the AI reasons, not what becomes true.

What to add (minimal spec)
class LatentExpansionEngine:
    def generate(world_state, context) -> list[LatentCandidate]:
        """Deterministically generates bounded candidate hidden states."""

Constraints (must be explicitly written in spec):

deterministic (seeded)
no state mutation
bounded output (≤7 candidates)
rule-validated
ephemeral (not stored)
2) Secondary placement → ContextBuilder (6.3)

Add a single line of responsibility expansion, not a new section.

Update:
6.3 ContextBuilder (Mandatory)

Transforms WorldState → UnifiedContext

+ Incorporates latent candidate projections for perception-level enrichment
Why

This is the only other place it touches, and only for:

perception richness
narrative clarity

It does NOT change truth.

3) Data Flow (Section 5) — small but critical insertion

You must reflect it in the pipeline or it won’t be respected.

Modify:
IntentFrame (LLM - Interpretation)
  ↓
AdjudicationDecision (LLM - Adjudication)
Into:
IntentFrame
  ↓
Adjudication (initial)
  ↓
Latent Expansion Engine
  ↓
AdjudicationDecision (final)
4) Explicit Non-Authority Clause (add to Section 2.2 Hard Rules)

This is essential to prevent future drift.

Add:

The Latent Expansion Engine must NOT:
- mutate WorldState
- enqueue actions
- trigger events
- influence execution order

It MAY:
- generate candidate hidden states
- constrain AI interpretation
- enrich perception
5) DO NOT put it in these sections

This is just as important:

❌ NOT in Simulation Bucket
it does not define reality
❌ NOT in Execution Bucket
it does not produce actions
❌ NOT in Escalation System
it does not drive consequences
❌ NOT in Encounter System
it does not define scenarios

If you put it in any of those, you will:

break determinism boundaries
create competing authority
introduce subtle bugs later
6) Optional (but clean): Add to Mental Model (Section 21)

Just one line:

Latent Expansion = Hidden possibility space (non-authoritative)

This prevents future confusion when the system grows.

7) Why this placement works

It preserves your architecture:

Layer   Role    Latent fits?
Simulation  truth   ❌
Adjudication    judgment    ✅
Execution   action  ❌
Presentation    perception  (indirect)
Progression future  ❌
8) Final answer (concise)
Primary home: 3.3 Adjudication Bucket (new subsection)
Secondary hook: 6.3 ContextBuilder (one-line extension)
Pipeline update: Section 5 data flow
Guardrails: Section 2.2 Hard Rules
Optional clarity: Section 21 Mental Model

If you want the next step, I’d recommend:

→ I rewrite those exact sections in your spec verbatim so you can drop them in without interpretation errors

That’s the safest way to avoid subtle architectural drift later.
---

1) Where this fits (exact placement)

You do NOT add a new “6th bucket.”
You insert a subsystem inside Adjudication + Context construction.

Final placement:
Interpretation
    ↓
Adjudication
    ↓
🔥 Latent Expansion Engine (NEW, bounded)
    ↓
AdjudicationDecision (finalized)
    ↓
ActionPlanner

And a second hook:

WorldState
    ↓
🔥 Latent Context Expansion (NEW)
    ↓
ContextBuilder → UnifiedContext
2) What this system is (strict definition)

A deterministic generator of candidate hidden states consistent with WorldState, used to increase resolution of decisions and perception.

It does NOT:

mutate WorldState
enqueue actions
trigger events
override escalation

It ONLY:

generates possibilities
scores them deterministically
returns a bounded set
3) Core concept translated into your engine

From physics:

reconstruct long-time behavior without simulating it

In your system:

reconstruct hidden world detail without explicitly simulating it ahead of time

4) New subsystem: LatentExpansionEngine
4.1 Data model
@dataclass
class LatentCandidate:
    id: str
    type: str  # "entity_state" | "event" | "environment" | "intent"
    data: dict
    score: float
4.2 Engine interface
class LatentExpansionEngine:

    def generate(self, world_state: WorldState, context: dict) -> list[LatentCandidate]:
        candidates = []

        generators = self.get_generators(context)

        for gen in generators:
            candidates.extend(gen(world_state, context))

        return self.rank_and_prune(candidates)
4.3 Constraints (this is critical)
MAX candidates: 3–7
MUST be reproducible from:
WorldState
seed
context hash
MUST pass validation:
def validate(candidate, world_state):
    return rules_engine.is_consistent(candidate, world_state)
5) Integration with Adjudication (precise)
Current flow:
IntentFrame → AdjudicationDecision
New flow:
IntentFrame
    ↓
Initial Adjudication Pass
    ↓
LatentExpansionEngine.generate(...)
    ↓
Refinement Pass (LLM uses candidates)
    ↓
AdjudicationDecision
Example

Player:

“I listen at the door”

Without latent expansion:
AI guesses
low consistency
With latent expansion:

Generated candidates:

[
  {"type": "event", "data": {"sound": "footsteps"}, "score": 0.82},
  {"type": "event", "data": {"sound": "silence"}, "score": 0.65},
  {"type": "event", "data": {"sound": "chanting"}, "score": 0.61}
]

LLM is constrained to:

interpret ONLY within this set
6) Integration with ContextBuilder (second hook)

You enhance perception without altering reality.

class ContextBuilder:

    def build(...):
        base = build_base_context(world_state)

        latent = latent_engine.generate(world_state, {"mode": "perception"})

        return merge(base, latent_projection(latent))
Result

You get:

richer descriptions
consistent hidden detail
no state mutation
7) Interaction with Escalation System

This is where most designs break. Here’s the clean boundary:

Escalation = REAL state progression
Latent = POSSIBLE hidden structure
Rule:

Latent candidates may influence which escalation paths become valid, but NEVER trigger them.

Example

Latent candidate:

{"type": "intent", "data": {"guards_suspicious": True}}

This may:

increase probability of guards_alerted event later

But escalation still requires:

actual event trigger
deterministic condition check
8) Interaction with Encounter System

Use the same hierarchy you already outlined:

Encounter = container
Escalation = consequence engine
Latent = hidden structure inference
Inside an encounter:

Latent expansion can generate:

enemy positioning not yet seen
hidden reinforcements (not spawned yet)
morale states

But:

it cannot spawn enemies
it cannot modify encounter state
9) Determinism guarantees (must hold)

You preserve all your guarantees by enforcing:

9.1 Seeded generation
seed = hash(world_state) ^ hash(intent_frame)
rng = Random(seed)
9.2 Pure function requirement
LatentExpansion(world_state, context) → candidates

No side effects.

9.3 No persistence

Candidates are:

ephemeral
recomputed each turn
10) Why this is actually worth adding
Without it:
your system is correct but sparse
AI feels constrained
With it:
you increase perceived depth dramatically
without increasing simulation cost
without losing control
11) When you should delay this

Do NOT implement yet if:

combat loop is incomplete
encounter lifecycle isn’t stable
event system still shifting

Because this layer:

amplifies whatever structure exists

12) Minimal viable implementation (what I’d actually do)

Start small:

Step 1

Implement ONE generator:

def sound_inference_generator(world_state, context):
    # returns possible sound sources based on layout + entities
Step 2

Inject ONLY into:

perception (listening, searching)
Step 3

Cap at 3 candidates

Step 4

Verify:

deterministic output
no escalation interference
no action leakage
13) Final mental model (updated)
WorldState      = Reality
Encounter       = Situation container
Escalation      = Real consequences
Latent Engine   = Hidden possibility space
Adjudication    = Chooses interpretation
Resolver        = Executes truth
Narrative       = Describes perception
Bottom line

This fits your system cleanly if and only if you treat it as:

a deterministic, bounded inference layer that enriches decision-making—never a driver of outcomes

If you want, the next useful step is:

defining 3–5 concrete generators tailored to your dungeon (sound, visibility gaps, AI intent, environmental anomalies)

That’s where this stops being abstract and starts producing measurable improvement.