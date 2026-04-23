AI-Driven Dungeon Master System (Unified Spec)

Version: 3.0 (Deterministic Execution + Action Queue Integration)

1. Core Principle

All gameplay emerges from deterministic simulation, shaped by constrained AI judgment, executed through a queued action system, and presented through multimodal systems.

2. System Philosophy (Non-Negotiable)
2.1 Separation of Powers
Layer   Responsibility
Simulation  What is true
Adjudication (AI DM)    What is attempted / should happen
Execution   How it actually unfolds
Presentation    What the player perceives
Progression What should happen next
2.2 Hard Rules
The AI (LLM) must NOT:
roll dice
mutate world state
execute actions
invent outcomes
The AI MAY:
interpret intent
select actions (high-level)
determine if a roll is needed
suggest difficulty (bounded)
shape pacing and tone
control information exposure
3. The 5 Buckets (System Domains)
3.1 Simulation Bucket (Reality Layer)
WorldState
Lighting system
Visibility system
Sound system
Trap system
AI awareness (group + individual)
(future) Combat system
3.2 Interpretation Bucket (Input + Intent)
STT (Faster-Whisper)
Voice processing
LLM intent parsing → IntentFrame
3.3 Adjudication Bucket (AI DM Brain)
LLM (Adjudication Mode)
AdjudicationEngine
Produces AdjudicationDecision (intent-level only)
Campaign influence
3.4 Execution Bucket (Deterministic Engine)

NEW CORE LAYER

ActionPlanner
ActionQueue
Resolver Loop
Reaction system
Interrupt system
Tool execution (via SessionManager)
3.5 Presentation Bucket (Player Experience)
NarrativeEngine
TTS (Kokoro)
Audio system (RAS)
Visual overlays
3.6 Progression Bucket (Campaign Control)
CampaignState
Event system
Phase control
4. The 7 Phases (Execution Order)
1. Input
2. Interpretation
3. Adjudication
4. Execution (Action System)
5. Resolution
6. Presentation
7. Progression
5. Authoritative Data Flow
User Speech
  ↓
STT
  ↓
IntentFrame (LLM - Interpretation)
  ↓
AdjudicationDecision (LLM - Adjudication)
  ↓
ActionPlanner (deterministic)
  ↓
ActionQueue
  ↓
Resolver Loop (execution engine)
  ↓
Tools (via SessionManager)
  ↓
WorldState (mutated)
  ↓
ContextBuilder → UnifiedContext
  ↓
Narrative / Audio / Visual
  ↓
TTS Output
  ↓
Campaign Progression
6. Core Data Models
6.1 WorldState (Single Source of Truth)
class WorldState:
    domain: str
    current_location: str
    party_position: tuple

    terrain: str
    time_of_day: str
    indoors: bool

    population_density: str
    danger_level: float
    party_fatigue: float

    topology_changes: list
    player_knowledge: dict

    dungeon_layout: dict
    fog_of_war: dict

    # NEW SYSTEMS
    lights: list
    traps: list
    sound_events: list
    entities: list
    ai_groups: list
6.2 UnifiedContext (Read-Only Projection)

Unchanged conceptually, but now reflects:

visibility state
awareness
lighting
sound-driven tension
6.3 ContextBuilder (Mandatory)

Transforms WorldState → UnifiedContext

6.4 CampaignState (Global Control)
class CampaignState:
    tension: float
    arc: str
    recent_events: list
    narrative_flags: dict
7. Intent + Action System
7.1 IntentFrame
@dataclass
class IntentFrame:
    action: str
    target: Optional[str]
    params: dict
    modifiers: dict
7.2 AdjudicationDecision (UPDATED)
class AdjudicationDecision:
    type: str  # action | check | auto | event | clarification

    action: str
    parameters: dict

    skill: str | None
    difficulty: int | None

    difficulty_adjustment: int
    tension_adjustment: float
