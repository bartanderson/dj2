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

**Recently done:** Orphaned-module disposition review (section 3 item 12)
- investigated and reported 2026-06-19, no integrate/dispose/delete action
taken (per the item's own gate: report findings to Bart before any
disposal). Checked actual wiring (import/call-site grep across the whole
tree), not just file contents in isolation, for all 9 originally-listed
candidates plus the empty `orchestration/` directory and the
`specification/tool_system_contract.json` spec file. Full per-item findings
and disposition recommendations: section 3 item 12 below. Headline results:
most candidates are confirmed genuinely dead (zero callers anywhere); one
(`inspection/explain_file.py`) is a complete, ready-to-use capability that
nothing currently calls - a real "hole," not dead weight; one
(`api/get_llm_context.py`) isn't orphaned at all despite zero in-repo
callers, since it's the documented external integration point for a
consumer (the future agent) that doesn't exist yet; and `contract_types.py`
+ `specification/tool_system_contract.json` + the empty `orchestration/`
directory turn out to be three pieces of one coherent, unfinished feature
rather than independent dead files. Also surfaced one finding outside the
original list, same directory: `contracts/load_contract.py`'s consumers
load a *different* `tool_system_contract.json` (the one physically in
`contracts/`, schema_version 3) and would `KeyError` immediately if ever
called, since that file has no `domains` key - dormant, not yet broken in
practice, only because nothing calls it.

Before that: Ingestion run 2026-06-19 against all three candidate
corpora from section 3 item 1: `tools.old/` (73 files, 2764 graph_edges),
`external_corpora/flask/src` (24 files, 800 graph_edges),
`external_corpora/sqlalchemy/lib` (255 files, 20769 graph_edges) - row
counts confirmed by direct query against each resulting DB. Permanent
regression proof added:
`tests/regression/test_external_corpus_ingestion.py` (2 new tests,
asserting a known real symbol from `tools.old/` appears correctly in
`graph_edges`); full suite now 82/82. New standing environment defect found
and worked around during this run - see section 2d. Before that:
`external_corpora/flask` and `external_corpora/sqlalchemy`
.git directories repaired 2026-06-19 - both had silently kept the empty
clone-skeleton `.git` (no objects, no config) instead of the real one after
last session's manual Windows rename/move/delete cleanup, root-caused to
PowerShell wildcard moves skipping hidden dot-folders; real `.git` (with
full pack + history) recovered from the still-present sandbox-local clones
at `/tmp/ext_clone/` and swapped in - see section 2c and section 3 item 1.
Before that: Embedding-fallback crash risk in seed discovery (old
item 22) and dead `runtime_bindings` wiring (old item 23) - both DONE
2026-06-18, fixed and regression-tested (6 new tests; 80/80 full suite
after); see section 3 items 13-14 for proof. Section 3 reordered/merged
same date: items 3+4+7, 9+13 step 2, and 6+8 consolidated to remove
duplication while preserving each source's nuance; closed items 1/15-20
removed from the open numbered list (nothing deleted - full writeups
remain in HISTORY.md section B). Before that: code-quality/weak-spot
audit of the live, wired code (old item 20) - DONE 2026-06-18, found the
two gaps just closed above; SystemSelfModel documented + tested (old item
19); SUBSYSTEM builtin-noise filter (old item 18); INTEGRITY view gap
closed (old item 17); SUBSYSTEM path-pollution fix (old item 16). Full
history: HISTORY.md.

**Now / next, in priority order:**
1. [NEW] Game-code corpora (`world/`/`engine/`/`resolver/`/`dungeon_neo/`)
   ingestion - decided 2026-06-19 to sequence this **ahead of** Row 1/Row 5
   below (was previously unsequenced, listed alongside item 3). Reasoning:
   Row 5 needs to design a new ingestion-time "why was this mutation made"
   capture mechanism, and that design should be informed by what mutation
   patterns actually look like in the real target domain (the game's own
   code), not guessed from the self-corpus or the two off-domain
   generalization corpora (Flask/SQLAlchemy) already ingested. Mechanically
   cheap to run - same `EngineRunner().run(...)` headless pattern already
   used for the three corpora done so far, same regression-test bar (a
   known real symbol resolves correctly in `graph_edges` post-ingestion).
