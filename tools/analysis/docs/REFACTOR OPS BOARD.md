🧭 EXECUTION PATH (ORDERED — DO NOT MIX WITH CHECKBOXES)
Next up scratchpad
--- --- ---
Do NOT expand anything new yet.

Next single focus:

    fix oracle_router expansion boundaries (depth + intent enforcement)
    PRIORITY: oracle_router expansion boundaries
    BUT now precisely interpreted as:
    enforce intent-consistent traversal budgets + semantic purity of expansion
    NOT just depth tuning

Then:

    expose DB-backed symbol discovery API 
        this becomes the only seed authority

Then:

    introduce QuerySession (this is your first “real oracle” moment)
        first true “oracle runtime object”
        assessor-owned execution context
        replaces ad-hoc query execution

If you want next, I can do something very useful for you:

👉 draw the exact engine → assessor data flow diagram using your real functions, so you can see where every current function will move.

That will make this click immediately without theory overhead.
--- --- ---

PHASE 1 — ENGINE STABILIZATION (CURRENT CRITICAL PATH)
Goal:

Make oracle_router deterministic under ontology constraints

[ ] oracle_router expansion boundaries
- intent → traversal budget enforcement
- forward vs reverse weighting stabilization
- eliminate structural over-expansion (implementation leakage)
- [x] remove implementation-level symbols from expansion results
  → DONE 2026-06-16: builtin + accessor-chain noise filtering unified into
    oracle/symbol_noise.py (is_noise_symbol / is_accessor_chain_noise),
    used by BOTH discovery-time seeding (db_oracle._discover_token) and
    expansion-time filtering (oracle_router._is_valid_symbol). Builtin
    classification is DB-authoritative (DBOracle.builtin_symbols()), no
    hardcoded word list left to drift. Budget enforcement and forward/
    reverse weighting are still open.
[ ] seed discipline enforcement
- seeds ONLY from discovery API (not caller injection)
- enforce DB-backed bootstrap constraint

PHASE 2 — QUERY DISCOVERY SYSTEM (NEXT DEPENDENCY)
[ ] DB-backed symbol discovery API (critical)

Replace all engine-origin symbol seeding with:
- list_symbols
- find_symbols
- find_files
- find_modules
✔ MUST be DBReader-only

PHASE 3 — ASSESSOR AS ORACLE CORE (MAJOR ARCHITECTURAL SHIFT)
[x] introduce QuerySession (FIRST TRUE ORACLE OBJECT) — implemented in
    assessor/query_session.py (class QuerySession, line ~127).
    2026-06-16: added durable history — query_sessions table +
    oracle/persist_query_session.py, written best-effort (try/except,
    never breaks the query contract) on every run_query() call.

QuerySession owns:
- snapshot binding
- router execution
- trace capture
- result normalization
- reasoning output packaging
👉 This is the moment engine stops being “query relevant”

[ ] move query execution fully into Assessor
- route_query becomes Assessor-owned
- DBOracle becomes pure kernel only
- no semantic interpretation in DB layer


PHASE 4 — ORACLE HARNESS STABILIZATION
[ ] DB-only execution mode
- no engine dependency in query path
- deterministic replay support
- query reproducibility guaranteed

PHASE 5 — REASONING TRACE EXPOSURE (ALREADY PARTIALLY ACTIVE)
[ ] expose expansion trace as first-class API
You already partially have:
✔ seed_paths
✔ expansion trace
✔ node inclusion reasons

Now formalize:
- expansion_explanation()
- seed_explanation()
- intent_mapping_trace()

PHASE 6 — WEIGHTED SEMANTIC SCORING (LATER)
[ ] replace heuristic scoring entirely
- transition from rule-based pruning → trace-weighted ranking
- derive influence from expansion provenance, not structural counts
-----------------------------------------------------------------------
🧭 REFACTORED OPS BOARD (CLEAN + FINALIZED STATE)
TRUTHS (LOCKED)
SymbolIdentity owns identity (no exceptions)
Graph is DB-derived truth (no heuristic writes)
Invariants are post-construction only (no influence on build path)
Routing is logically split; physical separation is complete but coupling remains in expansion strategy:
symbol_router → intent + seed discovery
oracle_router → expansion + pruning + planning
Query layer operates only on graph truth
LEGEND
[ ] pending
[-] in progress
[x] done
[!] blocked / needs decision