IMPORTANT CHANGE:

Adjudication produces intent, NOT tool calls.

7.3 Action Model
@dataclass
class Action:
    tool_name: str
    params: dict
    modifiers: dict = field(default_factory=dict)
    status: str = "pending"
    result: dict | None = None
7.4 ActionQueue
class ActionQueue:
    queue: deque
7.5 ActionPlanner (NEW)

Converts decision → executable actions

def plan(decision):
    if decision.action == "move":
        return [Action("move_party", decision.parameters)]
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
9. Tool System
Contract
{
    "success": bool,
    "trigger": str | None,
    "data": dict
}
SessionManager Role (UPDATED)
validates tool calls
applies rules
mutates WorldState
returns results

SessionManager is NOT the orchestrator.

10. Reaction System
Immediate, non-queued execution
@dataclass
class Reaction:
    owner_id: str
    trigger: str
    condition: Callable
    action_factory: Callable
Rules
executed immediately
may interrupt
depend on visibility + awareness
11. Interrupt System
Triggers
enemy_spotted
trap_detected
trap_triggered
Behavior
may clear queue
may start combat
may alter state
12. Stealth + Visibility System
Visibility requires:
Line of Sight AND Lighting
Stealth
hides entity
requires perception check to detect
Detection
if perception >= stealth_dc → detected
13. Lighting System
Rule
light_level = max(all light contributions)
Light affects visibility only
14. Sound System
Generates awareness, not vision
SoundEvent:
    position
    radius
    intensity
Effect
updates awareness.last_known_position
15. AI Awareness System
Shared Group Awareness
{
    "player_last_seen": (x,y),
    "alert_level": int
}
Behavior Scaling
Alert   Behavior
0   patrol
1   investigate
2+  pursue/attack
16. Combat System (Integrated)
Uses SAME action system
same queue
same resolver
turn-gated
Combat Rules
only active actor can enqueue
reactions still active
interrupts still valid
17. Narrative System
Structured first
class NarrativeOutput:
    type: str
    summary: str
    details: dict
LLM role
describe outcome
control tone
no state authority
18. Phase Orchestrator (UPDATED)
def run_turn(user_input):

    text = input_phase(user_input)

    intent = interpretation_phase(text)

    decision = adjudication_phase(intent)

    actions = action_planner.plan(decision)

    queue.add(actions)

    results = resolver.resolve_queue(session)

    ctx = context_builder.build(world_state, session)

    narrative = narrative_engine.describe(ctx, results)

    text = llm_format(narrative)

    tts.play(text)

    audio.update(ctx)
    visuals.update(ctx)

    progression_phase(ctx, decision)
19. Determinism Guarantees
Rule    Enforced By
No randomness in LLM    AdjudicationEngine
No state mutation outside SessionManager    Architecture
Ordered execution   Resolver
Single context source   ContextBuilder
20. Failure Modes (Guardrails)
Problem Prevention
AI hallucination    tool-only execution
desync  WorldState authority
pacing chaos    progression phase
narrative contradiction structured outputs
execution drift action queue
21. Final Mental Model
WorldState = Reality
SessionManager = Physics
Resolver = Execution Engine
Adjudication = Judgment
LLM = Voice of the DM
UnifiedContext = Perception
CampaignState = Story Momentum
22. What You Now Have
deterministic simulation
interrupt-driven execution
AI-constrained decision layer
modular systems (lighting, sound, stealth, combat)
scalable architecture
23. What Comes Next (Correct Order)
Combat System (full implementation)
NPC Agents (autonomous via same pipeline)
Encounter System (CampaignState-driven)
Bottom Line

This is now:

a deterministic simulation engine with a constrained AI acting as a true Dungeon Master

—not a narrative system pretending to be one.

If you want the next step, the correct move now is:

→ Full combat spec using THIS exact system under load (multi-entity, reactions, interrupts, stealth)

That’s the real validation point.