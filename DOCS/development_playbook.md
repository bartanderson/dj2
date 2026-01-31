# Development Playbook

## The Phase × Stage Matrix

### INPUT Phase (Receiving Signals)
| Mechanics             | Events                                 | Narrative                          |
|-----------------------|----------------------------------------|------------------------------------|
| Keyboard/mouse parsed | + Event trigger detection (enter room) | + Natural language command parsing |
| Hardcoded command map | + Hotkey context switching             | + Voice-to-intent processing       |

### INTERPRETATION Phase (Understanding Intent)
| Mechanics             | Events                                 | Narrative                          |
|-----------------------|----------------------------------------|------------------------------------|
| Command → Intent dict lookup | + Event condition evaluation    | + AI intent classification         |
| "move north" → MoveIntent | + "is trap triggered?" check       | + "player seems to want to flee"   |

### AUTHORITY Phase (Validation)
| Mechanics             | Events                                 | Narrative                                             |
|-----------------------|----------------------------------------|-------------------------------------------------------|
| "Can move to 5,3?" collision check | + "Can trigger quest X?" prerequisites | + "Is AI suggestion valid?" sanity check |
| Dice rolls for success | + Event probability evaluation | + Confidence threshold validation |

### MUTATION Phase (State Changes)
| Mechanics              | Events                                 | Narrative                                    |
|------------------------|----------------------------------------|----------------------------------------------|
| Direct position update | + Event state changes (quest active)   | + AI-proposed state changes (emotional state)|
| `party.x = 5`          | `quest.status = STARTED`               | `npc.mood = SUSPICIOUS` (via GameEngine)     |

### CONSEQUENCE Phase (Results)
| Mechanics             | Events                                 | Narrative                          |
|-----------------------|----------------------------------------|------------------------------------|
| Silent/null response  | + Event effects (damage applied)       | + AI-generated descriptions        |
| Position updates      | + Unlock door, spawn enemy             | + "The floor trembles as..."       |

### PERSISTENCE Phase (Memory)
| Mechanics             | Events                                 | Narrative                          |
|-----------------------|----------------------------------------|------------------------------------|
| SQLite save           | + Event log append (history)           | + AI memory embedding (context)    |
| Raw state snapshot    | + "Player killed dragon" journal       | + Semantic search index            |

### VIEW Phase (Display)
| Mechanics             | Events                                 | Narrative                          |
|-----------------------|----------------------------------------|------------------------------------|
| ASCII map render      | + Event notification popup             | + Dynamic AI descriptions          |
| Grid display          | + "Quest Complete!" banner             | + Context-aware atmospheric text   |

## The 7-Step Analysis Framework

### Step 1: Declare Responsibility

# File: world_controller.py
RESPONSIBILITY:
- Owns: Party position, current location state
- Does NOT own: Campaign content (maps, NPCs), AI decisions
- Delegates to: SessionSystem (save), DMChatAI (narration), AuthoritySystem (validation)
Step 2: Classify Authority (4 Buckets)
Ask: "Which bucket?"
Bucket 1 (Core): Must be deterministic. If AI can influence it, it's wrong.
Bucket 2 (Adapter): Glue code. If it has "if quest_active" logic, it's wrong.
Bucket 3 (AI-Facing): Can be probabilistic. If it validates dice rolls, it's wrong.
Bucket 4 (Sketch): Marked # EXPERIMENTAL. If imported by production code, it's wrong.
Step 3: Extract Implicit Contracts
For each public method:

Method: move_party(direction)
INPUTS: direction (enum), party_id (str)
OUTPUTS: success (bool), new_position (tuple), events_triggered (list)
INVARIANTS: Party must exist, direction must be cardinal, position must be valid
ERRORS: InvalidDirection, PartyNotFound, MovementBlocked (with reason)
Step 4: Audit Dependency Direction
Draw arrows:

