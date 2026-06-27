# SESSION STATE - session 26/27 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## What happened this session (session 26)

**Caught up from stale session 23 handoff. Built corpus map UI. Established
the mentor capability arc for Determined's next phase.**

### Catch-up findings
- SESSION_STATE.md was frozen at session 23. Determined had moved to session 25.
- tools/audit branch is fully contained in main - safe to delete, not blocking.
- Items 4, 5, 20, 21 were closed in sessions 24/25 (stub projector, editor,
  UI tabs, bag wiring). All on main.

### ui/corpus-map branch (2 commits, not yet merged)
Built a pinned corpus map panel that appears above the chat scroll on corpus
load. Shows:
- Roots: uncalled entry points ranked by fan-out (doors into the system)
- Core: most-called symbols (weight-bearing walls)
- Stats strip with stubs count and "view stubs" link

Key design decisions made:
- Pinned above scroll (flex-shrink:0), not injected into results list
- Collapses with toggle button
- Risk badges from pre-computed knowledge_artifacts only - no score_risk()
  calls at connect time (was 10+ queries per symbol; now one bulk query)
- Stubs replaced with count + link to query; stubs are workflow, not map
- Sections named "Roots (uncalled)" / "Core (most-called)" to communicate
  architectural poles, not just list names

Needs: Bart validates in running UI, then merge to main (TRACKER item 25).

### Key design conversation: Determined's mentor capability arc

Framing established (TRACKER items 22-25):
Determined's goal is to approximate what Claude does with a codebase - not
answer structural queries but navigate: orient, identify risk, surface the gap
between current code and design intent, guide the developer toward a goal.

Three capabilities needed, in this order:

1. Item 22 - Design doc extraction (prerequisite)
   Auto-mine markdown design docs into design_note artifacts using 3B model.
   mine_design_docs.py has the right shape but is a hardcoded list.
   Source of truth should be the actual docs (00A, 00B, 00F in dj2/docs/design/).

2. Item 23 - Frame comparison (builds on 22)
   Surface design notes automatically when code analysis touches a documented
   area. Subject-key lookup (filename/classname match), not semantic search.
   Include matching design notes in LLM context for spotlight/risk answers.
   This gives the tool the "desired frame" to compare against current code state.

3. Item 24 - Goal intake (builds on 23)
   Developer states intent -> tool translates to structural search -> assembles:
   design rules that apply + hot/safe zones + relevant stubs + safe insertion
   point -> returns navigation plan, not a fact answer.

Architecture insight: the 3B model is a connector of pieces, not a memory.
DB holds structured knowledge (code graph + design notes + findings).
Tool assembles the right context window; model reasons over what it is given.

## Current state

Branch: ui/corpus-map (Determined), 2 commits ahead of main
Tests: 321/322 passing (1 pre-existing stale fixture failure, unrelated)
Main: stable, all prior items merged

## FIRST THING NEXT SESSION - do this before anything else

Start the server, load the dj2 corpus, look at the corpus map panel.

   cd C:\Users\bartl\dev\Determined
   .venv\Scripts\python.exe -m determined.agent.local_agent --ui
   Load: C_Users_bartl_dev_dj2.db  (via Resume button)

Does the Roots/Core panel orient you to the codebase, or is it noise?
This verdict shapes everything that follows. If it orients, the ambient
structural knowledge approach works and items 22-24 build on top of it.
If it is noise, we learn what "useful" actually requires before building more.

Report what you see before starting any other work.

## What is next (after the verdict)

1. Merge ui/corpus-map to main if panel is useful. Revise if not.

2. Item 22 - Design doc extraction - read dj2 design docs, build extractor
   that uses 3B model to pull invariants/rules/boundaries into design_note
   artifacts. Start with 00A ARCHITECTURAL_CONSTITUTION.md (most explicit rules).
   Output shape matches existing DESIGN_NOTES tuples in mine_design_docs.py.

3. Item 23 - Frame comparison wiring - in spotlight + risk_profile handlers,
   look up design_note artifacts matching the symbol's file/classname and include
   them in the LLM context. Requires item 22 first.

4. Item 24 - Goal intake - after 22+23 are in place, new query mode where
   developer states a goal and tool assembles goal-scoped orientation.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, separate venv
UI: python -m determined.agent.local_agent --ui then http://127.0.0.1:5050
Active branch: ui/corpus-map (Determined)