IDENTITY LAYER

[x] SymbolIdentity active and stable in runtime
[x] identity authority consolidated
[x] identity migration complete
[ ] unify identity factory entrypoint (single creation path)

CLASSIFICATION LAYER

[x] routing separated via symbol_router
[x] classification operates on routed domain only
[ ] unify classification imports (single source path)
[ ] eliminate residual dual routing paths in tests

INGESTION

[x] AST extraction stable
[-] alias_map normalization consistency under observation
[ ] finalize dotted-name policy:

canonical identity preserved in graph
tokenization only for discovery layer
NEVER used as identity mutation
GRAPH

[x] edge persistence schema stable
[x] graph deterministic (DB aligned)
[x] invariant validation stable (post-build only)
[ ] verify all query consumers are DB-backed only
→ no in-memory fallback paths remain anywhere


ARCHITECTURE SPLIT

[ ] create contracts layer
[ ] create assessor layer
[ ] move query stack into assessor
[ ] enforce DB-only boundary
[ ] remove engine/query coupling



QUERY LAYER

[x] context / surface / impact stable
[x] cross-run deterministic behavior confirmed
[x] oracle query surface integrated

[ ] REMOVE engine-owned or caller-supplied seed selection
→ symbol discovery must become router bootstrap (no external caller dependency)

[ ] ADD symbol discovery API as unified bootstrap layer
→ list / find symbols / files / modules exposed through single entrypoint

[ ] ADD ranking refinement layer (post-router enhancement)
→ upgrade pruning from heuristic scoring → trace-informed scoring

[ ] DEFINE QUERY SURFACE API AS FIRST-CLASS ENTRYPOINT
→ includes:
    list_symbols
    find_symbols
    list_files
    list_modules
→ must be DBReader-backed ONLY (no engine coupling)

ROUTING LAYER

[x] intent detection stable (symbol_router)
[x] seed generation stable
[x] oracle_router functional
[ ] validate intent-specific expansion quality
    → impact_query should primarily return reverse dependency zones
    → surface_query should primarily return forward structural zones
    → general_query should balance both without exploding scope

[!] CURRENT ISSUE:
oracle_router expansion now supports explicit traversal control but intent policies are not yet tuned
    → depth limits need calibration
    → forward vs reverse influence balance needs calibration
    → [x] expansion includes too many implementation-level symbols
      RESOLVED 2026-06-16 via DB-backed noise unification (see PHASE 1 note above)

depth constraints consistency
traversal boundary discipline per intent

REASONING LAYER

[ ] answer architectural questions from graph truth
[x] expansion trace capture implemented
[ ] expose deterministic reasoning primitives:

seed selection explanation
expansion justification trace
intent → primitive mapping trace

[x] expose expansion reasoning view (node_reasons → API surface)
```_route_expand() now produces:
        seed_paths
        expansion trace
        node inclusion reasons
    These are being returned in execution_plan["trace"]
    You have already validated them in engine output.
```
[ ] identify structural influence and dependency zones
[ ] support oracle-style interrogation queries
[ ] oracle execution feedback loop (query → refinement signal)

CONTRACTION LAYER

[ ] deferred until query fragmentation observed in real usage ✔

TEST SUITE

[x] invariant regression resolved
[x] engine snapshot stable
[ ] project symbol ordering must be DB-deterministic (no insertion-order reliance anywhere)
[ ] minimal oracle CLI smoke test harness needed
[-] regressions classified as expected stabilization noise
[x] regression suite added 2026-06-16: tests/regression/test_oracle_router_persistence_lock.py
    covers noise-filter unification (builtin via DB not wordlist, accessor-chain
    filtering, dead _apply_intent_weights removal) and QuerySession DB persistence
    (incl. persist-failure-does-not-break-query case)

NOTES (CLEAN STATE SUMMARY)
instrumentation is structurally sufficient
DB remains authoritative truth source
invariants are post-build validation only
system is stable for expanding query capability layer
routing split is complete structurally, still evolving behaviorally
next real dependency gap: symbol discovery bootstrap API
next architectural evolution: expansion trace → weighted influence model

