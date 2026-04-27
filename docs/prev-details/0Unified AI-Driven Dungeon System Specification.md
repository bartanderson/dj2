Below is a single authoritative specification that unifies your voice system, dungeon engine, narrative layer, audio system, and overlays into one coherent, deterministic architecture. This is written so another system (or future you) can implement directly without reinterpretation.

Unified AI-Driven Dungeon System Specification

Version: 1.0
Purpose: Deterministic, interruptible, multimodal (voice + visual + audio) RPG engine with strict system boundaries and tool-driven AI.

1. Core Architectural Principle

All systems derive behavior from a single canonical state projection.

There is exactly one truth:

WorldState → SessionManager → UnifiedContext → All Systems

No system may:

Mutate state outside SessionManager
Infer hidden state independently
Maintain divergent representations
2. System Topology
[Voice Input]
    ↓
[STT (Faster-Whisper)]
    ↓
[Voice Orchestrator]
    ↓
[LLM - Tool Selection ONLY]
    ↓
[SessionManager]  ← ONLY mutation layer
    ↓
[WorldState]
    ↓
[ContextBuilder]
    ↓
[UnifiedContext]
    ├──► NarrativeEngine
    ├──► Audio System (RAS)
    ├──► Visual Overlay System
    └──► LLM (Formatting ONLY)
             ↓
         [TTS (Kokoro)]
3. Authoritative Data Model
3.1 WorldState (Source of Truth)
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

    # dungeon-specific
    dungeon_layout: dict
    fog_of_war: dict
3.2 SessionManager (ONLY mutation authority)

Responsibilities:

Validate actions
Apply rules
Trigger events
Update WorldState
class SessionManager:

    def handle_action(self, tool_name: str, args: dict) -> dict:
        # central dispatcher
        ...

    def move_party(self, direction: str, steps: int) -> dict:
        ...

    def interact_door(self, door_id: str, action: str) -> dict:
        ...

    def roll_check(self, skill: str, difficulty: int) -> dict:
        ...
3.3 UnifiedContext (Canonical Projection)
class UnifiedContext:
    # spatial
    domain: str
    location: str
    position: tuple

    # environment
    terrain: str
    time_of_day: str
    indoors: bool

    # activity
    activity: str

    # narrative state
    mood: str
    tension: float
    event: str | None

    # population
    presence: str

    # system metrics
    danger: float
    fatigue: float

    # knowledge
    knowledge: dict

    # structural changes
    topology_changes: list
3.4 ContextBuilder (MANDATORY)
class ContextBuilder:

    def build(self, world_state, session_state) -> UnifiedContext:
        return UnifiedContext(
            domain=world_state.domain,
            location=world_state.current_location,
            position=world_state.party_position,

            terrain=world_state.terrain,
            time_of_day=world_state.time_of_day,
            indoors=world_state.indoors,

            activity=session_state.activity,

            mood=self._derive_mood(world_state),
            tension=self._derive_tension(world_state),
            event=session_state.current_event,

            presence=world_state.population_density,

            danger=world_state.danger_level,
            fatigue=world_state.party_fatigue,

            knowledge=world_state.player_knowledge,
            topology_changes=world_state.topology_changes
        )
4. Tool System (LLM Interface Contract)
4.1 Rule

LLM may ONLY act via registered tools.

4.2 Tool Schema
TOOLS = {
    "move_party": {...},
    "interact_door": {...},
    "roll_check": {...}
}
4.3 Execution Layer
def execute_tool_call(call):
    tool = TOOLS.get(call["name"])
    if not tool:
        return {"error": "invalid_tool"}

    args = validate(call["arguments"], tool["schema"])
    return tool["handler"](**args)
5. Narrative System (GAIA-Aligned)
5.1 Input
class NarrativeInput:
    context: UnifiedContext
    recent_events: list
5.2 Output (STRUCTURED FIRST)
class NarrativeOutput:
    type: str
    summary: str
    details: dict
5.3 Rule

NarrativeEngine NEVER mutates state.

6. LLM Roles (Strict Separation)
6.1 Mode A: Tool Selection

Input:

user text
allowed tools
summarized context

Output:

{ "tool_call": { "name": "...", "arguments": {...} } }
6.2 Mode B: Narrative Formatting

Input:

NarrativeOutput

Output:

natural language text only
6.3 Forbidden

LLM must NOT:

roll dice
modify world state
invent outcomes
7. Audio System (RAS Integration)
7.1 Input
AudioContext = map(UnifiedContext)
7.2 Mapping
def map_audio_context(ctx):
    return {
        "domain": ctx.domain,
        "location": ctx.location,
        "mood": ctx.mood,
        "intensity": ctx.tension,
        "activity": ctx.activity,
        "time_of_day": ctx.time_of_day,
        "indoors": ctx.indoors,
        "presence": ctx.presence,
        "danger": ctx.danger
    }
7.3 Rule

Audio reacts to state, never drives it.

8. Visual Overlay System
8.1 Input
UnifiedContext.topology_changes
8.2 Example
[
    {"type": "door_opened", "id": "D12"},
    {"type": "wall_broken", "position": (4, 7)}
]
8.3 Rule

Visual layer reflects state changes, does not infer them.

9. Voice System (Interruptible Loop)
9.1 Pipeline
Mic → VAD → STT → Orchestrator → LLM → Tools → Engine → TTS
9.2 Cancellation Model
class CancelToken:
    def cancel(self): ...
    def is_cancelled(self): ...
9.3 Interruption Rule

User speech immediately cancels:

TTS playback
LLM generation
9.4 Priority
User Input > Everything
10. Execution Loop (Authoritative Flow)
def main_loop(user_input):

    # 1. Tool selection
    tool_call = llm_select_tool(user_input)

    # 2. Execute
    result = session_manager.handle_action(
        tool_call["name"],
        tool_call["arguments"]
    )

    # 3. Build context
    ctx = context_builder.build(world_state, session_state)

    # 4. Narrative
    narrative = narrative_engine.describe(ctx, result)

    # 5. Format response
    text = llm_format(narrative)

    # 6. Output
    tts.play(text)

    # 7. Parallel updates
    audio.update(ctx)
    visuals.update(ctx)
11. Determinism Rules (Non-Negotiable)
All randomness lives in SessionManager
All state mutations go through SessionManager
UnifiedContext is read-only
LLM is stateless and non-authoritative
12. Synchronization Rule

All downstream systems update only AFTER WorldState mutation completes.

No speculative updates. No partial state reads.

13. Minimal Implementation Slice (First Milestone)

Must support:

Voice input
Move command
Door encounter
Door interaction
Dice roll
Narrated result
Audio + visual update
Interrupt mid-speech
14. Extension Points

Once stable:

Combat system (same tool pipeline)
NPC agents (read UnifiedContext)
Memory/RAG (read-only augmentation)
Multi-party control
Advanced sound layering
15. Failure Modes to Guard Against
Issue	Cause	Fix
Desync	multiple state sources	enforce UnifiedContext
hallucinated actions	LLM autonomy	tool-only execution
audio lag	no cancellation	enforce token
narrative drift	freeform text	structured outputs
visual mismatch	inferred state	topology_changes only
16. Final Directive

This system works only if you enforce discipline:

No shortcuts around SessionManager
No “just this once” LLM decisions
No duplicate context builders

If you follow this strictly, you get:

deterministic gameplay
real-time voice interaction
scalable systems (combat, NPCs, world)
zero hallucination drift

If you want next, the logical step is:

combat system spec using this exact pipeline, or
direct wiring into your dungeon generator + fog-of-war code paths to validate the loop end-to-end.