2. Truth.md Phase 1 Row 1 remainder + Row 5 (section 3 item 2) - next
   substantive feature work; everything else closed from the Phase 3 gap
   audit. Sequenced after item 1 above, not before, per the reasoning there.
3. Orphaned-module disposition review (section 3 item 12) - investigated
   and reported 2026-06-19 (see "Recently done" above and section 3 item 12
   for full findings). No further open work here unless/until Bart makes a
   per-item disposition call.
4. Engine/Assessor boundary completion, the Architecture Split, the
   query-expansion/impact_query semantics audit, and the Agent Capability
   Layer build-out (section 3 items 3-11) - all open, see section 3 for
   full detail and sequencing notes.

**Standing defects to remember every session** (section 2): stale `.pyc`
caching is a confirmed tooling defect on this environment - if runtime
behavior contradicts visible source, suspect a stale cache before assuming
the source is wrong.

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

These were originally documented as Cowork sandbox defects (FUSE/virtiofs
file-bridge issues). The file-write truncation bugs (2a) and delete-path
permission bugs (2c) were confirmed to be Cowork-specific and are no longer
applicable when running Claude Code directly on Windows. Full incident
history: HISTORY.md section A.

### 2a. Stale/locked `.pyc` cache bug

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

### 2b. `sqlite3.OperationalError: disk I/O error` on new DB writes

New 2026-06-19, found while ingesting the three corpora in section 3 item
1. Any **new** sqlite DB file written to the dj2 mount hits
`disk I/O error` on the first write (table creation), even though reads
and writes against an *existing* DB on the same mount work fine.

**Confirmed fix:** run `PRAGMA journal_mode=MEMORY` immediately after
`sqlite3.connect()`, before any other statement. Sqlite's default
rollback-journal mode needs to create a `-journal` sidecar file
alongside the main `.db` on first write; the mount's I/O layer chokes on
that specific operation. Forcing the journal to live in memory instead
avoids it entirely.

**Caveat:** a stale `-journal`/`-wal`/`-shm` sidecar left over from an
earlier failed attempt (i.e. before this fix was applied) can re-trigger
the same error on a fresh connect, because sqlite attempts rollback
recovery against the orphaned journal before your `PRAGMA` call ever
runs. If this error recurs even with the pragma in place, check for and
clear sidecar files for that exact DB path first.

---

## 3. Open items / next steps

Closed/no-action items previously numbered 1 and 15-20 have been removed
from this list (2026-06-18 cleanup) - nothing deleted, see the Dashboard
above for the at-a-glance "recently done" line and HISTORY.md section B
for full writeups. Items 3+4+7, 9+13 (step 2), and 6+8 below have been
merged from the prior numbering to remove duplication while preserving
every source document's nuance - see each merged item's body for the
distinct angles folded in.