---------------------------------------------------
## 🧭 AGENT READINESS ASSESSMENT (2026-06-16, evidence-based)

**UPDATE 2026-06-16 (later same day) — both gaps below are now CLOSED.**
- The "no wired front door" gap is closed: `Assessor.all_views()` /
  `Assessor.ask()` (assessor/assessor.py) wire all 5 Truth Layer views
  (including the previously-orphaned SUMMARY/SUBSYSTEM) to real DB-backed
  data, and `tools/analysis/ask.py` is the real CLI entrypoint —
  `python tools/analysis/ask.py <db_path> "<question>"` — that calls
  `assessor.ask(question)` end-to-end. Verified by direct run against the
  real project DB (`C_Users_bartl_dev_dj2_tools_analysis.db`): NL question
  → oracle router intent → AI compiler (fallback path) → AST → executor →
  real STRUCTURE/INTEGRITY views, no stubs anywhere in the path.
- New permanent regression coverage:
  `tools/analysis/tests/regression/test_run_algebra_end_to_end.py` (4
  assert-based tests: all 5 views build from real seeded data,
  SUMMARY/SUBSYSTEM execute through the algebra, `ask()` runs end-to-end,
  `ask()` is deterministic across repeated calls). All 4 pass, plus the
  pre-existing `test_oracle_router_persistence_lock.py` (6 tests) and
  `truth/tests/test_query_algebra.py` (32 tests) — 42 tests total,
  confirmed passing together in the sandbox after this session's edits.
- The "legacy dead-end agents" gap is closed by deletion, not just a
  warning marker: `oracle/agent.py` (GraphOracleAgent), `oracle/nl_agent.py`
  (NaturalLanguageGraphAgent), `tests/debug/oracle_compare_harness.py`
  (their only real consumer), and `truth/test_harness.py`
  (TruthTestHarness — non-asserting print-only runner, zero real callers)
  have all been removed. Confirmed via repo-wide grep: zero remaining
  references in any `.py` file (only this historical note and stale
  `__pycache__` entries, which have been cleaned, mention the old names).
  `ask.py` + `Assessor.ask()` are what replaced them, per Bart's
  conditional approval ("If you have something better they can both go").

Question asked (as of the original assessment below): is this ready to
power a real AI agent yet?

Short answer at the time: the pieces are individually solid, but there is no wired
front door. Nothing currently connects "agent asks a question" to "Truth
Layer answers it" in a live, running path.

Evidence, by layer:

**Ingestion / graph (mature):** AST extraction, graph build, DB
persistence, invariant validation — all DB-backed, all have regression
coverage, all stable per existing test suite. Not a blocker.

**Query/reasoning core (solid but disconnected):** oracle_router (intent
+ expansion), QuerySession (lifecycle + DB-persisted history), and the
Truth Layer (AST/Planner/Executor, 25+ tests) are each individually real
and tested. But `QuerySession.run_algebra()` — the one method that chains
real NL → AI compiler → AST → executor → real views — has **zero callers
anywhere in the codebase**. It has never been run end-to-end against a
live project DB. Confirmed by direct grep: `route_query`/`QuerySession(`/
`.session()` are only ever invoked from inside their own modules, the
regression suite, and the debug comparison harness — never from anything
that looks like a usable entrypoint.

**No production entrypoint exists.** `run.py` / `debug_run.py` only run
the *ingestion* pipeline (build the graph + DB). There is no CLI, chat
loop, or API surface today where a human or agent types a question and
gets a routed/algebra-backed answer back.

**Legacy dead-end agents present and risky to rediscover:**
`oracle/agent.py` (GraphOracleAgent) and `oracle/nl_agent.py`
(NaturalLanguageGraphAgent) look like "the agent" — they're the simplest,
most agent-shaped files in the repo — but they bypass oracle_router,
QuerySession, and the Truth Layer entirely: raw LLM-extracted intent
dict → direct oracle call, no AST, no validation, no determinism
guarantee. They are not imported by anything except each other and the
debug harness (confirmed via grep), so they're inert today, but a future
session (mine or otherwise) could easily mistake one of these for the
intended integration point and build on the wrong foundation. Recommend
explicit deprecation marker or deletion once confirmed unused.

