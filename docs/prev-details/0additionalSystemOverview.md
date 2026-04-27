Below is a cohesive, implementation-ready specification of your system. It is structured so another AI (or you, later) can reconstruct behavior deterministically without guesswork.

No narrative fluff—this is a systems contract.

0. SYSTEM OVERVIEW
Core Principle

Intent is interpreted → Actions are executed deterministically → State is authoritative → Narrative reflects state

Execution Model
User Input
   ↓
Intent Extraction
   ↓
Action Planning (1..N Actions)
   ↓
Action Queue
   ↓
Resolver Loop
   ├─ Reactions (pre)
   ├─ Action Execution
   ├─ World Updates (light, sound, visibility)
   ├─ Reactions (post)
   ├─ Interrupts
   ↓
Narrative Output
1. CORE DATA STRUCTURES
1.1 Intent
@dataclass
class IntentFrame:
    action: str
    target: Optional[str]
    params: Dict[str, Any]
    modifiers: Dict[str, Any]
1.2 Action
@dataclass
class Action:
    tool_name: str
    params: Dict[str, Any]
    modifiers: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[dict] = None
1.3 Action Queue
class ActionQueue:
    def __init__(self):
        self.queue = deque()

    def add(self, action): self.queue.append(action)
    def peek(self): return self.queue[0] if self.queue else None
    def pop(self): return self.queue.popleft() if self.queue else None
    def clear(self): self.queue.clear()
1.4 Tool Contract

All tools MUST return:

{
    "success": bool,
    "trigger": Optional[str],
    "data": dict
}
2. RESOLVER LOOP (AUTHORITATIVE ENGINE)
def resolve_queue(session):
    outputs = []

    while True:
        action = session.action_queue.peek()
        if not action:
            break

        context = build_reaction_context(action, session)

        # PRE-REACTIONS
        reactions = evaluate_reactions(context, session)
        if resolve_reactions(reactions, context, session):
            break

        tool = registry[action.tool_name]

        # CONTEXT VALIDATION
        if tool.context_check(action, session.world_state) < 0:
            action.status = "blocked"
            action.result = {"success": False, "reason": "blocked"}
            outputs.append(action)
            break

        # EXECUTE
        result = tool.func(...)
        action.result = result

        # WORLD UPDATES (CRITICAL ORDER)
        compute_lighting(world_state)
        update_visibility(world_state)
        propagate_sound(world_state)
        update_group_awareness(world_state)

        # POST-REACTIONS
        reactions = evaluate_reactions(context, session)
        if resolve_reactions(reactions, context, session):
            break

        # INTERRUPTS
        if should_interrupt(result, session):
            break

        if not result["success"]:
            action.status = "failed"
            outputs.append(action)
            break

        action.status = "complete"
        outputs.append(action)
        session.action_queue.pop()

    return outputs
3. INTERRUPT SYSTEM
Triggers
"enemy_spotted"
"trap_detected"
"trap_triggered"
Handler
def should_interrupt(result, session):
    t = result.get("trigger")

    if t == "enemy_spotted":
        start_combat(session, result)
        return True

    if t == "trap_detected":
        session.action_queue.clear()
        return True

    if t == "trap_triggered":
        apply_trap_damage(session, result)
        session.action_queue.clear()
        return True

    return False
4. COMBAT SYSTEM
4.1 State
@dataclass
class CombatState:
    active: bool = False
    initiative_order: List[str]
    current_index: int = 0

    def current_actor(self):
        return self.initiative_order[self.current_index]

    def advance(self):
        self.current_index = (self.current_index + 1) % len(self.initiative_order)
4.2 Turn Rule
if combat.active:
    only current_actor may enqueue actions
4.3 NPC Turn
if not player_turn:
    action = npc_ai.select_action(...)
    queue.add(action)
    resolve_queue(...)
    combat.advance()
5. REACTION SYSTEM
5.1 Structure
@dataclass
class Reaction:
    owner_id: str
    trigger: str
    condition: Callable
    action_factory: Callable
    consumes: bool = True
5.2 Evaluation
def evaluate_reactions(context, session):
    for entity in world.entities:
        for reaction in entity.reactions:
            if reaction.trigger != context.action.tool_name:
                continue
            if reaction.condition(context):
                yield (entity, reaction)
5.3 Execution
Runs immediately (NOT queued)
May interrupt main flow
6. STEALTH + VISIBILITY
6.1 State
@dataclass
class VisibilityState:
    hidden: bool
    detected_by: set
6.2 Visibility Rule
visible = (
    has_line_of_sight(observer, target)
    AND tile.light_level >= threshold
)
6.3 Detection
if hidden:
    if perception >= stealth_dc:
        detected
7. LIGHTING SYSTEM
Rule
light_level = max(all light contributions)
Propagation
intensity = source_intensity * (1 - dist / radius)

LOS may block light.

8. SOUND SYSTEM
8.1 Event
@dataclass
class SoundEvent:
    position
    radius
    intensity
8.2 Detection
perceived = intensity * (1 - dist / radius)

if perceived > threshold:
    awareness.last_known_position = source
9. AI GROUP AWARENESS
Shared State
group.shared_awareness = {
    "player_last_seen": (x,y),
    "alert_level": int
}
Behavior
Alert	Behavior
0	patrol
1	investigate
2+	pursue/attack
10. TRAP SYSTEM
Detection
if passive_perception >= detection_dc:
    trigger = "trap_detected"
Trigger
trigger = "trap_triggered"
11. ORDER OF OPERATIONS (NON-NEGOTIABLE)

Every action step MUST follow:

1. Pre-reactions
2. Action execution
3. Lighting update
4. Visibility update
5. Sound propagation
6. Awareness update
7. Post-reactions
8. Interrupt check
12. DESIGN RULES (CRITICAL)
12.1 Authority Rules
WorldState is single source of truth
Tools mutate state
Narrative NEVER mutates state
12.2 Determinism Rules
No LLM decides outcomes
No randomness without explicit roll
All checks are explicit
12.3 Reaction Rules
Reactions are immediate
Reactions may interrupt
Reactions do not queue
12.4 Visibility Rules
Requires LOS AND lighting
Stealth modifies detection, not LOS
12.5 Sound Rules
Sound grants awareness, not vision
Awareness drives AI, not detection alone
12.6 Combat Rules
Same ActionQueue
Turn gating enforced
No alternate execution path
13. EXAMPLE FLOW (FULL SYSTEM)
Input:

“Move north quietly”

Step Sequence:
Intent parsed
Action queued
Move begins

Tile 1:

dark → no visibility
sound emitted → guard awareness increases

Tile 2:

guard hears → moves to investigate

Tile 3:

enters lit tile
visibility check succeeds
→ trigger: enemy_spotted
Interrupt fires
Combat starts
Queue cleared
14. EXTENSION POINTS (SAFE)

You can add without breaking system:

reactions (new triggers)
light types
sound categories
AI behaviors
status effects
15. WHAT THIS SYSTEM GUARANTEES
deterministic outcomes
interrupt-driven realism
modular extensibility
strict AI control boundaries
compatibility with narrative overlay