tools/analysis - TRACKER (consolidated)
=========================================

This file consolidates the status/tracker docs that used to live as
separate files in tools/analysis/docs/. The originals are preserved in
docs/del/, not deleted:

- REFACTOR OPS BOARD.md
- Truth Kernel Board.md
- Truth.md
- todo-done.md

This file is "what's true right now and how we got there" - status
snapshots, open items, a single canonical writeup of recurring environment
defects, and the chronological session log. For architecture/intent (the
why behind the design), see DESIGN.md (also in this folder, consolidated
from AGENT CAPABILITY LAYER v1.md / TRUTH KERNEL v1.md / truth query
algebra.md / contracts + visibility.md / Symbol Classification
Stabilization Plan.md / work flow.md).

Per CLAUDE.md's working agreement: update this file in place as part of
finishing work (checkboxes, dated notes) so Bart can see what changed via
`git diff`, and so a future session doesn't need conversation history to
know where things stand.

Consolidated 2026-06-17. The four original files had substantial overlap
(the same incidents described from different angles - an engine-refactor
angle in REFACTOR OPS BOARD.md, a tier-status angle in Truth Kernel
Board.md, a verification-phase angle in Truth.md, and a flat done-list
angle in todo-done.md). This consolidation keeps one canonical version of
each event, cross-referencing rather than repeating where the originals
repeated each other.

---

## Dashboard - at a glance

**Recently done:** Code-quality/weak-spot audit of the live, wired code
(item 20) - DONE 2026-06-18, two real wiring gaps found and reported (not
yet fixed, see items 22-23); SystemSelfModel documented + tested
(item 19); SUBSYSTEM builtin-noise filter (item 18); INTEGRITY view gap
closed (item 17); SUBSYSTEM path-pollution fix (item 16). Full detail:
section 3 below; full history: HISTORY.md.

**Now / next, in priority order:**
1. [DECISION NEEDED] Two real gaps found by item 20's audit, neither fixed
   yet: embedding-fallback crash risk (item 22) and dead `runtime_bindings`
   wiring / permanently-empty "runtime" bucket (item 23) - fix-now vs.
   track-for-later is Bart's call.
2. Orphaned-module disposition review (item 21) - not started.
3. Truth.md Phase 1 Row 1 remainder + Row 5 (item 2) - next substantive
   feature work; everything else closed from the Phase 3 gap audit.
4. Engine refactor Phases 3-6, the Architecture Split, and the Agent
   Capability Layer build-out (items 3-13) - all open, see section 3 for
   sequencing.

**Standing defects to remember every session** (section 2): silent
file-write truncation and stale `.pyc` caching are real, repeatedly-
confirmed tooling defects in this environment, not project bugs - verify
every write per CLAUDE.md's mandatory procedure.

---

## 1. Current status snapshot

### 1a. Engine refactor phase plan (from REFACTOR OPS BOARD.md)

Goal of Phase 1: make oracle_router deterministic under ontology
constraints. Status as of 2026-06-17:

**PHASE 1 - ENGINE STABILIZATION**
- [x] remove implementation-level symbols from expansion results - DONE
  2026-06-16, builtin + accessor-chain noise filtering unified into
  `oracle/symbol_noise.py`, used at both discovery time and expansion time.
- [x] seed discipline enforcement (seeds only from discovery API) - DONE
  2026-06-17, production seeding confirmed already 100% DB-backed; dead
  `_seed_symbols()` decoy wrapper removed from `api/oracle_router.py`.
- [x] oracle_router expansion boundaries (intent -> traversal budget
  enforcement, forward vs reverse weighting) - DONE 2026-06-17 (later
  session), see ROUTING LAYER below for the calibration detail.

**PHASE 2 - QUERY DISCOVERY SYSTEM**
- [x] DB-backed symbol discovery API - DONE 2026-06-17:
  `list_symbols`/`find_symbols`/`find_files`/`find_modules`/
  `symbol_module_map` implemented in `oracle/db_oracle.py`, all
  DBReader-only (single SELECT against `symbols`/`files`, no
  engine/in-memory fallback).

