# SESSION STATE - session 61 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## Active branch: main (both repos)
Clean state. All commits landed.

## What happened this session (session 61)

### Frontier graph - fixed and shipped (commits f1bda3f, 18029f1)
- Root cause found: `resolved=1` in graph_edges means annotation-derived, NOT "is a project
  function." Original frontier query was built on a wrong assumption.
- Fix: suffix-match JOIN on target_id (`LIKE '%.' || f_callee.name`), no resolved filter.
  Verified on test program (3 edges) and dj2 (14 real frontier edges).
- dj2 frontier: validate_action (5 callers), get_player_by_session (4), on_arc_completed,
  _register_world_tools, semantic_match_subrace, others.
- TRACKER item 28 closed (evaluate() split already landed in f902ff2).
- TRACKER item 29 filed: ABC/abstract-method frontier shape (needs class hierarchy schema).

### Frontier tab - extended (commit 18029f1)
Three Tier 1 connections from DISCOVERY_MODEL composability audit:
1. **Mode selector**: Direct (functional->stub) / Chain (stub->stub) / All. Mode change
   reloads graph. Chain nodes shown in gray.
2. **Project button**: appears when a red stub node is selected. Calls
   `project_stub_request` socket event -> `stub_projector.project_stub()` -> shows
   suggested implementation in collapsible panel below graph.
3. **Queue button**: calls `frontier_to_queue` socket event -> `list_stubs()` ranked by
   caller count -> writes each as `workflow_items` next_up entry. Connects frontier ranking
   to `prioritize_work()` planning system.

### DISCOVERY_MODEL.md (commits fa504a3, 8f0906c)
New design document at Determined/docs/DISCOVERY_MODEL.md. Five concepts with exploration
checklists and disposition fields:
- Topology, Frontier, Implementation Queue, Access Paths, Waypoints
- Composability audit section: what already exists vs. what needs connecting
- Mining Priority: Tier 1 (connect existing) > Tier 2 (new prompt) > Tier 3 (new UI) >
  Tier 4 (schema)

## Key existing pieces discovered (composability audit)

Already built in Determined, directly reusable:
- `list_stubs()` - ranks stubs by caller count (Q1 done)
- `stub_projector.py` / `project_stub` tool - implementation scaffold (Q6 done)
- `evaluate_claim()` - Observe->Situate->Evaluate kernel (Q3 backbone)
- `gather_context()` in stub_projector - collects callers + contracts for a stub
- `prioritize_work()` + `workflow_items` + `add_item()` - planning system (Q5 backbone)
- `knowledge_artifacts` + `store_finding()` - generic artifact store (W6 backbone)
- `symbol_context()` - everything known about a symbol (A4 backbone)

## Next session: Tier 2 and Tier 3 from DISCOVERY_MODEL

### Tier 2 - new prompt on existing kernel (~30 lines)
**Q3 stub scorer**: `gather_context(stub)` -> format as claim -> `evaluate_claim(claim,
question="how central is implementing this to making the system runnable?")`.
New agent tool `score_stub` that sequences these two. Adds a "Score" column to
the build queue.

### Tier 3 - new UI rendering of existing data
- **A4 sub-menu popover**: hover any `<span data-sym="X">` -> emit symbol_context ->
  render as floating panel. No new backend. ~40 lines JS + CSS.
- **Q5 Build queue tab**: new tab reading `workflow_items WHERE kind='next_up'` as
  a sortable table. Same data `prioritize_work()` reads, better presentation.
- **W3 Waypoints panel**: new tab reading `knowledge_artifacts WHERE kind='waypoint'`.

### After Tier 3: Tier 4 (schema)
- **A1**: add `is_project_call BOOLEAN` to graph_edges. Converge `list_stubs` (uses
  `callee` column) and frontier query (uses `target_id`) into one canonical lookup.

## graph_edges schema reminder
Columns: id, source_id (caller name), target_id (callee name), caller, callee,
         line_number, caller_file, resolved (annotation-derived bool, NOT is_project_call)

## Hardware facts (unchanged)
- llama-server-3b: NSSM auto service, port 8080
- llama-server-8b: NSSM manual service, port 8081
- Start 8B: `nssm start llama-server-8b` (admin PowerShell)

## Corpus state (dj2)
- DB: C:\Users\bartl\dev\Determined\C_Users_bartl_dev_dj2.db
- 47 stubs, 1319 non-stubs. 14 direct frontier edges.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, use `python`
Active branch in both repos: main
Use PowerShell tool (not Bash). NEVER use python -c with inner quotes - write .py scripts.
