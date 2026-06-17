🧭 EXECUTION PATH (ORDERED — DO NOT MIX WITH CHECKBOXES)
Next up scratchpad
--- --- ---
Do NOT expand anything new yet.

DONE 2026-06-17 (later session): oracle_router expansion boundaries
(depth + intent enforcement) - see ROUTING LAYER / "CURRENT ISSUE" and
NEXT STEPS Track A item 1 below for the full calibration writeup.

Next single focus:

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

[x] CURRENT ISSUE — RESOLVED 2026-06-17:
oracle_router expansion now supports explicit traversal control but intent policies are not yet tuned
    → [x] depth limits calibrated 2026-06-17 — surface_query forward_depth
      1→2 (a single hop wasn't a "structural zone"); reverse_query
      reverse_depth 2→1 (direct-usage question, narrower than
      impact_query's transitive reverse_depth=2, which is unchanged).
      general_query (1/1 balanced) and impact_query (reverse-only, depth
      2) were already correctly calibrated and left unchanged. Locked in
      by tests/regression/test_intent_budget_calibration.py (5 tests).
    → [x] forward vs reverse influence balance calibrated 2026-06-17 — see
      above; reverse_query and impact_query are now structurally
      distinguishable instead of sharing one budget.
    → [x] dead "two_hop" key (never read anywhere in _route_expand)
      removed from every intent_budget entry, same shape as the deleted
      _apply_intent_weights stub.
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

## 2026-06-17 (continued) - algebra shape contract audit + fix

Real bug report from Bart's Windows machine: `test_ask_purpose_question_
routes_to_role_view` crashed with `AttributeError: 'list' object has no
attribute 'totals'`. Root cause turned out NOT to be an AI compiler error -
Ollama (reachable on Bart's machine, unreachable in the sandbox, which is
why this only reproduced there) had compiled `Select("ROLE", metric=
"files")` for "what is the purpose of ingest.py", a question naming one
specific file. That's a legitimate, registry-valid, arguably *more
precise* choice than the full view - not an invalid AST. The actual bug
was that the test assumed `QueryResult.data` always had one fixed shape
(`.totals`/`.files` as attributes of a wrapper object) instead of handling
whichever shape the algebra legitimately returned.

This matters beyond the one test: per Bart's framing, the query algebra is
meant to be "an algebra of valid checkboxes that the AI selects... and
narrates in a friendly fashion" - i.e. the AI choosing a different but
equally valid checkbox is the system working as designed, and the
consumer/narration layer's job is to handle whichever valid checkbox came
back, not to demand one specific one. Per his explicit direction ("get
that fixed thoroughly... full mapping... handle all the existing possible
cases"), did a full audit of the Select/Combine shape contract across all
6 views and ~15 metrics, not just a patch for the one failing test:

- **`truth/query_executor.py`**: added `get_field(result, name, default)`
  - the shared, shape-safe way to read a field off a `QueryResult`
  regardless of whether `metric=None` (full view, attribute/key access) or
  `metric=name` (that field's value already, no wrapper). Documented
  inline as the contract every future consumer (tests, `Assessor.ask()`
  callers, any narration layer) should go through instead of assuming a
  fixed shape.
- **SUBSYSTEM shape inconsistency found and fixed**: of the 6 views,
  SUBSYSTEM was the only one whose full-view (`metric=None`) shape was a
  bare dict (`{"subsystems": {...}}`, bracket access) instead of a
  dataclass (attribute access) like the other 5. Added `SubsystemView`
  dataclass (`truth/views.py`) and updated `build_subsystem_view()`
  (`truth/subsystem_view.py`) to return it. This is exactly the kind of
  shape drift that makes "assume one fixed shape" bugs likely - now all 6
  views are uniform.
- **Dead + silently-wrong code removed**: `QuerySemanticsRegistry.
  validate_metric()` (`truth/query_plan.py`) had zero callers anywhere
  (confirmed via grep) and checked `VALID_FILTER_KEYS` instead of
  `QueryPlan.VALID_METRICS` - had it ever been called, it would have
  rejected every legitimate metric for every view. Same "looks like a
  feature, isn't" shape as the previously-deleted `two_hop` key and
  `_apply_intent_weights` stub. The real, actually-enforced metric check
  lives in `QueryPlanner._validate_select`, unchanged.
- **AI-prompt/registry drift risk closed**: `query_compiler.py`'s
  `_ALGEBRA_SPEC` (the text fed to Ollama) used to be a hand-typed copy of
  `QueryPlan.VALID_METRICS`/`QuerySemanticsRegistry.VALID_COMBINES`, with
  nothing stopping the two from silently diverging. `_build_algebra_spec()`
  now generates that text directly from the registry, so the prompt the
  model sees and the rules `QueryPlanner` actually enforces can never
  disagree again. Also tightened the ROLE mapping guidance to note that
  both the full view and `metric="files"` are valid for a one-file
  question, with a preference noted (not a hard rule).
- **Two consumers fixed to handle real shapes, not patched to expect one**:
  `test_role_view_routing.py`'s failing test now reads via `get_field()`
  and asserts on whichever of `files`/`totals` actually came back;
  `test_run_algebra_end_to_end.py`'s SUBSYSTEM assertions switched from
  bracket to attribute access to match the dataclass fix.
- **New permanent regression suite**:
  `tests/regression/test_query_result_shape_contract.py` (4 tests) - the
  actual "full mapping" proof: `get_field()` agrees with direct
  metric-selection for *every* (view, metric) pair in the real registry
  against real DB-backed data (not stubs), `get_field()` returns the
  documented default rather than crashing or guessing when a different
  metric was selected, every view's full-view shape is attribute-accessible
  (locks the SUBSYSTEM fix in so it can't quietly regress to a dict), and
  the AI prompt spec provably contains every view/metric/combine pair the
  registry defines.

Full sweep after this work: 25 regression tests (6 modules) + 32 pytest
(`truth/tests/test_query_algebra.py`) = 57/57 passing, including the
originally-failing test.

**Environment note - the silent-truncation bug hit every single edit made
during this work.** All 5 files touched via the `Edit` tool this session
(`truth/views.py`, `truth/subsystem_view.py`, `truth/query_executor.py`,
`truth/query_plan.py`, `truth/query_compiler.py`) were truncated mid-file
on disk despite the `Read` tool displaying complete, correct content
immediately after each edit - confirmed via `wc -l`/`tail`/`ast.parse`
against the real files in the sandbox, exactly the failure mode CLAUDE.md's
"File write verification (mandatory)" section warns about. All 5 were
recovered via direct bash heredoc rewrite and re-verified (`ast.parse` +
line/byte counts + tail inspection). The two test-file edits
(`test_role_view_routing.py`, then the new
`test_query_result_shape_contract.py`) were written via heredoc from the
start for the same reason. Even this very doc section was truncated mid-
sentence on the first attempted `Edit` and had to be recovered the same
way. This is not a one-off: treat every `Edit`/`Write` call in this repo
as unverified until checked on disk, no exceptions, per CLAUDE.md.


---------------------------------------------------

## 2026-06-17 (later) - determinism test fix: same answer family, not byte-identical AST

Bart ran the full sweep on his real Windows machine (the only place the live
Ollama compiler is actually reachable) and hit a real failure:
`test_ask_role_question_is_deterministic` failed on
`assert first["compiled_ast"] == second["compiled_ast"]` - two separate
`assessor.ask("what is the role of store.py")` calls compiled to two
different (both valid) ASTs.

Root cause is the same class as the original Windows bug this whole
2026-06-17 audit started from, one level up: `Select("ROLE")` and
`Select("ROLE", metric="files")` are BOTH registry-valid compilations for
a one-file question - `query_compiler.py`'s MAPPING GUIDANCE only says
"prefer files when one file is named", a preference, not a hard
constraint - and an LLM compiler running at `temperature=0.0` is not
guaranteed to land on the same choice across two separate calls in
practice (greedy decoding is not bit-reproducible across requests with
llama.cpp/Ollama - floating-point non-associativity in parallel reduction,
a known property of the inference backend, not a bug in this codebase).
The test's old invariant ("same question -> byte-identical AST text") was
wrong for an LLM-backed compiler that can correctly pick from a family of
valid ASTs; "same question -> same answer content" is the correct
invariant, and it's exactly the `get_field()` principle already applied
to `test_ask_purpose_question_routes_to_role_view` earlier this date.

Fixed `tests/regression/test_role_view_routing.py`'s
`test_ask_role_question_is_deterministic`: still asserts
`first["intent"] == second["intent"] == "role_query"`, but now reads both
calls' results via `get_field()` and asserts the underlying role
classification for store.py (persistence) agrees, regardless of which
valid metric the compiler happened to pick each time. No change needed to
`get_field()`, `views.py`, or the compiler itself - this was purely a
test-invariant fix, the same shape as the original bug.

Full sweep after this fix (sandbox, rule-based-fallback path since Ollama
isn't reachable there): 25 regression + 32 pytest = 57/57 passing.
Bart's Windows machine is the one place this fix's real value shows up,
since that's where the live-Ollama nondeterminism actually occurs - it's
on him to re-run there and confirm.

**Environment note (still ongoing):** this single-test edit was *also*
silently truncated on disk by the `Edit` tool (landed mid-comment with no
SyntaxError-free indicator until `ast.parse()` caught it), recovered via
the same bash heredoc + `head`/`tail` reconstruction pattern as every
other edit this session. This doc section itself is being written the
same way for the same reason. The truncation rate this session (effectively
every Edit-tool call, source files and docs alike) is high enough that it
should be treated as a standing environment defect, not noise - see Bart's
question about this, to be addressed as a parallel track.
---------------------------------------------------

## NEXT STEPS (2026-06-17) - pick up here next session

Two independent tracks are open. Neither blocks the other; pick whichever
Bart prioritizes.

**Track A - original Phase 1/2 critical path:**
1. DONE 2026-06-17 (later session) - oracle_router expansion budget
   calibration: surface_query forward_depth 1→2, reverse_query
   reverse_depth 2→1 (now distinguishable from impact_query's transitive
   reverse_depth=2), dead `two_hop` key removed from every
   `intent_budget` entry. See ROUTING LAYER / "CURRENT ISSUE" section
   above for full rationale; locked in by
   `tests/regression/test_intent_budget_calibration.py` (5 tests). Full
   sweep after this work: 52/52 passing (47 prior + 5 new).
   Important caveat surfaced while doing this: `_route_expand()`'s output
   (`expanded_symbols`/trace) currently feeds ONLY the explainability
   surface (`seed_explanation`/`node_reasons`/persisted `query_sessions`
   row) - `QuerySession.run_algebra()` builds its actual answer from
   `Assessor.all_views()` (the full graph snapshot), entirely independent
   of the expansion budget. So this calibration improves trace quality
   today, not algebra answer content - that coupling (if ever wanted) is
   unbuilt, not broken.
2. NEXT: PHASE 2 - expose a DB-backed symbol discovery API
   (list_symbols/find_symbols/find_files/find_modules, DBReader-only) as
   the single unified seed-bootstrap entrypoint, replacing any
   engine-origin or caller-supplied seeding. This is the next item in
   Track A and is unstarted.

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
truncation incidents plus one fully-phantom Read-tool view (now four
truncation incidents as of this entry).
