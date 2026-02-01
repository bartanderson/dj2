# AI Contract - Dungeon Journey 2

## Absolute Constraints
- **AI NEVER owns state** - Read-only access to SessionSystem
- **AI NEVER mutates state directly** - All changes via GameEngine
- **AI ONLY requests actions via interfaces** - Tool calls return proposals, not execution
- **Windows Reality**:
  - Use backslashes in CMD: `python tools\script.py`
  - CRLF line endings
  - NO `python -c` for multiline scripts - use .py files instead
  - Single-line `python -c` only for very simple commands
  - Example of what DOES NOT work:
    ```cmd
    python -c "
    print('hello')
    print('world')
    "
    ```
  - Example of what works:
    ```cmd
    python -c "print('hello'); print('world')"
    ```
  - Better: Create a script file. The user reuses test.py, so if its one time thats what they use.

## The 7 Runtime Phases (The Conveyor Belt)
Every command cycles through:
1. **INPUT**: Raw signals (clicks, keys, network)
2. **INTERPRETATION**: Intent classification (AI-assisted in Narrative stage)
3. **AUTHORITY**: Validation (dice, rules, permissions)
4. **STATE MUTATION**: Apply changes (SessionSystem only)
5. **CONSEQUENCE**: Effects, narration (AI assists here)
6. **PERSISTENCE**: Save, logs, snapshots
7. **VIEW PROJECTION**: Render, UI update

Rule: Never skip, never reverse, never combine adjacent phases.

## The 4-Bucket Authority Hierarchy
- **Bucket 1 (Core)**: Game rules, validation, persistence - Deterministic, testable, AI treats as oracle
- **Bucket 2 (Adapter)**: Tool registries, HTTP bridges, serialization - No business logic
- **Bucket 3 (AI-Facing)**: Prompt construction, narrative selection - Non-authoritative, suggestions only
- **Bucket 4 (Sketch)**: Prototypes, experiments - Never imported by Bucket 1

## Dependency Direction (Invariant)
Core (Bucket 1) → Interfaces (Bucket 2) → AI Systems (Bucket 3)
Never reverse. Bidirectional arrows indicate violation.

## The Ownership Rule
If a system VALIDATES rules → it MUST OWN the state it validates.
No "advisory authority" - control it or don't touch it.

## Stage Definitions (Capability Maturity)
- **Mechanics**: Deterministic simulation (movement, combat, saves)
- **Events**: Reactive system (triggers, quests, consequences)
- **Narrative**: AI integration (interpretation, dynamic narration, memory)

Progression: Mechanics solid → Events added → Narrative layered on top.