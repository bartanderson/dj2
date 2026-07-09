# SESSION STATE - session 67 handoff
_Overwrite completely each session. Not authoritative - see dj2/TRACKER.md for truth._

## Active branch: main
Clean state. No code changes this session.

## What happened this session (session 67)

### World Compiler / Semantic Runtime architecture ingested

Bart shared a detailed architecture proposal: Semantic Runtime and World Compiler.
Key insight: the world description language becomes the language of the system,
not code for elements of it. Compiler generates runtime machinery from declarative
schemas rather than hand-wiring it.

**New item filed:**
- G0: World Description Language and IR — foundation layer, precedes G1/G2/G3
  - Research gate: Inform 7 entity model, Souffle (Datalog), Bevy ECS scheduler,
    Greg Young on event sourcing
  - Scope: define entity schema format + event consequence model only
  - Deliverable: design note with Door/Goblin/Torch examples + compile target
  - Shape rules: no Turing-complete schemas, keep IR and runtime separate

**Dependency chain updated:**
G0 -> G1/G2 -> G3 -> G4 -> World Exploration -> Dungeon

## Next session priorities
1. G0: Research gate (Inform 7, Souffle, Bevy scheduler, Greg Young event sourcing)
   then write the design note specifying entity schema and event consequence formats
2. G1: Analyze world event chain (blocked on G0 schema decisions for new wiring)
2. G2: World decoration/overlay system (Door schema is a G0 deliverable example)
3. G3: NarrativeService (CONSEQUENCE phase narration, single-shot LLM)

## Hardware facts
- LLM: Qwen3-8B, on-demand subprocess started by Determined UI on launch (port 8081)
- No NSSM services. Model managed by Determined via llm_client.py.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, use `python`
Use PowerShell tool (not Bash). NEVER use python -c with inner quotes - write .py scripts.