**Smallest next step to move the needle on real readiness:** wire one
real entrypoint — even a CLI script — that does:
```python
assessor = Assessor(db_path)
result = assessor.session().run_algebra(
    "some real question",
    views={
        "STRUCTURE": assessor.structure_view(),
        "STABILITY": assessor.stability_view(),
        "INTEGRITY": assessor.integrity_view(),
    },
)
```
and prints the result against a real project DB. That single run proves
the whole stack end-to-end and is the actual gate before "ready to power
a real agent" can be claimed. Everything else (budget tuning, discovery
API unification, SUMMARY/SUBSYSTEM views) is refinement on top of a path
that hasn't been lit up yet.

**DONE 2026-06-16 — see UPDATE note above.** `tools/analysis/ask.py` is
exactly this script (slightly fuller: all 5 views via `Assessor.all_views()`
rather than just STRUCTURE/STABILITY/INTEGRITY), run successfully against
the real project DB. The gate is cleared; remaining items (budget tuning,
discovery API unification) are real refinement work, not readiness blockers.

---------------------------------------------------
ARCHITECTURAL CLARITY APPENDIX
🧭 EXECUTION MODEL UPDATE (NEW — APPEND ONLY)

This section clarifies how the system is now structurally understood without altering existing contracts.

---

## 🧠 LAYER INTERPRETATION CLARIFICATION

The previous "engine vs assessor split" is NOT a rewrite of the system,
it is a **read-boundary separation over the same graph substrate**.

No existing component is removed — only responsibilities are reinterpreted.

---

## 🧩 DBOracle (STRUCTURAL KERNEL — READ ONLY)

This layer is strictly responsible for:

✔ Edge retrieval (caller → callee relationships)
✔ Forward traversal (surface)
✔ Reverse traversal (influence)
✔ Neighbor queries
✔ Graph snapshot assembly

### ❌ Explicitly NOT responsible for:
- semantic interpretation
- ranking or scoring
- subsystem inference
- intent handling
- query orchestration

### 🧷 Important correction (from prior confusion)

SemanticGraphView is **NOT a live component anymore**
→ treat as REMOVED / ASSIMILATED into DBOracle snapshot path

All semantic transformations now occur above this layer.

---

## 🧠 ASSSESSOR (SEMANTIC ORACLE — ACTIVE REASONING LAYER)

Assessor is now the **only consumer of DBOracle for reasoning**

It is responsible for:

✔ Graph interpretation
✔ Hotspot / degree analysis
✔ Subsystem projection
✔ Validation + integrity checks
✔ Responsibility mapping
✔ Snapshot synthesis
✔ Query execution orchestration
✔ System reporting (system_report)

### Key rule:
Assessor is allowed to COMBINE data.
DBOracle is not.

---

## 🧭 ROUTER (INTENT ENGINE — PARTIALLY STABLE)

Router is responsible for:

✔ Intent classification
✔ Seed selection
✔ Expansion policy execution
✔ Query shaping (impact/surface/general)

### ⚠ Current instability:
- expansion boundary enforcement is incomplete
- intent budgets not consistently applied
- forward/reverse weighting still heuristic in places
- implementation-level symbols still leak into expansion

---

## 🌱 DISCOVERY LAYER (SEED AUTHORITY — NEW CRITICAL BOUNDARY)

This is the ONLY valid bootstrap source for queries.

✔ DB-backed symbol enumeration
✔ file/module discovery
✔ engine-independent
✔ used ONLY by router for initial seed sets

### ❌ MUST NOT:
- depend on engine runtime state
- use cached analysis structures
- infer symbols from traversal results

---

## 🧭 QUERYSESSION (IMPLEMENTED — assessor/query_session.py)

This boundary now exists. It represents:

- a single query lifecycle container
- snapshot of:
  - seeds
  - expansion trace
  - intent classification
  - assessor results
  - router decisions

UPDATE 2026-06-16: history is now durable, not just in-memory.
QuerySession.run_query() persists each QuerySessionResult to a
`query_sessions` table via oracle/persist_query_session.py, best-effort
(failures are caught and logged, never break the query contract).