1. **[TOP PRIORITY, NEW 2026-06-18] Evaluate widening the ingestion test
   corpus.** The analysis tool has so far only ever ingested itself (157
   files, its own self-corpus) plus regression fixtures - DESIGN.md
   section 3 flags this explicitly as an open assumption: the reasoning
   layer is "proven, but only proven on one corpus," unverified on a
   differently-shaped codebase. Candidates to evaluate as additional test
   cases, each exercising different capabilities:
   - The game's own source: `world/`, `engine/`, `resolver/`,
     `dungeon_neo/` - real target-domain code, generalizes old item 13
     step 1 ("widen ingestion scope") from a fixed first-step into part
     of this broader evaluation.
   - `tools.old/` - already in-repo, untouched by the self-analysis run
     so far, a reasonable next corpus before the game code.
   - Possibly downloadable open-source projects, for capabilities (or
     codebase shapes/sizes) the in-repo corpora don't exercise.
   Sequencing across these is intentionally **not** fixed - Bart was
   explicit that this is "a listing... not an ordering," and wants
   proposed impacts of alternative orderings rather than one imposed
   priority. Items 13 and 14 below (old items 22/23) were a stated
   prerequisite before widening scope, since both bugs could otherwise
   produce misleading or crashing results on a differently-shaped corpus
   - both are now fixed, so this item is unblocked. Verify whichever
   corpus is chosen first with a regression test asserting a known real
   symbol from that corpus appears correctly in `graph_edges` after
   ingestion (the same bar old item 13 step 1 set).

   **Status update 2026-06-19 (later, this session): ingestion actually
   run against all three non-game-code candidates, all three landed.**
   Used `EngineRunner().run(corpus=..., project_prefixes=[], repo_root=...,
   connection=...)` directly (the headless invocation pattern from
   `tests/core/test_engine_smoke.py` - `run_engine.py`'s own `__main__` is
   GUI-only via tkinter and unusable here). Row counts confirmed by direct
   query against each resulting DB:
   - `tools.old/`: 73 files, 2764 `graph_edges`.
   - `external_corpora/flask/src`: 24 files, 800 `graph_edges`.
   - `external_corpora/sqlalchemy/lib`: 255 files, 20769 `graph_edges`.

   Verification bar this item set ("a regression test asserting a known
   real symbol from that corpus appears correctly in `graph_edges`") is
   met: `tests/regression/test_external_corpus_ingestion.py`, new this
   session, 2 tests - one asserting `tools.old/` ingestion produces a
   non-empty `graph_edges` table at all, one asserting a specific known
   real symbol from that corpus resolves correctly as a node in it. Full
   regression suite: 82/82 after (was 80/80).

   Hit two new environment issues doing this, both now logged as standing
   defects rather than one-offs: a `disk I/O error` on any brand-new
   sqlite DB write to this mount (section 2d - fixed with
   `PRAGMA journal_mode=MEMORY`), and the delete-path "Operation not
   permitted" bug (2c) turning out not to be scoped to
   `external_corpora/` after all - reproduced on new files anywhere in
   the mount, worked around the same way (`mv` aside).

   Remaining candidate from this item's original list: the game's own
   source (`world/`/`engine/`/`resolver/`/`dungeon_neo/`) - **decided
   2026-06-19 (later session) to do this next, ahead of item 2 below** -
   see Dashboard "Now / next" item 1 for the reasoning (Row 5's new
   ingestion-capture design should be informed by real target-domain
   mutation shapes, not guessed). Not yet started. Cleanup from last
   session's run is fully resolved as of 2026-06-19 (later):
   `_sandbox_cleanup_needed/` deleted by Bart, and the two
   `.git_broken_skeleton` dirs are confirmed gone on his actual machine -
   their lingering visibility to `stat`/`rm` inside the sandbox is a stale
   virtiofs mount-cache artifact, not a real file (Cowork sandbox defect,
   now resolved). No outstanding Windows-side action remains.
2. **Truth.md Phase 1 Row 1 remainder + Row 5:** genuinely never-captured
   data (no intent/description field on `MutationEvent`; no general
   "why/intent" capture at ingestion time). Requires new ingestion, not
   just wiring - bigger lift than anything closed so far. **Sequenced
   after item 1's game-code ingestion (decided 2026-06-19) - design this
   against real target-domain mutation shapes, not the self-corpus alone.**
3. **Engine/Assessor boundary completion** (merges old items 3, 4, and 7
   - three angles on the same end-state, kept together since they're
   sequential pieces of one boundary, not independent work):
   - Move query execution fully into Assessor: `route_query` becomes
     Assessor-owned, `DBOracle` becomes pure kernel only, no semantic
     interpretation in the DB layer (old Phase 3 remainder).
   - DB-only execution mode: no engine dependency in the query path,
     deterministic replay support (old Phase 4).
   - Architecture split groundwork this depends on: create a contracts
     layer, create an assessor layer, move the query stack into
     assessor, enforce the DB-only boundary, remove engine/query
     coupling (old item 7, all still open).
4. **Engine refactor Phase 5:** formalize the existing trace data as
   first-class named API functions (`expansion_explanation()`,
   `seed_explanation()`, `intent_mapping_trace()`) - the underlying data
   already exists in `execution_plan["trace"]`.
5. **Trace-weighted ranking (explicitly deferred - merges old items 6 and
   8, same upgrade described from two angles):** replace heuristic
   pruning/scoring with trace-weighted ranking derived from expansion
   provenance (old Phase 6); equivalently, upgrade the ranking refinement
   layer from heuristic scoring to trace-informed scoring (old item 8).
   "Later" per the original Phase 6 note - revisit once query-expansion
   quality (item 6 below) has been validated against real usage, since
   that validation will inform what "trace-informed" should actually
   weight.
6. **Query-expansion validation / `impact_query` semantics audit (merges
   old item 9 and old item 13 step 2 - same open question, raised from
   the usage-evaluation angle and the build-order angle):**
   - Validate intent-specific expansion quality against real usage - the
     budgets are now calibrated and locked by regression tests, but
     whether `impact_query`/`surface_query`/`general_query` actually
     produce the *right* zones for real questions hasn't been evaluated
     end-to-end (old item 9).
   - Audit `impact_query`'s actual semantics against real data
     specifically: full transitive closure, or only what the
     explainability trace's depth budget surfaces? DESIGN.md section 3
     calls for this to be audited against real data before the task.md
     mechanism is built on top of it, not after (old item 13 step 2). If
     a gap is found, fix it or add a separate full-closure ripple query
     (both directions) as a new, explicit capability - not silently
     repurposing the explainability trace for a job it wasn't built for
     (old item 13 step 3, kept here since it's the direct contingency on
     this audit's outcome).
7. **Reasoning layer remainder:** answer architectural questions from
   graph truth directly; identify structural influence/dependency zones;
   support oracle-style interrogation queries; an oracle execution
   feedback loop (query -> refinement signal).
8. **Test suite hygiene:** project symbol ordering must be DB-
   deterministic (no insertion-order reliance anywhere); a minimal oracle
   CLI smoke test harness; alias_map normalization consistency (currently
   "under observation," not yet confirmed stable); unify the identity
   factory entrypoint to a single creation path; unify classification
   imports to a single source path; eliminate residual dual routing
   paths in tests.
9. **Truth Kernel Tier 3/4 (system replacement / closed-world complete):**
   all items open and explicitly future-state - Assessor fully on the
   Truth Layer exclusively, Oracle fully routed through it, engine
   introspection migrated, legacy dual-path removed, no ad-hoc graph
   inspection paths remaining anywhere, query language frozen.
10. **Agent Capability Layer build order, remainder (old item 13 steps 4
    and 5 - steps 1 and 2 folded into items 1 and 6 above):**
    1. [ ] Build the task.md generator off the ripple query from item 6
       above. Markdown, plain checklist format, matching this doc's
       voice.
    2. [ ] Build the "re-reference a task.md" path: read file -> extract
       the originating query -> re-run against current DB -> diff ->
       report.
    As with item 1 above, Bart's direction is that this is a listing of
    capability pieces, not a locked sequence - propose impacts of
    alternative orderings (e.g. doing corpus-widening work in parallel
    with this rather than strictly before it) rather than assuming one.
11. **Truth Kernel Board Tier 0:** AI compiler surface hypotheses -
    TRUTH KERNEL v1.md's view-legality and Combine-legality lists are
    stale relative to the current 6-view reality (they only mention 5
    views and don't include ROLE in the allowed Combine pairs) - worth a
    pass to update DESIGN.md's spec language or explicitly note the gap
    there if ROLE participation in Combine is ever needed.
12. **Orphaned-module disposition review (hole vs. dead): INVESTIGATED
    AND REPORTED 2026-06-19.** Evaluated all 9 originally-listed
    candidates - `resolution/symbol_origin_resolver.py`,
    `inspection/explain_file.py`, `utilities/reachable_print_trace.py`,
    `context/build_context_packet.py`, the `contracts/` cluster
    (`contract_validator.py`, `contract_lifecycle.py`,
    `contract_health_aggregator.py`, `contract_types.py`, plus 3 empty
    stub files), `api/get_llm_context.py`, `api/query_entry.py`, the
    empty `orchestration/` directory, and
    `specification/tool_system_contract.json` - via actual import/call-site
    wiring checks (whole-tree grep for each symbol/module), not just
    surface-reading file contents, per this project's standing principle
    of never assuming dead from surface signals alone. **No
    integrate/dispose/delete action taken on any of it - this item's own
    gate requires reporting to Bart first, which is what this entry is.**
    Per-item disposition:
    - **Confirmed genuinely dead (zero callers anywhere), safe-to-remove
      candidates:** `utilities/reachable_print_trace.py` (a standalone
      manual debug script, has its own `__main__`, never imported
      elsewhere); `context/build_context_packet.py` (superseded by the
      now-live `context/build_context_bundle.py`; its own comments
      already flag its `dependencies`/`referenced_symbols` fields as
      placeholders not to be trusted); `api/query_entry.py` (a simpler,
      superseded precursor to `inspection/explain_file.py` /
      `get_llm_context_for_file` - returns only raw counts, no
      contracts/semantic summary); `contracts/contract_validator.py`,
      `contract_lifecycle.py`, `contract_health_aggregator.py` (a
      self-contained "contract health scoring" trio, fully wired to each
      other internally but with zero external callers anywhere); the 3
      empty stub files (`analysis_contract.py`, `failure_contract.py`,
      `representation_contract.py`, confirmed 0 bytes each). Also
      confirmed dead, though this is not a new finding:
      `contracts/contract_map.py` -> `contracts/contract_observer.py` ->
      `validation/contract_validation_pass.py` - existing regression
      tests (`tests/regression/test_drift_signals_wiring.py` line 15,
      `tests/regression/test_integrity_view_wiring.py`) already document
      this exact path as zero-caller, and `assessor/assessor.py`'s own
      comment (line 264) confirms the live pipeline replaced it with
      direct DB queries (`evaluate_file_contracts()` is explicitly
      labelled "a no-op stub" there).
    - **One genuine hole (missing capability that should be wired):**
      `inspection/explain_file.py` is a complete, working, DB-backed
      per-file report generator (imports, symbol density, top
      callers/callees, contract violations, a heuristic semantic
      summary) that nothing currently calls. TIER 2's Role-view
      evaluation above already wants exactly this kind of per-file
      explainability signal - this looks ready to serve that need
      directly rather than needing to be built from scratch.
    - **Not actually orphaned despite zero in-repo callers:**
      `api/get_llm_context.py` - its own docstring identifies it as "the
      ONLY function external systems should call" for LLM-context
      retrieval. Zero in-repo callers is expected here, not a sign of
      dead code: its intended consumer is the future agent CLAUDE.md
      describes, which doesn't exist yet. Recommend: keep as-is, revisit
      only once an actual external consumer exists to confirm the shape
      still fits.
    - **An unfinished-but-coherent feature, not three unrelated items:**
      `contracts/contract_types.py` (typed dataclasses - `SystemContract`,
      `DomainContract`, `OutputContract`, `DependencyRules`,
      `CoreInvariants`, `StabilityPrinciple`) and
      `specification/tool_system_contract.json` (the domains-shaped spec
      those dataclasses exactly mirror: ingestion/representation/
      analysis/indexing/orchestration domains, output_contract,
      dependency_rules, core_invariants, stability_principle) are a
      matched pair - confirmed nothing ever actually loads that JSON file
      into those dataclasses anywhere. The empty `orchestration/`
      directory is the third piece of this same unfinished thread: that
      same spec file's own "orchestration" domain definition ("Controls
      execution flow across all other domains... must not implement
      domain logic") describes exactly what should live there, and
      nothing has been written yet. Recommend treating these three as one
      decision, not three: either finish wiring the typed loader + start
      building the orchestration layer the spec describes, or
      consciously shelve all three together as a deferred design, not
      "delete the loader, ignore the spec, leave the directory empty by
      accident."
    - **New finding, outside the original 9-item list but same
      directory, worth flagging alongside it:** `contracts/
      load_contract.py` (and its consumers `parse_contract.py`/
      `scan_contract.py`) load a *different* `tool_system_contract.json`
      - the one physically sitting in `contracts/` itself
      (`schema_version: 3`, a "modules" pipeline-status document, not the
      "domains" spec above) - and then call `contract["domains"][...]`
      on it. That file has no `domains` key at all, so this chain would
      raise `KeyError` immediately if anything ever called it. Currently
      zero callers, so this is dormant rather than actively broken in
      production - flagging so nobody tries to wire `parse_contract.py`/
      `scan_contract.py` in as-is without first fixing which JSON file
      they're meant to read.
    - **Confirmed no overlap with item 2 (Truth.md Row 1/Row 5):** none
      of the above touch `MutationEvent`, intent/description capture, or
      "why was this change made" semantics at ingestion time - the
      "intent" hits in the contracts cluster are all the word
      "intentionally"/"system intent" in docstrings describing contract
      *design* intent, unrelated to mutation-author intent. Row 5
      remains genuinely unstarted new ingestion work, not something this
      review accidentally already solved or could accidentally break.
13. **Embedding-fallback crash risk in seed discovery: DONE 2026-06-18.**
    `oracle/db_oracle.py`'s `discover_seed_symbols_semantic()` previously
    only caught `ImportError` around the top-level
    `import numpy`/`from ...embedding_model import embed_text`
    statements - any failure *after* that point (the actual model load
    inside `embedding_model.get_model()`, which can fail at call time due
    to a missing model cache, no network access, a corrupted download,
    etc.) propagated uncaught all the way to every `ask.py` query. Fixed:
    the embedding-index build and lookup are now wrapped in
    `except Exception`, logging a warning (`_logger.warning(...)`, new
    module logger added) and falling back directly to `_discover_token()`
    - not via `discover_seed_symbols()`, since that path re-enters
    `discover_seed_symbols_semantic()` through `_discover_combined()` and
    would recurse forever against a failure that won't go away on retry.
    Proof: `tests/regression/test_embedding_seed_discovery_fallback.py`
    (3 tests) - one against the real environment (sentence-transformers
    genuinely not installed in this sandbox, confirming the fix handles
    the exact naturally-occurring case), one simulating a non-ImportError
    failure (`OSError`) to prove the broader exception net works and
    doesn't recurse, one confirming the public `discover_seed_symbols()`
    entrypoint used by `route_query()`/`QuerySession.run_query()` doesn't
    crash either. Full regression suite: 80/80 after.
14. **Dead `runtime_bindings` wiring: DONE 2026-06-18.** `parse_ast()`
    (`ingestion/parse_ast.py`) previously set `FileAnalysis.runtime_bindings`
    directly from its caller-supplied parameter - always `{}`, since
    `scan_project_files.py` line 192 hardcodes
    `runtime_bindings = {}  # still placeholder for now` - even though
    `_extract_runtime_bindings()` was already being called for real
    inside `_extract_symbol_references()`, just discarded after its own
    internal use. Production classification
    (`classify_references.py`'s `route_symbol(runtime_bindings=
    analysis.runtime_bindings, ...)`) therefore always received `{}`, so
    the "runtime" bucket was permanently empty in real output. Fixed:
    `parse_ast()` now also calls `_extract_runtime_bindings()` itself and
    merges the result onto `runtime_bindings` before it's stored on
    `FileAnalysis` - deliberately redundant with
    `_extract_symbol_references()`'s internal call rather than changing
    that function's return signature, to avoid touching its other direct
    caller (`tests/debug/test_symbol_pipeline_trace.py`).
    `scan_project_files.py`'s placeholder line is left untouched (still
    correctly describes the parameter it passes; the fix lives entirely
    inside `parse_ast()`). Proof:
    `tests/regression/test_runtime_bindings_wiring.py` (3 tests) - new
    fixture `tests/fixtures/sample_project/runtime_bucket_case.py`
    (`ai = engine.ai_system; ai()`) run through the real pipeline
    (`parse_ast()` -> `classify_references()`, the same two calls
    `analyze_files()` chains in production) confirms the reference is
    classified `bucket='runtime'`; a regression-guard test confirms
    forcing `runtime_bindings` back to `{}` (the exact pre-fix production
    state) loses the bucket on the same fixture, proving this test would
    have caught the original bug. Full regression suite: 80/80 after.

---

## 4. Chronological session log

Moved to HISTORY.md (section B) as part of the 2026-06-18 TRACKER/HISTORY
split - full dated session-by-session record, verbatim, nothing dropped.
