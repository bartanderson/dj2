# SESSION STATE - session 63 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## Active branch: main (both repos)
Clean state. All commits landed.

## What happened this session (session 63)

### Reasoning pipeline R1-R4 (commits 041b8e3, 48fd0f2)
New file: `determined/agent/reasoning_engine.py`
- **Decomposer** (R1): calls quality LLM (port 8081) to break an architectural question
  into sub-questions with routing hints (db vs evaluate)
- **Router** (R2): dispatches each sub-question to deterministic DB query or evaluate() kernel
  - DB routes: caller_count, callee_count, class_membership, sibling_pattern, import_coupling, is_stub
  - evaluate routes: sots_match, design_judgment
- **Synthesizer** (R3): calls quality LLM with assembled findings, produces recommendation + confidence
- **reason_about()**: full pipeline function, accepts optional knowledge_conn for persistence
- **RM8 persistence**: _store_chain() writes reasoning_chain artifacts to knowledge_artifacts
- **Staleness detection**: _check_stale_chain() compares stored vs current caller_count

`determined/agent/agent_tools.py`: reason_about tool registered in TOOLS, passes knowledge_conn

### UI wiring (commit 8a53fd2)
`stub_projector.py`: _strip_fences() removes markdown code fences from suggested_body

`ui_server.py`: two new socket handlers:
- `stub_score_quick` - fast DB-only score (caller_count, is_stub, risk_level), no LLM
- `reason_about_request` - full pipeline, emits reason_about_result

`console.html` Frontier tab:
- "Reason" button alongside "Project" (shown only when stub selected)
- Node tap fires stub_score_quick; result shows HOT/WARM/SAFE badge + caller count in status bar
- reason_about_result renders in same fg-projection panel as project output
- fgLoad_ hides both buttons on reload

### REASONING_MODEL.md updated
RM1-RM4 marked done with disposition notes. RM5 (UI) is next but backend is now solid.

## DB routes verified against dj2 corpus (validate_action)
- 7 callers, is_stub=yes, standalone function, 2 validate* siblings, 0 import coupling

## Testing needed (manual, on Windows hardware)
1. Start Determined server + load dj2 corpus
2. Load Frontier tab, click a stub node
   - Status bar should show HOT/WARM/SAFE badge + caller count immediately
   - "Project" and "Reason" buttons should appear
3. Click "Project" - projection should show clean code (no markdown fences)
4. Click "Reason" - reasoning panel shows sub-questions + recommendation (~60s with 8B cold)
5. Run `reason_about question="should validate_action be a standalone function?" symbol=validate_action` in chat
6. Check knowledge_artifacts for kind='reasoning_chain' after step 4/5

## Remaining REASONING_MODEL items
- RM5: UI panel refinements (incorporate Build queue, Pins, score into cohesive layout)
- RM6: 3B vs 8B benchmark on Router evaluate() calls
- RM7: confidence aggregation test (deliberately conflicting sub-answers)
- RM8: done (persistence implemented)
- RM9: connect to Q4 MCTS (future)

## Hardware facts (unchanged)
- llama-server-3b: NSSM auto service, port 8080
- llama-server-8b: NSSM manual service, port 8081 (quality tier, needed for Decomposer + Synthesizer)
- Start 8B: `nssm start llama-server-8b` (admin PowerShell)

## Corpus state (dj2)
- DB: C:\Users\bartl\dev\Determined\C_Users_bartl_dev_dj2.db
- 47 stubs, 1319 non-stubs. 14 direct frontier edges.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, use `python`
Active branch in both repos: main
Use PowerShell tool (not Bash). NEVER use python -c with inner quotes - write .py scripts.