### Purpose:
Make query execution reproducible and inspectable — across runs, not just
within a single process now.

---

## 🧠 IMPORTANT INTERPRETATION SHIFT

System is no longer:

> graph traversal system

It is now:

> intent-conditioned semantic projection over deterministic structural graph

Traversal is NOT BFS/DFS anymore.

It is:
- budgeted
- intent-shaped
- trace-aware
- constrained propagation

---

## ⚠ OPEN PROBLEM (UPDATED 2026-06-16)

oracle_router expansion still requires:

- strict intent budget enforcement
- [x] removal of implementation-level symbol leakage — done via DB-backed
  noise unification (oracle/symbol_noise.py), see PHASE 1 / ROUTING LAYER notes
- consistent forward/reverse weighting per intent type
- deterministic expansion trace normalization

Next dependency in line (unchanged): DB-backed symbol discovery API as the
single unified bootstrap entrypoint (PHASE 2 above).
---------------------------------------------------

## 2026-06-17 - ROLE view wired up (Truth.md Phase 3/4: purpose-of-file gap)

Per Truth.md Phase 3 findings (Row 1/Row 2): "what is the purpose of X" /
"why does X exist" / "what is the role of X" questions had no path to a
real answer. `Assessor.responsibility_map()` already had real, DB-backed,
per-file role classification (ingestion/classification/graph/persistence/
reporting via `engine/responsibility_map.py` ROLE_PATTERNS) but nothing
wired it into the query algebra - same "orphaned primitive" shape as the
SUMMARY/SUBSYSTEM gap closed earlier on 2026-06-16.

Closed by adding ROLE as a 6th Truth Layer view, same fix pattern as
before, no new heuristics:
- `truth/query_plan.py`: `"ROLE": {"files", "totals"}` added to
  `QueryPlan.VALID_METRICS`.
- `truth/views.py`: `RoleView` dataclass + `build_role_view()` - pure
  transform of `responsibility_map()`'s existing output into view shape.
- `assessor/assessor.py`: `Assessor.role_view()` added, wired into
  `all_views()` (now 6 keys: STRUCTURE/STABILITY/INTEGRITY/SUMMARY/
  SUBSYSTEM/ROLE).
- `api/oracle_router.py`: `_detect_intent()` routes purpose/why/role
  phrasing to a new `role_query` intent; `_select_primitives()` and the
  `intent_budget` table in `_route_expand()` both handle it (zero
  traversal budget - ROLE is file-level, not symbol-traversal-dependent).
- `truth/query_compiler.py`: `role_query -> Select("ROLE")` added to the
  rule-based `_INTENT_TO_AST` table, explanation text, and the
  Ollama-facing `_ALGEBRA_SPEC` (VALID VIEWS / VALID METRICS / mapping
  guidance).

New permanent regression coverage:
`tools/analysis/tests/regression/test_role_view_routing.py` (5 tests:
ROLE in `all_views()` with real seeded role data, `Select("ROLE")`
executes via `QueryExecutor`, `_detect_intent()` classifies
purpose/why/role phrasing as `role_query`, `ask()` routes end-to-end to
the ROLE view, `ask()` is deterministic for role questions).
`test_run_algebra_end_to_end.py` updated to expect 6 view keys instead of
5. Full sweep after this work: 5 (new) + 4 (run_algebra_end_to_end) + 6
(oracle_router_persistence_lock) + 32 (truth/tests/test_query_algebra,
via pytest) = 47/47 passing.

**Environment note - recurrence of the silent-truncation bug, plus a new
variant:** during this work the Edit/Write-tool-to-sandbox sync silently
truncated `api/oracle_router.py` not once but twice more, and also
truncated `tests/regression/test_run_algebra_end_to_end.py` and this very
doc - in each case mid-file in a way that stayed syntactically/visually
*valid* (no `SyntaxError`, no obvious corruption), which is the dangerous
variant: `_route_expand()` lost its final `return` statement and so
implicitly returned `None`, breaking `route_query()` downstream with a
confusing `TypeError` far from the real cause; this doc silently dropped
an entire appended section. Caught and fixed via the same `wc -l`/
`ast.parse`-vs-Read-tool diff + full heredoc rewrite workflow already
documented earlier in this file - but notably, a `Write`-tool rewrite (not
just `Edit`) was **also** silently truncated to the exact same byte count
as the prior truncated version of `oracle_router.py`, so the working fix
was specifically a **bash heredoc write/append**, not a re-attempt via the
Windows-side file tools. If this recurs again, don't bother retrying
Write/Edit - go straight to the heredoc.