**PHASE 3 - ASSESSOR AS ORACLE CORE**
- [x] introduce QuerySession (first true oracle object) - implemented in
  `assessor/query_session.py`; history persisted to a `query_sessions`
  table via `oracle/persist_query_session.py` (best-effort, never breaks
  the query contract).
- [ ] move query execution fully into Assessor (route_query becomes
  Assessor-owned, DBOracle becomes pure kernel only) - still open.

**PHASE 4 - ORACLE HARNESS STABILIZATION**
- [ ] DB-only execution mode (no engine dependency in query path,
  deterministic replay support) - still open.

**PHASE 5 - REASONING TRACE EXPOSURE**
- Partially active already: seed_paths, expansion trace, and node
  inclusion reasons all exist in `execution_plan["trace"]`.
- [ ] formalize as first-class API: `expansion_explanation()`,
  `seed_explanation()`, `intent_mapping_trace()` - still open.

**PHASE 6 - WEIGHTED SEMANTIC SCORING**
- [ ] replace heuristic scoring with trace-weighted ranking - still open,
  explicitly "later."

**Detailed layer checklist (TRUTHS LOCKED: SymbolIdentity owns identity;
graph is DB-derived truth, no heuristic writes; invariants are
post-construction only; routing is logically split - symbol_router does
intent + seed discovery, oracle_router does expansion + pruning +
planning, with physical separation complete but some coupling remaining
in expansion strategy; query layer operates only on graph truth.)

IDENTITY LAYER: SymbolIdentity active/stable [x], identity authority
consolidated [x], identity migration complete [x], unify identity factory
entrypoint (single creation path) [ ].

CLASSIFICATION LAYER: routing separated via symbol_router [x],
classification operates on routed domain only [x], unify classification
imports (single source path) [ ], eliminate residual dual routing paths
in tests [ ].

INGESTION: AST extraction stable [x], alias_map normalization consistency
under observation [-], finalize dotted-name policy (canonical identity
preserved in graph, tokenization only for discovery layer, never used as
identity mutation) [ ].

GRAPH: edge persistence schema stable [x], graph deterministic (DB
aligned) [x], invariant validation stable (post-build only) [x], verify
all query consumers are DB-backed only / no in-memory fallback paths
remain anywhere [ ].

ARCHITECTURE SPLIT (all still open): create contracts layer [ ], create
assessor layer [ ], move query stack into assessor [ ], enforce DB-only
boundary [ ], remove engine/query coupling [ ].

QUERY LAYER: context/surface/impact stable [x], cross-run deterministic
behavior confirmed [x], oracle query surface integrated [x]. Remaining
items below were written before the discovery API landed and are now
superseded by Phase 2's completion above, kept here for traceability:
remove engine-owned/caller-supplied seed selection [x, see Phase 1], add
symbol discovery API as unified bootstrap layer [x, see Phase 2], add
ranking refinement layer (heuristic -> trace-informed scoring) [ ], define
query surface API as first-class entrypoint [x, see Phase 2].