WorldController (Bucket 1/2) → SessionSystem (Bucket 1) ✓
WorldController → DMChatAI (Bucket 3) ✓
DMChatAI → WorldController (direct mutation) ✗ VIOLATION
Arrows must flow 1→2→3 only.
Step 5: Check Phase Compliance
Place code in the matrix:
Is this Interpretation logic doing Mutation work?
Is this Mechanics code trying to do Narrative generation?
Violation Pattern: DMChatHandler._extract_conversation_context() does Interpretation + State Query (mixing phases)
Step 6: Identify Architectural Patterns
Active Record (What you have):
State + Behavior in one class (WorldController)
Good for: Rapid prototyping
Bad for: Testing, phase compliance
Fix: Extract WorldState (data), WorldRuntime (behavior), keep WorldController as thin coordinator
Event-Driven (Target):
State Change → Event → AI Observes → Action Proposal → Engine Validates
Loose coupling, natural AI integration
Fix: Add EventEmitter to SessionSystem, AI subscribes instead of queries
Step 7: Assign Action
[ ] FREEZE - Good enough, don't touch (e.g., working MovementService)
[ ] ADD_CONTRACT - Document interface, no rewrite yet (e.g., ToolRegistry)
[ ] ISOLATE - Wrap with adapter, prevent spread (e.g., DMChatHandler violations)
[ ] REWRITE_SMALL - < 2 hours, clear scope (e.g., extract method)
[ ] REWRITE_MEDIUM - < 1 day, needs planning (e.g., CampaignState rename)
[ ] REWRITE_LARGE - Major refactor, schedule separately (e.g., full Event system)
[ ] DELETE - Dead code (e.g., old puzzle system prototypes)
Common Patterns & Fixes
Pattern: God Object (WorldController 1500+ lines)
Symptoms: Mixes coordination, logic, persistence, AI calls
Fix:
Extract WorldState (pure data model)
Extract WorldRuntime (travel, time mechanics)
Extract SessionFacade (save/load coordination)
Keep WorldController (thin coordinator, routes only)
Pattern: AI Direct Mutation
Symptoms: ai_dungeon_master.py calls world.add_location() directly
Fix:
# BEFORE: AI → WorldState (VIOLATION)
# AFTER: AI → Proposal → GameEngine → WorldState

@tool(name="propose_location")
def propose_location(coords, description):
    return {
        "action_type": "ADD_LOCATION",
        "payload": {"coords": coords, "desc": description},
        "confidence": 0.8,
        "source": "AI"
    }