Also found and fixed a **second, distinct** bug in the same area: a
locked/undeletable stale `.pyc` in `api/__pycache__/oracle_router.cpython-310.pyc`
(`rm` returned "Operation not permitted") whose recorded mtime+size
happened to exactly match an intermediate (pre-fix) saved state of
`oracle_router.py`, so Python's normal cache-invalidation check
considered it valid and silently ran stale bytecode despite the on-disk
`.py` source being correct - `_detect_intent()` kept returning
`general_query` for purpose/why/role questions even after the source fix
landed and `__pycache__` dirs were (apparently) cleared. Diagnosed by
comparing `inspect.getsource()` (correct) against direct `_detect_intent()`
calls (wrong, i.e. running compiled-but-not-matching-source bytecode),
then confirmed via the pyc header (`flags=0`, i.e. timestamp-based
invalidation, not hash-based) showing an exact mtime+size match to the
stale state. Fixed by `touch`-ing the source file to force a new mtime,
which made the existing (locked, undeletable) cache invalid and forced a
recompile. If `_detect_intent`-style behavior ever looks "obviously wrong
despite correct-looking source" again, check this before assuming the
source itself is bad: compare `inspect.getsource(module.func)` against
actually calling `module.func(...)`, and if they disagree, suspect a
stale/locked pyc rather than a code bug.

---------------------------------------------------

## NEXT STEPS (2026-06-17) - pick up here next session

Two independent tracks are open. Neither blocks the other; pick whichever
Bart prioritizes.

**Track A - original Phase 1/2 critical path (unchanged status, not
touched by the 2026-06-17 ROLE work):**
1. Finish PHASE 1 oracle_router expansion boundaries: intent-specific
   traversal budgets exist for surface/impact/reverse/general/role_query
   (see `_route_expand()`'s `intent_budget` dict in `api/oracle_router.py`)
   but forward-vs-reverse weighting calibration and depth-limit tuning
   per intent are still open (see "Next up scratchpad" at the top of this
   file and the ROUTING LAYER / "CURRENT ISSUE" sections above).
2. Then PHASE 2: expose a DB-backed symbol discovery API
   (list_symbols/find_symbols/find_files/find_modules, DBReader-only) as
   the single unified seed-bootstrap entrypoint, replacing any
   engine-origin or caller-supplied seeding.

**Track B - Truth Kernel / Truth.md candidates surfaced by the ROLE-view
work (same "Phase 4: one truth at a time" shape Row 2/ROLE just closed):**
1. Truth.md Phase 3 Row 3 - `drift_signals` is hardcoded `[]` at the
   `build_stability_view()` call site in `assessor.py` (a query against
   it validates and executes cleanly but is silently always empty - the
   most dangerous gap shape, since nothing signals it's missing).
   Populate it from real drift-detection data, or explicitly document why
   it can't be yet.
2. Truth.md Phase 3 Row 4 - `_module()` in `truth/subsystem_view.py`
   assumes dotted module-qualified symbol names; this codebase's actual
   caller format is mostly bare function names, so SUBSYSTEM grouping
   fragments into ~355 single-function "subsystems" instead of real
   architectural groupings. Needs either a better module-inference
   heuristic or a documented caveat on what SUBSYSTEM currently means.
3. Truth Kernel Board.md Tier 2 - "Role classification interpretability"
   and "Subsystem interpretability" both need evaluation against real
   debugging/onboarding tasks, not just correctness checks (which they
   already pass).

Whichever track is picked, the **mandatory file-write verification
procedure in CLAUDE.md** ("File write verification (mandatory)" section)
applies to every edit in this repo - bash-side diff against intended
content, not just a Read-tool glance, given this session's three
truncation incidents plus one fully-phantom Read-tool view.