ROUTING LAYER: intent detection stable (symbol_router) [x], seed
generation stable [x], oracle_router functional [x]. "CURRENT ISSUE" -
RESOLVED 2026-06-17: depth limits calibrated (`surface_query` forward_depth
1->2; `reverse_query` reverse_depth 2->1, now distinguishable from
`impact_query`'s transitive reverse_depth=2; `general_query` 1/1 balanced
and `impact_query` reverse-only depth 2 were already correct and left
unchanged) - locked in by
`tests/regression/test_intent_budget_calibration.py` (5 tests). Dead
`two_hop` key removed from every `intent_budget` entry. Still open:
[ ] validate intent-specific expansion quality against real usage (this is
the "is it actually useful" evaluation, separate from "is it calibrated
correctly" which is now done).

REASONING LAYER: expansion trace capture implemented [x], expose
expansion reasoning view (node_reasons -> API surface, `_route_expand()`
returns seed_paths/expansion trace/node inclusion reasons in
`execution_plan["trace"]`) [x]. Still open: [ ] answer architectural
questions from graph truth, [ ] expose deterministic reasoning primitives
as named functions (seed selection explanation / expansion justification
trace / intent->primitive mapping trace - the data exists in the trace
dict, just not as named callable primitives yet), [ ] identify structural
influence and dependency zones, [ ] support oracle-style interrogation
queries, [ ] oracle execution feedback loop (query -> refinement signal).

CONTRACTION LAYER: [x] deferred until query fragmentation observed in
real usage (decision, not a gap).

TEST SUITE: invariant regression resolved [x], engine snapshot stable [x],
regression suite added 2026-06-16 (`test_oracle_router_persistence_lock.py`)
[x]. Still open: [ ] project symbol ordering must be DB-deterministic (no
insertion-order reliance anywhere), [ ] minimal oracle CLI smoke test
harness needed, [-] some regressions classified as expected stabilization
noise.

**Notes (clean-state summary, still accurate):** instrumentation is
structurally sufficient; DB remains authoritative truth source; invariants
are post-build validation only; routing split is complete structurally,
still evolving behaviorally; next architectural evolution is expansion
trace -> weighted influence model (Phase 6).

### 1b. Truth Kernel tier status (from Truth Kernel Board.md)

Purpose: deterministic introspection governance layer. Nothing enters
until it's testable, deterministic, and grounded in existing system truth
- the Truth Kernel is not allowed to invent information.

**TIER 0 - query interface hypotheses (AI compiler surface).** Defines how
natural language maps into the query algebra; TRUTH KERNEL v1.md
(DESIGN.md section 2) is the authoritative spec. Promotion rule: must have
executable tests.

**TIER 1 - VERIFIED (fact).** All proven correct via execution:
- [x] Query AST, Query Planner, Query Executor.
- [x] Structure View - wired to real DB data, builtin-filtered.
- [x] Stability View - wired to real contract reports. `drift_signals`
  populated 2026-06-17 (was hardcoded `[]` - the "most dangerous gap
  shape," see chronological log).
- [x] Integrity View - wired to real validation data.
- [x] Summary View, Subsystem View - both re-upgraded 2026-06-16 to real
  DB-backed data with direct test coverage (not the earlier stub-only
  coverage). Subsystem grouping quality fixed 2026-06-17 (was fragmenting
  into ~355 near-singletons on bare/undotted symbol names).
- [x] Role View - added 2026-06-17, wraps `Assessor.responsibility_map()`.
  Single-file filter scoping added same date (later session) after a real
  Windows bug where a one-file question returned the unfiltered full view.
- [x] QueryResult shape contract - closed 2026-06-17: full Select/Combine
  shape audited and locked across all 6 views / ~15 metrics after a real
  Windows-only AttributeError; `get_field()` added as the one correct way
  to read a QueryResult regardless of which valid metric was selected.
- [x] Determinism test invariant - closed 2026-06-17 (later): fixed to
  compare answer content via `get_field()` rather than raw AST text, since
  an LLM compiler at temperature=0.0 can validly pick between more than
  one registry-correct AST for the same question.

Criteria: passes the real regression suite (not the deleted print-only
`truth/test_harness.py`), no structural contradictions, deterministic
outputs.

**TIER 2 - USEFUL (signal quality).** Correct but evaluated for practical
value:
- [x] Hotspot ranking quality - resolved, builtins excluded from the
  degree-count ranking via the DB-authoritative builtin set.
- [x] Stability signal usefulness - EVALUATED 2026-06-17: verdict NOT YET
  USEFUL. Real signal, but its only contract source (null caller/callee in
  persisted symbol_references) is a raw-ingestion-corruption check, not an
  architectural stability check - trivially clean (142 stable / 0 unstable
  / 0 drift_signals) against the real 157-file project DB. Full findings in
  chronological log.
- [x] Integrity signal usefulness - EVALUATED 2026-06-17: verdict NOT YET
  USEFUL, and narrower than it should be - `Assessor.validation_summary()`
  bypasses the already-built `SystemValidator` class entirely (reimplements
  2 of its 4 checks inline, skips its `_validate_contracts` escalation
  path), and `IntegrityView.db_mismatches` is a permanently hardcoded `[]`
  ("no DB comparison anymore") - same orphaned-looks-like-a-signal shape as
  the old drift_signals bug, just never flagged. Full findings in
  chronological log; see also new open items 16-18 below.
- [x] Subsystem interpretability - EVALUATED 2026-06-17: verdict MIXED. The
  Row 4 fix holds - grouping now tracks real top-level package directories,
  not near-singletons. But (a) `_file_path_to_module()` (db_oracle.py)
  doesn't trim to a project-relative path the way the codebase's two
  existing `module_name_from_file_path()` utilities do, so subsystem
  identity strings are polluted with the full absolute filesystem path,
  and (b) the per-subsystem dependency list isn't builtin/stdlib-filtered
  the way hotspot ranking explicitly is, diluting the "what does this
  depend on" signal with noise (`len`, `str`, `RuntimeError`, ...). Full
  findings in chronological log.
- [x] Role classification interpretability - EVALUATED 2026-06-17: verdict
  NOT YET RELIABLE. The keyword-substring-on-callee-name heuristic produces
  false positives whenever a file merely calls/references another
  subsystem's function or type by name - confirmed against real data:
  `db_oracle.py` (a persistence/query file) gets flagged "graph"/
  "classification"/"reporting" because it references `GraphBundle`/
  `GraphEdge`, `embed_symbol`, and `print`. Orchestrator files (e.g.
  `run_engine.py`) correctly get every role, which is true but
  undifferentiating. Full findings in chronological log.

**TIER 3 - AUTHORITATIVE (system replacement).** All open: [ ] Assessor
fully uses Truth Layer exclusively, [ ] Oracle fully routed through Truth
Layer, [ ] Engine introspection migrated, [ ] legacy dual-path removed.

**TIER 4 - KERNEL (closed world complete).** Future state, all open: [ ]
all introspection flows through the Truth Query Algebra, [ ] no alternate
query systems exist, [ ] no ad-hoc graph inspection paths remain, [ ]
query language is frozen (no expansion allowed).

**Core principle (unchanged):** AI interprets the request, maps it to the
query algebra (only allowed primitives), executes deterministically via
the executor, then narrates the result (no invention) based on intent -
either a summarized human response or direct AI context. The Truth Kernel
itself stays deterministic throughout.

### 1c. Truth verification phase status (from Truth.md)

Truth.md's own Phase 0-6 plan for proving the Truth Layer is real, distinct
from the engine-refactor Phase 1-6 in section 1a above (same number range,
different track - don't conflate them).

- **Phase 0 (Freeze - verification only, no architecture/router/oracle/
  assessor changes): COMPLETE.**
- **Phase 1 (prove the Truth Layer is a real subsystem, not dead code):
  COMPLETE, verdict MET** as of 2026-06-16. All 5 (now 6) views produce
  real output from real DB-backed data; the assembled pipeline (NL ->
  router -> compiler -> AST -> executor -> views) has run end-to-end
  against both a seeded test DB and the real project DB, with permanent
  regression coverage. Full findings in the chronological log below.
- **Phase 2 (compare router path vs Truth Layer path for signal quality/
  noise/determinism/explainability): not started.** Can start whenever
  prioritized - nothing blocks it.
- **Phase 3 (identify missing truths via evidence, not guesses): done as
  a one-time audit, 2026-06-16/17.** Found 5 concrete gaps ("Rows 1-5"),
  see chronological log for the full evidence-based writeup. Pattern: two
  failure shapes, not five unrelated ones - "never captured" (Rows 1, 5)
  needing new ingestion, vs. "captured/computable but not wired or wired
  wrong" (Rows 2, 3, 4) needing only connection work.
- **Phase 4 (add one truth at a time, per missing capability): 3 of 4
  wired-but-broken rows closed.** Row 2 (role/purpose questions) closed
  2026-06-17 via the ROLE view. Row 3 (drift_signals hardcoded `[]`)
  closed 2026-06-17 (later session). Row 4 (subsystem fragmentation)
  closed 2026-06-17 (later still). Row 1's non-Row-2 remainder and Row 5
  (no intent/description field on `MutationEvent`) remain open - both are
  "never captured" and need new ingestion, not just wiring.
- **Phase 5 (determine if the query algebra needs expansion, based on
  repeated question patterns): not started**, implicitly answered "no
  expansion needed yet" by Phase 4's experience so far - every gap closed
  was a wiring fix within the existing AST shape, not a new primitive.
- **Phase 6 (AI compiler, only after Views/Planner/Executor are stable and
  questions are understood): live, earlier than the original plan
  expected.** The Ollama-backed compiler (`truth/query_compiler.py`) was
  wired in during the 2026-06-16 morning session (see chronological log)
  and is in active use, with the rule-based table as fallback.

---

## 2. Standing environment defects (canonical reference)

These are real, repeatedly-confirmed defects in this session's file-write
tooling - not project bugs. CLAUDE.md's "File write verification
(mandatory)" section is the binding procedure. Full incident-by-incident
detail (27 silent-truncation incidents, 3 stale-pyc variants) was moved to
HISTORY.md section A 2026-06-18 - this section is the operational summary
every session actually needs before touching a file in this repo.

### 2a. Silent file-truncation bug

Edit and full-file Write calls in this repo have repeatedly produced files
on disk that are silently truncated, padded with trailing NUL bytes, or
left byte-for-byte unchanged - despite a reported success and a correct-
looking in-context Read. Severity ranges from syntactically obvious
(caught by `ast.parse()`) to syntactically invisible (a function or whole
block silently disappears at a clean boundary, no error raised).
Retrying via a different tool is not a fix - confirmed reproducing the
identical truncated byte count across tools at least once.

**The only confirmed-reliable fix:** a direct bash heredoc rewrite (or
heredoc append onto an already-verified-correct prefix), followed by a
full bash-side diff against the intended content string. Zero diff output
is the only authoritative confirmation - byte/line counts and tail
snippets are a useful first pass but not sufficient alone. Full procedure
is in CLAUDE.md's "File write verification (mandatory)" section.

**28 confirmed occurrences so far** across this engagement. This file
(TRACKER.md) is the single most truncation-prone file encountered (5+
incidents) - treat any edit to it as elevated-risk and always run the full
diff, never a byte-count shortcut. Full incident log: HISTORY.md section A.

### 2b. Stale/locked `.pyc` cache bug

Three confirmed variants: a locked/undeletable stale `.pyc` whose
mtime+size happens to match an intermediate source save and so passes
Python's normal cache-validity check; the same thing but where even
`rm -rf __pycache__` reports clean success while the file silently
remains; and a case where deletion succeeds but trusting it without
re-verification still misses the window. All three look the same at
runtime: `inspect.getsource()` shows correct code but the live function
object's actual behavior (or `dis.dis()` output) reflects the old version.

**Takeaway:** if `inspect.getsource()` and `dis.dis()` on the same live
function object ever disagree, or runtime behavior contradicts visibly-
correct source, suspect a stale `.pyc` before assuming the source is
wrong - `touch <source.py>` to force a recompile, since a `__pycache__`
deletion isn't always trustworthy on this mount even when it reports
success. Full variant detail: HISTORY.md section A.

---

## 3. Open items / next steps

In rough priority order, deduplicated across all four original source
files. Closed items below are trimmed to what shipped + proof; full
writeups for each live in HISTORY.md section B.

1. **Phase 2 evaluation work (Truth Kernel Board Tier 2): DONE 2026-06-17.**
   Evaluated Stability/Integrity/Subsystem/Role view usefulness against a
   real project-corpus engine run (157 files, 631 symbols, 2127 refs);
   verdict mixed-to-negative but not blocking - see section 1b's Tier 2
   block. Produced findings 16-18 below. Full writeup: HISTORY.md section B.
2. **Truth.md Phase 1 Row 1 remainder + Row 5:** genuinely never-captured
   data (no intent/description field on `MutationEvent`; no general
   "why/intent" capture at ingestion time). Requires new ingestion, not
   just wiring - bigger lift than anything closed so far.
3. **Engine refactor Phase 3 remainder:** move query execution fully into
   Assessor (route_query becomes Assessor-owned, DBOracle becomes pure
   kernel only, no semantic interpretation in the DB layer).
4. **Engine refactor Phase 4:** DB-only execution mode (no engine
   dependency in the query path, deterministic replay support).
5. **Engine refactor Phase 5:** formalize the existing trace data as
   first-class named API functions (`expansion_explanation()`,
   `seed_explanation()`, `intent_mapping_trace()`) - the underlying data
   already exists in `execution_plan["trace"]`.
6. **Engine refactor Phase 6 (later, explicitly deferred):** replace
   heuristic pruning/scoring with trace-weighted ranking derived from
   expansion provenance.
7. **ARCHITECTURE SPLIT (all open):** create a contracts layer, create an
   assessor layer, move the query stack into assessor, enforce a DB-only
   boundary, remove engine/query coupling.
8. **Ranking refinement layer:** upgrade pruning from heuristic scoring to
   trace-informed scoring (overlaps with Phase 6 above).
9. **Validate intent-specific expansion quality against real usage** -
   the budgets are now calibrated and locked by regression tests, but
   whether `impact_query`/`surface_query`/`general_query` actually produce
   the *right* zones for real questions hasn't been evaluated end to end.
10. **Reasoning layer remainder:** answer architectural questions from
    graph truth directly; identify structural influence/dependency zones;
    support oracle-style interrogation queries; an oracle execution
    feedback loop (query -> refinement signal).
11. **Test suite hygiene:** project symbol ordering must be DB-
    deterministic (no insertion-order reliance anywhere); a minimal oracle
    CLI smoke test harness; alias_map normalization consistency (currently
    "under observation," not yet confirmed stable); unify the identity
    factory entrypoint to a single creation path; unify classification
    imports to a single source path; eliminate residual dual routing
    paths in tests.
12. **Truth Kernel Tier 3/4 (system replacement / closed-world complete):**
    all items open and explicitly future-state - Assessor fully on the
    Truth Layer exclusively, Oracle fully routed through it, engine
    introspection migrated, legacy dual-path removed, no ad-hoc graph
    inspection paths remaining anywhere, query language frozen.
13. **Agent Capability Layer build order (see DESIGN.md section 3 for the
    why - this is sequencing only). Status: not started, zero items below
    have any code behind them as of 2026-06-17.**
    1. [ ] Widen ingestion scope to world/ + engine/ + resolver/ +
       dungeon_neo/. No new code - run existing ingestion over more files,
       plus whatever path-config change that requires. Verify with a
       regression test asserting a known real symbol (e.g.
       `generate_location_from_potential`) shows up in `graph_edges` after
       ingestion.
    2. [ ] Audit `impact_query`'s actual semantics against real data: full
       transitive closure, or only what the explainability trace's depth
       budget surfaces? Write this down as fact either way before building
       on it.
    3. [ ] If a gap is found in #2, fix it or add a separate full-closure
       ripple query (both directions) as a new, explicit capability - not
       silently repurposing the explainability trace for a job it wasn't
       built for.
    4. [ ] Build the task.md generator off the ripple query from #2/#3.
       Markdown, plain checklist format, matching this doc's voice.
    5. [ ] Build the "re-reference a task.md" path: read file -> extract
       the originating query -> re-run against current DB -> diff ->
       report.
14. **Truth Kernel Board Tier 0:** AI compiler surface hypotheses -
    TRUTH KERNEL v1.md's view-legality and Combine-legality lists are
    stale relative to the current 6-view reality (they only mention 5
    views and don't include ROLE in the allowed Combine pairs) - worth a
    pass to update DESIGN.md's spec language or explicitly note the gap
    there if ROLE participation in Combine is ever needed.
15. **Semantic Identity Reconstruction: status corrected from "Phase 3 not
    started" to "Phase 3 deliberately abandoned" - no action item.** The
    shadow/trace infrastructure (`route_symbol_shadow()`, `TraceCollector`,
    CP0-CP4) was built and is real and live; the planned replacement of the
    legacy router was tried and explicitly reversed per the code's own
    comments. Full writeup: DESIGN.md section 4 ("shadow/observability
    layer") and HISTORY.md section B.
16. **SUBSYSTEM identity strings polluted by absolute file paths: DONE
    2026-06-17/18.** Fixed via a new persisted `project_root` (new
    `project_meta` table + `set_project_root()`/`get_project_root()`) so
    `_file_path_to_module()` trims paths correctly. Test coverage:
    `tests/regression/test_subsystem_path_pollution_fix.py` (7 tests); full
    suite 85/85 after. Full writeup: HISTORY.md section B.
17. **INTEGRITY view thinner than the codebase's own validation logic:
    DONE 2026-06-18.** `validation_summary()` now calls the real
    `SystemValidator` checks instead of a partial inline reimplementation;
    `IntegrityView.db_mismatches` now reflects a real `graph_edges`/
    `symbol_references` count-disagreement signal instead of a hardcoded
    `[]`. Test coverage: `tests/regression/test_integrity_view_wiring.py`
    (6 tests); full suite 96/96 after. Full writeup: HISTORY.md section B.
18. **SUBSYSTEM dependency lists weren't builtin/stdlib-filtered: DONE
    2026-06-17/18.** `build_subsystem_view()` now takes the same DB-
    authoritative `builtin_symbols` set hotspot ranking already uses and
    excludes builtin edges before module resolution. Test coverage:
    `tests/regression/test_subsystem_builtin_noise_filter.py` (5 tests).
    Full writeup: HISTORY.md section B.
19. **`SystemSelfModel`/`SystemSelfModelBuilder` undocumented and untested:
    DONE 2026-06-18.** Real, production-wired Tier 2 component
    (`Assessor.self_model()`, `QuerySession` results) had zero docs/tests.
    Fixed: DESIGN.md section 6 added, stale comment references corrected,
    `tests/regression/test_system_self_model.py` added (8 tests). Full
    writeup: HISTORY.md section B.
20. **[HIGH PRIORITY] Code-quality / weak-spot audit of the live, wired
    code: DONE 2026-06-18.** Mapped the real live surface via static
    import-reachability from both real entry points (`ask.py` for
    queries, `engine/run_engine.py` for ingestion): 50 modules reachable,
    64 not - the unreached set matches item 21's orphaned-module candidate
    list, cross-validating that split. Of the 50 live modules, found no
    bare/swallowed excepts, no TODO/FIXME/HACK debt, and the project's
    deliberate non-fatal `except Exception` sites (schema check, session
    persistence, system_self_model gap recording) are all legitimate,
    well-commented "record the gap, don't invent" patterns, not bugs.
    Found two real gaps, both confirmed against live code and/or the real
    project DB, neither fixed yet (audit scope, not fix scope) - recorded
    as items 22 and 23 below. Full writeup: HISTORY.md section B.
21. **Orphaned-module disposition review (hole vs. dead).** Evaluate
    `resolution/symbol_origin_resolver.py`, `inspection/explain_file.py`,
    `utilities/reachable_print_trace.py`, `context/build_context_packet.py`,
    the `contracts/` cluster (`contract_validator.py`,
    `contract_lifecycle.py`, `contract_health_aggregator.py`,
    `contract_types.py`, plus 3 empty stub files), `api/get_llm_context.py`,
    `api/query_entry.py`, the empty `orchestration/` directory, and
    `specification/tool_system_contract.json` - each through the "missing
    capability that should be wired" vs. "genuinely dead, safe to remove"
    lens, per this project's standing principle of never assuming dead from
    surface signals alone. Deferred, not yet started; report findings to
    Bart before any integrate/dispose/delete action.
22. **Embedding-fallback crash risk in seed discovery (found by item 20's
    audit, not yet fixed).** `oracle/db_oracle.py`'s
    `discover_seed_symbols_semantic()`/`discover_seed_symbols()` only
    catch `ImportError` around importing `sentence-transformers`/
    `embedding_model` - the docstring promises "falls back to token-based
    if the sentence-transformers package is not installed," but a load-
    time failure *after* a successful import (model download/network
    failure, corrupted HuggingFace cache, etc., raised inside
    `embedding_model.get_model()`) happens outside that `try` block and is
    never caught. This sits on the live path for every single `ask.py`
    query - `assessor/query_session.py`'s `run_query()` passes
    `self.oracle.discover_seed_symbols` straight into `route_query()` with
    no surrounding try/except. `sentence-transformers` is confirmed
    actively installed and in use on Bart's real machine (see
    `embedding_model.py`'s own torch-warning-silencing comment,
    2026-06-17) - so a model-load failure there would crash every query
    instead of degrading gracefully as documented. Needs either a broader
    `except Exception` around the embedding path with a logged fallback,
    or a deliberate decision that this risk is acceptable as-is.
23. **Dead `runtime_bindings` wiring - "runtime" bucket is permanently
    empty in production (found by item 20's audit, not yet fixed).** The
    per-file `_extract_runtime_bindings()` (`ingestion/parse_ast.py`) and
    `resolve_runtime_symbol()` (`graph/runtime_resolution.py`) are real,
    correct, and individually unit-tested - but only by tests that
    construct `SymbolEnvironment`/`FileAnalysis` fixtures directly with a
    hand-built non-empty `runtime_bindings` dict, bypassing the real
    pipeline. In the real pipeline, `ingestion/scan_project_files.py` line
    192 hardcodes `runtime_bindings = {}  # still placeholder for now` and
    passes that empty dict straight through `analyze_files()` into every
    `parse_ast()` call, which stores it unchanged onto
    `FileAnalysis.runtime_bindings`. `_extract_runtime_bindings()` *is*
    called for real inside `_extract_symbol_references()` - but only into
    its own separately-scoped local variable, used solely to resolve raw
    call names for that pass's own `SymbolReference` construction; the
    result is never propagated back onto `FileAnalysis.runtime_bindings`.
    Production classification (`classification/classify_references.py`'s
    `route_symbol(runtime_bindings=analysis.runtime_bindings, ...)`, the
    actual bucket-assignment call for every symbol reference) therefore
    always receives `{}`. Confirmed against the real project DB:
    `SELECT bucket, COUNT(*) FROM symbol_references GROUP BY bucket`
    returns only `builtin`/`project`/`stdlib`/`external` - zero rows with
    `bucket = 'runtime'` - despite "runtime" being a documented bucket in
    `classify_references.py`'s own contract comment. Same bug shape as the
    previously-fixed drift_signals/db_mismatches gaps (item 17): a real,
    tested, correct computation exists, but the wiring that would surface
    it in production output was never connected - the difference here is
    that the unit tests construct fixtures by calling the internal helper
    directly, so test-green gave no signal the production path was inert.
    Needs a decision on whether `parse_ast()` should call
    `_extract_runtime_bindings()` itself and thread the result onto
    `FileAnalysis.runtime_bindings`, replacing the
    `scan_project_files.py` placeholder.

---

## 4. Chronological session log

Moved to HISTORY.md (section B) as part of the 2026-06-18 TRACKER/HISTORY
split - full dated session-by-session record, verbatim, nothing dropped.