# GameEngine validates in Authority phase, executes in Mutation phase
Pattern: Phase Mixing (DMChatHandler line 293)
Symptoms: _extract_conversation_context() has PHASE_VIOLATION: Direct AI call for context extraction in Interpretation phase
Fix: Move to DMChatAI boundary (Bucket 3), pass context as parameter from Input phase
Decision Framework: When to Refactor
The 4 Questions
Is it BROKEN? (crashes, wrong behavior)
Yes → Fix immediately (minimal change)
No → Continue
Is it BLOCKING a feature? (can't proceed without it)
Yes → Isolate and work around (adapter pattern)
No → Continue
Is it in the AUTHORITATIVE spine? (Bucket 1, deterministic)
Yes → Freeze or Add Contract (don't break determinism)
No → Continue
Does it CROSS phase boundaries? (Interpretation doing Mutation)
Yes → Isolate immediately (violation)
No → OK for now
The 2-Hour Rule
If estimate > 2 hours:
Isolate with adapter
Document contract
Schedule rewrite
Continue current work
Current System Mapping
-----
Table
Component	Current Stage	Phase Issues	Bucket	Action
WorldController	Mechanics→Events	Mixes phases	1/2 (bleeding)	ISOLATE → REWRITE_MEDIUM
DMChatHandler	Mechanics→Events	Line 293 violation	3 (violating 1)	ISOLATE immediately
GameEngine	Mechanics	Incomplete (no full loop)	1	REWRITE_MEDIUM (complete loop)
ToolSystem	Mechanics	Unguarded (direct mutation)	2 (acting like 1)	REWRITE_SMALL (proposals only)
SessionSystem	Mechanics	Good	1	FREEZE (add contracts)
Dungeon System	Mechanics→Events	Clean via HTTP	2	FREEZE
-----
Windows-Specific Reminders
Commands: python tools\script.py (backslash)
Code paths: "tools/script.py" (forward slash in strings)
Line endings: CRLF (\r\n)
No python -c for multiline (use .py files)
CMD with activated env (not PowerShell)
Conversation Starters for AI
For Quick Analysis:
"Analyze [filename] using 7-step framework. Responsibility? 
Authority bucket? Phase placement? Critical violation?"
For Architecture Decisions:
"Comparing [Option A] vs [Option B] for [feature].
Evaluate: Phase compliance, Stage appropriateness, Risk to existing.
Recommend with concrete next step."
For Bug Triage:

"Bug: [description]. 
Apply decision framework: Quick fix, Isolate, or Refactor underlying cause?"
For Code Review:

"Review this diff against ai_contract.md. 
Any phase violations? Bucket misclassifications? Dependency direction errors?"
---
Recommended Reading Order
Start Here (30 minutes):
Dev.to Big Ball of Mud  - Validates your pain
https://dev.to/m_midas/big-ball-of-mud-understanding-the-antipattern-and-how-to-avoid-it-2i
Medium: Transition to Microservices  - Practical pattern mapping
https://medium.com/@milos.kecman/transition-from-a-monolithic-application-to-microservices-a5184fb4c417
Deep Dive (2 hours):
3. Master's Thesis: Refactoring Patterns  - See Chapter 4 "Migration Patterns Catalogue"
https://is.muni.cz/th/f8zv4/Master_Thesis.pdf
Pattern FD1 (Strangler): Your GameEngine delegation
Pattern AX4 (Anti-corruption layer): Your HTTP bridge/phase boundaries
Pattern BD1 (Domain-driven decomposition): Your Mechanics/Events/Narrative stages
Academic Context (skim):
4. ArXiv Mo2oM  - Just the "Soft Clustering" section (explains why WorldController temporarily violates boundaries)
https://arxiv.org/html/2508.07486v1
Practical Application to Your Current Work
Validate Your ai_contract.md
Compare to Clean Architecture principles:
✅ "Dependency direction: Core → Interface → AI" = Clean Architecture dependency rule
✅ "AI NEVER mutates state" = Domain logic isolated from infrastructure (AI is infrastructure)
✅ "GameEngine as coordinator" = Use Cases layer in Clean Architecture
Validate Your development_playbook.md
Compare to Migration Patterns:
Your "7-Step Framework" = Combination of AX1 (Recover Architecture) + BD1 (Domain Decomposition) + FD1 (Strangler Pattern)
Your "2-Hour Rule" = Incremental migration best practice from thesis
Your "Isolate vs Rewrite" = Branch by Abstraction vs Greenfield decision tree
Your Git References
The thesis specifically mentions:
"Monolith clarity and architecture recovery can be omitted if the detailed description of the current architecture already exists"
You have this: Your PHASE_AUDIT.md + four_layer.py output = Architecture Recovery documentation. You're ahead of most migration projects.
The "8th Phase" You Saw
You mentioned 8 phases earlier. You likely saw RUP's Inception/Elaboration/Construction/Transition mapped against your Input/Interpretation/Authority/Mutation/Consequence/Persistence/View.
The relationship:
Your 7 runtime phases happen within each RUP phase
During Elaboration (where you are), you verify that all 7 runtime phases are correctly implemented before moving to Construction (adding Events/Narrative features)
Key Takeaway: Don't build Stage B (Events) until your Stage A (Mechanics) passes all 7 runtime phase validations. This is exactly what RUP's "elaboration" milestone requires.
You're not just refactoring—you're performing a textbook architecture recovery following industry-standard migration patterns. The documents I created (ai_contract.md, development_playbook.md) are your AX1 (Architecture Recovery) and BD1 (Domain Decomposition) deliverables per the academic literature.
---
## What to Do With These

1. **Save** `ai_contract.md` to project root (this becomes your Ollama system prompt)
2. **Save** `development_playbook.md` to project root (your reference, load excerpts when needed)
3. **Archive** the original 13 files (keep for history, don't load into context)
4. **Update** your `scripts/build_context.py` to pull from `ai_contract.md` instead of scattered files

**Validation**: The matrix shows exactly what you wanted - examples of what belongs in Mechanics vs Events vs Narrative at each phase. The 7-step framework gives you the method to analyze any file against these coordinates.
