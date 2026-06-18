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
- [ ] Stability signal usefulness - open.
- [ ] Integrity signal usefulness - open.
- [ ] Subsystem interpretability - the correctness bug is fixed (see Tier
  1), but evaluation against real debugging/onboarding tasks hasn't
  happened yet.
- [ ] Role classification interpretability - same shape: correct and
  tested, not yet evaluated against real tasks.

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
(mandatory)" section is the binding procedure; this section is the
incident log that justifies it.

### 2a. Silent file-truncation bug

Edit and full-file Write calls in this repo have repeatedly produced files
on disk that are silently truncated - missing content from the middle or
end of the file - while the Read tool's in-context view shows the
complete, correct content immediately after. Severity ranges from
syntactically obvious (cuts mid-keyword, caught by `ast.parse()`) to
syntactically invisible (cuts mid-comment or right after a function's last
statement, so the function silently falls off the end and implicitly
returns `None` - no `SyntaxError`, looks fine, is wrong). On at least one
occasion (`Truth.md`, 2026-06-17) the Read tool displayed ~130 lines of
fully-formed, plausible content that had never been written to disk at
all - confirmed via `wc -l` against the real file. Retrying via Write
after an Edit failure is not a fix - confirmed at least once that a Write
retry reproduced the exact same truncated byte count as the prior failed
Edit.

**The only confirmed-reliable fix:** a direct bash heredoc rewrite (or
heredoc append onto an already-verified-correct prefix), followed by
`wc -l`/`wc -c` + (for `.py` files) `ast.parse()` + a full bash-side diff
against the intended content string. Zero diff output is the only
authoritative confirmation - line/byte counts and tail snippets are a
useful quick first pass but not sufficient alone, since truncation can
land at a plausible-looking boundary partway through. Full procedure is in
CLAUDE.md's "File write verification (mandatory)" section; this tracker
file itself was written and verified using that exact procedure.

**Incident log (at least 14 confirmed occurrences across this project's
sessions, in order):**
1. 2026-06-16 - small Edit to `query_session.py` truncated mid-statement
   (10041 of ~10222 bytes).
2. 2026-06-17 - `api/oracle_router.py` truncated twice (lost
   `_route_expand()`'s final `return`, causing a downstream `TypeError`);
   a Write-tool retry reproduced the identical truncated byte count.
3. 2026-06-17 - `tests/regression/test_run_algebra_end_to_end.py`
   truncated.
4. 2026-06-17 - REFACTOR OPS BOARD.md itself silently dropped an entire
   appended section.
5. 2026-06-17 - all 5 files touched in the shape-contract audit
   (`truth/views.py`, `truth/subsystem_view.py`, `truth/query_executor.py`,
   `truth/query_plan.py`, `truth/query_compiler.py`) truncated mid-file;
   plus both new test files for that session were written via heredoc
   from the start; plus REFACTOR OPS BOARD.md's own section about this was
   truncated mid-sentence on the first attempt.
6. 2026-06-17 (later) - the determinism-test-fix edit to
   `test_role_view_routing.py` truncated mid-comment.
7. 2026-06-17 (later still) - an Edit to the new
   `test_discovery_api_and_subsystem_fix.py` produced no error and a
   correct-looking in-context view, but the on-disk byte count was
   provably identical to the pre-edit file.
8. 2026-06-17 (later session) - `contracts/contract_drift_classifier.py`
   truncated mid-comment, missing its entire classification loop and
   `return signals` statement (syntactically valid, so `ast.parse()` alone
   did not catch it).
9. 2026-06-17 (same session) - `Truth Kernel Board.md` truncated mid-word
   on the very next edit after #8 was fixed.
10. 2026-06-17 (later session) - all four files in the single-file-filter
    fix batch (`oracle/embedding_model.py`, `truth/query_plan.py`,
    `truth/query_executor.py`, `truth/query_compiler.py`) came back
    truncated - the worst single-batch blast radius on record. One
    (`embedding_model.py`, cut mid-keyword `def`) was syntax-breaking; the
    other three were not.
11. 2026-06-17 (later still) - all 6 old test files edited during the
    pre-regression-suite test audit were truncated, including one
    (`test_db_utils.py`) that `ast.parse()` reported as fine despite being
    cut to a single half-written comment line with no actual code - the
    exact "passes ast, still wrong" case the verification procedure exists
    to catch.
12. 2026-06-17 (run-on continuation) - all 3 test files edited while
    fixing the bucket-gate bug were truncated mid-line despite the Edit
    tool itself reporting success.
13. 2026-06-17 (Pass 2 session) - both `DESIGN.md` and `TRACKER.md` itself
    were silently truncated by edits earlier in this same session (the
    Agent Capability Layer rewrite, and this file's item-13 expansion).
    Caught only because this section's own procedure was followed before
    moving on to unrelated work: `wc -l`/`wc -c` against `git show
    HEAD:<path>` showed DESIGN.md on disk at 438/451 lines and TRACKER.md
    at 951/952, both cut off mid-word with no trailing newline. Recovered
    by treating the git HEAD blob as the verified-correct base, re-applying
    the intended edits via a bash/python splice (not Edit/Write on the
    live file), and writing the result via direct redirect, each verified
    with a zero-diff check before moving on. Worth naming explicitly: this
    is the first time the bug has hit this tracker file's own
    self-description of the bug - a reminder that "we already wrote the
    procedure down" is not the same as "the procedure ran this time."

Treat this as a standing defect for every future session in this repo,
not as noise: verify every Edit/Write via the bash-diff procedure before
moving on, every time, no exceptions.

### 2b. Stale/locked `.pyc` cache bug (two variants)

**Variant 1 (2026-06-17, oracle_router.py):** a locked/undeletable stale
`.pyc` in `api/__pycache__/oracle_router.cpython-310.pyc` (`rm` returned
"Operation not permitted") had a recorded mtime+size that happened to
exactly match an intermediate, pre-fix saved state of the `.py` source.
Python's normal timestamp-based cache-invalidation check considered it
valid and silently ran the stale bytecode even after the real source fix
had landed and `__pycache__` had apparently been cleared -
`_detect_intent()` kept returning `general_query` for purpose/why/role
questions well after the source fix. Diagnosed by comparing
`inspect.getsource(module.func)` (correct) against actually calling
`module.func(...)` (wrong/stale) - when these disagree, suspect a
stale/locked pyc before assuming the source is bad. Fixed by `touch`-ing
the source file to force a new mtime, invalidating the cache and forcing
a recompile.

**Variant 2 (2026-06-17, run-on continuation, persistence_engine.py): more
concerning.** After landing a real source fix, the function still produced
the old (wrong) behavior. `inspect.getsource()` showed the corrected
source, but `dis.dis()` on the *same live function object* showed the OLD
bytecode. The cached `.pyc`'s embedded source mtime/size matched the live
`.py` file's mtime/size exactly, byte for byte - meaning this time even
`rm -rf __pycache__` + `-B` did NOT help, because `-B` only suppresses
*writing* new `.pyc` files, it doesn't stop Python from *reading and
trusting* an already-existing one that still validates, and both
`rm`/`os.remove()` on the `.pyc` failed with `PermissionError` on this
virtiofs-mounted folder even though the owning process had full rwx.
Fixed the same way as Variant 1 - `touch`-ing the source to bump its mtime
forward - which worked because the FUSE layer allowed in-place rewrite of
the `.pyc` even though it refused unlink, so the cache then self-healed on
next import.

**Takeaway for future sessions:** if `inspect.getsource()` and `dis.dis()`
on the same live function object ever disagree, or if a function's
runtime behavior contradicts its visibly-correct source, suspect a stale
`.pyc` before assuming the code itself is wrong - and reach for `touch
<source.py>` rather than trusting a `__pycache__` deletion to have been
sufficient, since on this mount it sometimes isn't.

---

## 3. Open items / next steps

In rough priority order, deduplicated across all four source files:

1. **Phase 2 evaluation work (Truth Kernel Board Tier 2):** evaluate
   Stability signal usefulness, Integrity signal usefulness, Subsystem
   interpretability, and Role classification interpretability against
   real debugging/onboarding tasks - all four are correctness-verified
   already, this is a judgment-call evaluation, not a coding fix.
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
15. **CCSS pipeline: decision made and executed 2026-06-17 - SHELVED.**
    Moved from `tools/analysis/ccss - redesign into tool over analysis db/`
    to `tools/analysis/_shelved/ccss/` (byte-for-byte, verified via sha256
    diff; no code changes). Rationale, in addition to the findings below:
    the folder's own internal imports (`tools.analysis.ccss.*`) never
    matched its actual on-disk path (spaces, no real `__init__.py`), so
    the pipeline could not have run as written even before considering
    integration. Full rationale recorded in
    `tools/analysis/_shelved/ccss/SHELVED.md`. If contract-axis test
    coverage becomes a real need later, `pass1.py` (structural extraction)
    and `gap_ledger.py` (snapshot diffing) are worth reusing; PASS2/PASS3
    need a from-scratch build against the real spec, not a patch - see
    SHELVED.md for why. Original findings, preserved for context: found
    during Pass 2 doc review (2026-06-17), the folder contained a working
    PASS1 -> PASS2 -> PASS3
    implementation (`pass1.py`/`pass2.py`/`pass3.py`/`run.py`/
    `scan_tests.py`/`snapshot_store.py`/`ledger_store.py`/
    `snapshot_compare.py`/`gap_ledger.py`/`regression_check.py`) that
    structurally matches the canonical spec in
    `docs/current predecessors still useful/pre ccss/prompt.md` (same
    file_id/test_id/symbol_uid identity model, same PASS1/2/3 contract
    boundaries). It is not wired into the main pipeline, the oracle
    router, or the Truth Kernel - the only outside reference is
    `engine/pipeline_dependency_tracer.py` tracking it as a known import
    bucket, not calling it. More importantly, PASS2's `enrich_symbol()` is
    a pure passthrough (no fqdn/role/confidence - the semantic enrichment
    the spec calls for was never implemented) and PASS3's `gaps` list is
    structurally always `[]` (coverage axes are computed from raw surface
    tokens and symbol_uid presence, which is trivially complete by
    construction, not from actual role/runtime resolution) - this is the
    project's own "looks done, isn't" pattern again. `snapshots/` and
    `ledger/` are currently empty on disk, and `regression_check.py`
    hardcodes two specific timestamped snapshot filenames that don't
    currently exist, so it would fail if run as-is. Nobody has decided
    whether this is worth finishing (real semantic enrichment + real gap
    detection), worth integrating into the main DB-backed pipeline (the
    folder's own name suggests that was the intent - "redesign into tool
    over analysis db" - but the code still reads source files directly via
    AST, not the DB), or worth shelving. Needs a decision before any more
    time goes into it either direction.
16. **Semantic Identity Reconstruction: status corrected from "Phase 3 not
    started" to "Phase 3 deliberately abandoned."** Found during Pass 2 doc
    review (2026-06-17), grounded against `graph/symbol_router.py` and
    `graph/route_trace.py`. The historical plan (now in
    `docs/del/Semantic Identity Reconstruction Migration Plan.md`)
    proposed a phased bridge - shadow pipeline, CP2.5/CP3 checkpoints -
    eventually replacing `route_symbol()` with semantic-identity-aware
    resolution. The shadow/trace infrastructure (`route_symbol_shadow()`,
    `TraceCollector`, CP0-CP4 checkpoints) was built close to as specified
    and is real and live, called from
    `classification/classify_references.py`. But the planned end state -
    retiring or replacing the legacy router - was not just "not yet
    reached," it was tried and explicitly reversed: the code's own
    comments mark an earlier "CP2.5 semantic observation layer" that could
    influence routing as `(DEPRECATED)` and "removed from execution,"
    replaced by a DB-backed "seed discovery" layer with "no semantic
    interpretation, no identity reconstruction," plus a permanent
    trace-only CP2.5 that explicitly "MUST NOT influence CP3 routing
    decisions." See DESIGN.md section 4's new "shadow/observability layer"
    subsection for the full writeup. No action item here - this is a
    status correction, not an open task. The system arrived at a stable,
    intentional end state; it's just a different end state than the
    original plan described, and nothing previously said so.

---

## 4. Chronological session log

### 2026-06-16 (morning)

**Noise-filter unification.** `split.i.surface` and `cursor.self.oracle.conn`
-style internal dotted-accessor symbols were showing up as query seeds -
structurally real but not meaningful query targets. Unified into
`oracle/symbol_noise.py` (`is_noise_symbol`/`is_accessor_chain_noise`),
applied consistently at both discovery time (`db_oracle._discover_token`)
and expansion time (`oracle_router._is_valid_symbol`) - no more drift
between the two call sites' filtering behavior.

**AI compiler wired to a real LLM.** `truth/query_compiler.py` rewritten
to try a local Ollama call (`llama3.2:3b`) first, validate its output
through `QueryPlanner`, and fall back to the original rule-based
intent->AST table on any failure. Local-only, no Anthropic API call.

**Torch warning diagnosed (not yet fixed for real - see 2026-06-17 entry
below for the actual fix).** The recurring torch warning on Windows
(sentence-transformers pulling in PyTorch) doesn't respond to
`PYTHONWARNINGS=ignore`, because it's emitted via `logging.warning()`
(`torch.distributed.elastic`'s own glog-style logger), not via
`warnings.warn()` - the `warnings` module's env var has no effect on a
plain `logging` call.

### 2026-06-16 (later same day) - agent readiness gaps closed

An evidence-based assessment (see REFACTOR OPS BOARD.md's "AGENT READINESS
ASSESSMENT") found the individual pieces solid but no wired front door:
`QuerySession.run_algebra()` - the one method chaining real NL -> AI
compiler -> AST -> executor -> real views - had zero callers anywhere and
had never been run end-to-end against a live project DB. Two views
(SUMMARY, SUBSYSTEM) were similarly orphaned: implemented, but with only
stub-dict test coverage, never called from `assessor.py`. Legacy dead-end
agents (`oracle/agent.py`'s `GraphOracleAgent`, `oracle/nl_agent.py`'s
`NaturalLanguageGraphAgent`) bypassed oracle_router/QuerySession/Truth
Layer entirely and looked like "the agent" to a future session, risking
being mistaken for the real integration point.

Closed same day:
- `Assessor.summary_view()`/`subsystem_view()`/`all_views()` wire SUMMARY
  and SUBSYSTEM to real DB-backed data (`reduced_snapshot()`/
  `bucket_summary()`/`file_count()` for SUMMARY, the real graph snapshot
  for SUBSYSTEM).
- `Assessor.ask(text)` wraps `session().run_algebra(text,
  views=self.all_views())`; `tools/analysis/ask.py` is the new CLI
  entrypoint - `python tools/analysis/ask.py <db_path> "<question>"` - run
  successfully end-to-end against the real project DB.
- Deleted `oracle/agent.py`, `oracle/nl_agent.py`, and their only real
  consumer `tests/debug/oracle_compare_harness.py`, per Bart's conditional
  approval ("If you have something better they can both go") - `ask.py` /
  `Assessor.ask()` is that something better.
- Deleted `truth/test_harness.py` (`TruthTestHarness`) - a manual
  print-based runner where pass/fail meant only "no exception was thrown,"
  zero real callers, per Bart's stated preference for real assertion-based
  tests over decorative harnesses.
- New regression suite: `tests/regression/test_run_algebra_end_to_end.py`
  (4 assert-based tests - all 5 views build from real seeded data,
  SUMMARY/SUBSYSTEM execute through the algebra, `ask()` runs end-to-end,
  `ask()` is deterministic). Full sweep: this suite (4) +
  `test_oracle_router_persistence_lock.py` (6) +
  `truth/tests/test_query_algebra.py` (32) = 42/42 passing.
- First documented occurrence of the silent file-truncation bug (see
  section 2a, incident #1).

### 2026-06-16 (same day, loose-script cleanup pass)

Audited every loose top-level `.py` file in `tools/analysis/` plus two
test files that surfaced as dependents. All traced to one root cause:
`tools/analysis/run_analysis_pipeline.py` does not exist anywhere in the
repo and never did in this session's visibility - it was the
orchestration entrypoint an earlier architecture iteration was built
around, since superseded by `engine/run_engine.py` (ingestion) + `ask.py`
(querying).

Deleted 7 dead files: `run.py` (subprocessed into the missing module),
`debug_run.py` (imported it directly), `run_parity_test.py` (imported 5
more nonexistent `engine.core.*` modules plus a nonexistent
`engine.parity.ParityChecker`, had an internal `NameError` bug and
unfinished placeholder comments - superseded by the real, working
`engine/parity_contract.py` + `engine/structural_parity_diff.py`),
`load_config_profiles.py` (expected a nonexistent
`analysis_profiles.yaml`, zero callers), `tests/core/test_pipeline_smoke.py`
and `tests/core/test_reference_extraction_integrity.py` (both imported the
missing module - their other imports, `test_db_utils.py` and
`graph/project_context.py`, were confirmed still legitimately used by
other live tests), and a top-level `rewrite plan for routing to
classification.md` (a near-duplicate early draft of `docs/Symbol
Classification Stabilization Plan.md` - kept the cleaner copy, deleted
this one).

Kept, dormant but functional (standalone diagnostic CLIs, no broken
imports, just no current callers): `db_probe_toolsold.py`,
`db_toolsold_audit.py` (heavy overlap with each other - candidates to
merge if ever revived), `debug_gap_report.py`.

Added STATUS NOTE headers (no other content changed) to three older
planning docs that all assumed the now-dead `run_analysis_pipeline.py`/
`debug_run.py` were the live entrypoints: `Symbol Classification
Stabilization Plan.md` (now condensed into DESIGN.md section 4),
`current predecessors still useful/architectural triage protocol.md`
(out of scope for this consolidation pass - see CLAUDE.md / Bart's
two-pass instruction), and `contracts  + visibility.md` (now condensed
into DESIGN.md section 5).

### 2026-06-16 - Truth.md Phase 1 findings: algebra is alive

Ran the actual verification Phase 1 calls for: are the algebra mechanics
real or dead code? Findings, read directly from code, not assumed:

The mechanics are alive and tested - `truth/query_ast.py`
(Select/Filter/Combine), `truth/query_plan.py` (Planner + Registry), and
`truth/query_executor.py` (Executor) are all real, non-stub
implementations, with 25+ passing tests in
`truth/tests/test_query_algebra.py` covering valid/invalid Combine pairs,
metrics, filter keys, and executor determinism.

At the time of this finding, three of five views were wired to real data
(STRUCTURE, STABILITY - though with `drift_signals` hardcoded `[]`, and
INTEGRITY); SUMMARY and SUBSYSTEM were still orphaned. Both gaps were
closed the same day (see the "agent readiness gaps closed" entry above) -
by the time this finding was written up in full, all 5 views were real,
and the verdict on Phase 1's exit criteria ("Truth Layer produces real
output from real project data") was recorded as **MET**. Phase 1 closed;
Phase 2 (router vs. Truth Layer comparison) was left open, to start
whenever prioritized.

### 2026-06-16/17 - Truth.md Phase 3: evidence-based gap audit

Trigger: Bart noticed `ask()` had no way to answer "what is the purpose of
this file" and asked whether that was one hole or a symptom of several.
Ran real questions against a real DB (worked around a sandbox-only sqlite
`database disk image is malformed` error - likely a Windows-to-sandbox
binary-file mount sync artifact, not a project bug - by re-running
ingestion into a fresh temp DB), recorded actual output, no guessing.
Found 5 concrete rows:

- **Row 1** - "what is the purpose of X" / "why does X exist" / "what is
  the role of X" all fell to the catch-all `general_query` intent (no
  category existed for purpose/why/role phrasing) and produced the
  byte-identical fallback `Combine(Select(STABILITY), Select(INTEGRITY))`
  regardless of which file was actually named - the symbol mentioned in
  the question never had a path into those views at all. Absent category,
  not a tuning problem.
- **Row 2** - role/responsibility classification existed and was real
  (`engine/responsibility_map.py` + `Assessor.responsibility_map()`,
  keyword-matching file path + callee names against real DB data,
  confirmed with real totals across the bucket categories) but had zero
  path into `all_views()`/`Select()`/`Combine()` - a wiring gap, same
  shape as the SUMMARY/SUBSYSTEM orphaning already fixed.
- **Row 3** - `drift_signals` was hardcoded `[]` at the
  `build_stability_view()` call site - a query against it validates and
  executes cleanly, and silently always returns nothing real. Flagged as
  "the most dangerous gap shape," since the algebra can't signal that it
  doesn't actually know.
- **Row 4** - `_module()` in `truth/subsystem_view.py` assumed dotted,
  module-qualified symbol names (`symbol.split(".")[:2]`), but this
  codebase's real call graph is mostly bare function names with no dots -
  so the "subsystem" key ended up being the function name itself, 355
  "subsystems" for a project with roughly 60-70 real files. Worse than a
  hole, since it looks like an answer.
- **Row 5** - no intent/description field exists anywhere on
  `MutationEvent` (`shared/types.py` has only `line_number`/`target`/
  `operation`/`raw_expression`), so "why was this mutation made" has
  nothing to recover regardless of view or query - genuinely never
  captured, same shape as Row 1.

Pattern across all 5: two failure shapes, not five unrelated ones - "never
captured" (Rows 1, 5, needs new ingestion) vs. "captured/computable but
not wired or wired wrong" (Rows 2, 3, 4, needs only connection work).
Rows 2, 3, and 4 were all closed over the following day - see the three
entries below.

### 2026-06-17 - ROLE view added (Row 1/Row 2 closed)

Per Phase 4's rule ("one missing capability, one implementation, one
measurable improvement"): added ROLE as a 6th Truth Layer view, same fix
pattern as the SUMMARY/SUBSYSTEM wiring - connect an existing thing, no
new heuristics.

- `truth/views.py`: `RoleView` dataclass + `build_role_view()`, a pure
  transform of `responsibility_map()`'s existing output.
- `assessor/assessor.py`: `Assessor.role_view()`, wired into `all_views()`
  (now 6 keys: STRUCTURE/STABILITY/INTEGRITY/SUMMARY/SUBSYSTEM/ROLE).
- `api/oracle_router.py`: `_detect_intent()` gained a `role_query` branch
  (purpose/why-does/why-is/role-of/what-role/what-kind-of phrasing);
  `_select_primitives()` maps it to `["role"]`; `_route_expand()`'s
  `intent_budget` gained a zero-traversal-depth entry for it (ROLE is
  file-level, not graph-dependent - zero budget is the honest answer).
- `truth/query_plan.py` / `truth/query_compiler.py`: ROLE registered with
  `totals`/`files` metrics; `role_query` compiles directly to
  `Select("ROLE", ...)`, not a Combine fallback.

Measured improvement: `assessor.ask("what is the purpose of ingest.py")`
now returns `intent == "role_query"`, a `Select` (not `Combine`) AST, and
real per-file role data - not the previous byte-identical fallback
regardless of file named.

New coverage: `tests/regression/test_role_view_routing.py` (5 tests).
Full sweep: 47/47 (5 new + 4 run_algebra_end_to_end + 6
oracle_router_persistence_lock + 32 pytest).

**Two environment incidents this session** (see section 2 for the
canonical writeup): the silent-truncation bug (incidents #2-#4) and the
first documented stale-`.pyc` variant (section 2b, Variant 1) -
`_detect_intent()` kept returning `general_query` even after the source
fix landed, traced to a locked, undeletable `.pyc` whose mtime+size
coincidentally matched an intermediate pre-fix save.

### 2026-06-17 (continued) - algebra shape contract audit

Real bug from Bart's Windows machine (the only place the live Ollama
compiler is reachable): `AttributeError: 'list' object has no attribute
'totals'`. Root cause was not an AI compiler error - Ollama had compiled
`Select("ROLE", metric="files")` for a one-file question, a legitimate,
registry-valid, arguably more precise choice than the full view. The bug
was a test (and implicitly, any future consumer) assuming `QueryResult.data`
always had one fixed shape.

Per Bart's framing - the algebra is "valid checkboxes the AI selects...
the consumer's job is to handle whichever valid checkbox came back, not
demand one specific one" - did a full audit, not a one-test patch:

- `truth/query_executor.py`: added `get_field(result, name, default)`,
  the shared shape-safe way to read any `QueryResult` field regardless of
  whether `metric=None` (attribute/key access on the full view) or
  `metric=name` (already-unwrapped value).
- Found and fixed a real shape inconsistency: SUBSYSTEM was the only one
  of 6 views whose full-view shape was a bare dict instead of a
  dataclass. Added `SubsystemView` dataclass, updated
  `build_subsystem_view()` to return it.
- Removed dead+wrong `QuerySemanticsRegistry.validate_metric()` (zero
  callers, checked the wrong dict - would have rejected every legitimate
  metric had it ever been called).
- `query_compiler.py`'s `_ALGEBRA_SPEC` (the text fed to Ollama) now
  generates directly from the registry instead of being hand-typed,
  closing a drift risk between what the model is told and what's
  enforced.
- Fixed the two broken consumers to handle real shapes via `get_field()`
  rather than assuming one.
- New suite: `tests/regression/test_query_result_shape_contract.py` (4
  tests) - proves `get_field()` agrees with direct metric-selection for
  every (view, metric) pair against real data, returns the documented
  default rather than guessing, and that every view's full shape is now
  attribute-accessible.

Full sweep: 57/57 (25 regression + 32 pytest).

**Environment note:** every one of the 5 source files touched this
session was truncated on disk (incident #5, section 2a).

### 2026-06-17 (later) - determinism test fix

Bart's Windows run hit `test_ask_role_question_is_deterministic` failing
on byte-identical-AST comparison - two calls of the same question
compiled to two different, both-valid ASTs (`Select("ROLE")` vs.
`Select("ROLE", metric="files")`). Same bug class as the shape-contract
fix, one level up: an LLM compiler at `temperature=0.0` is not guaranteed
to land on the same valid choice twice (greedy decoding isn't
bit-reproducible across requests with llama.cpp/Ollama - floating-point
non-associativity in parallel reduction, a backend property, not a
codebase bug).

Fixed the test's invariant, not the compiler: now asserts
`intent == "role_query"` on both calls plus agreement on the real role
classification read via `get_field()`, rather than raw AST text equality.
No production code changed. Full sweep: 57/57 (same counts, fixed test
now passing for the right reason). This fix's real value only shows on
Bart's Windows machine, since that's the only place the live-Ollama
nondeterminism actually occurs.

**Environment note:** this single-test edit was also truncated (incident
#6).

### 2026-06-17 (later still) - Track A completed; Track B item 2 closed

Per Bart's direction ("Track A, then also fix subsystem fragmentation"),
did both in one session.

**Track A - DB-backed symbol discovery API:** added `list_symbols`,
`find_symbols`, `find_files`, `find_modules`, `symbol_module_map` to
`oracle/db_oracle.py`, all DBReader-only (distinct in purpose from the
pre-existing `discover_seed_symbols`, which is NL-query relevance scoring
for `route_query`'s seed step - these are general-purpose lookup
primitives for browsing/bootstrap). Confirmed production seeding was
already 100% DB-backed (`QuerySession.run_query()` already passes
`self.oracle.discover_seed_symbols` as `find_symbols_fn`); removed the
dead `_seed_symbols()` decoy wrapper in `api/oracle_router.py` (its one
call site was already commented out - never live, same "looks like a
feature, isn't" shape as the deleted `_apply_intent_weights` stub and the
deleted legacy agent files).

**Track B item 2 - SUBSYSTEM fragmentation (Row 4):** root cause was
`_module()`'s dotted-name assumption not matching this codebase's mostly-
bare-name call graph. Fix: `_module()`/`build_subsystem_view()` now take
an optional `module_map` (built by the new `symbol_module_map()` - real
`symbols` table declarations, file_path's containing directory as the
module); a symbol is looked up in the map first (exact, then bare tail
segment), with the old dotted-name heuristic as fallback only for symbols
absent from the map (builtins, external calls, noise) - confirmed
non-breaking against the existing test fixture before writing the fix.
Wired in: `Assessor.subsystem_view()` passes the real map by default, so
the fix is live on the production path.

New suite: `tests/regression/test_discovery_api_and_subsystem_fix.py` (7
tests - 5 discovery methods including the ambiguous-name deterministic
tie-break, plus a direct with-vs-without-module_map comparison showing
`"do_thing"` stops being its own singleton subsystem). Full sweep: 64/64.

**Environment note:** a fifth truncation incident (incident #7, section
2a).

### 2026-06-17 (later session) - Track B item 1 closed: drift_signals wired

Closed Row 3. Same shape as Row 2/4: `ContractDriftClassifier`
(`contracts/contract_drift_classifier.py`) already existed with the exact
output shape `build_stability_view()` expects, with zero callers anywhere.

- `assessor.py`'s `stability_view()` now calls
  `ContractDriftClassifier().classify(reports)` and passes the real
  result, replacing the hardcoded `[]`.
- `file_contract_reports()` violations gained a `"layer": "graph"` key
  (the only contract this method produces, `symbol_reference_integrity`,
  isn't in the declared-contract registry, so `"graph"` was chosen as the
  most accurate available label, not pulled from a registry lookup that
  doesn't cover it).
- `ContractDriftClassifier.classify()` hardened with a `_field()`
  dict-or-attribute shape-safe accessor (same principle as `get_field()`),
  since real violations are plain dicts, not the attribute-style
  `ContractViolation` from the dead `contract_observer.py` path.

Measured improvement: a seeded DB with N broken symbol references now
returns real, correctly-classified drift signals (confirmed for
transient/recurring/structural count thresholds) instead of `[]`.

New suite: `tests/regression/test_drift_signals_wiring.py` (6 tests).
Full sweep: 60/60 (54 prior + 6 new).

With Rows 2, 3, and 4 all closed, every "captured/computable but
wired-wrong" gap from the Phase 3 audit is resolved - what remains (Row
1's non-Row-2 remainder, Row 5) is exclusively the "never captured"
category, needing new ingestion.

**Environment note:** two more truncation incidents (#8, #9, section 2a).

### 2026-06-17 (later session) - single-file ROLE filter scoping fixed; torch warning actually silenced

Bart hit two real problems running `ask.py "what is the purpose of
db_probe_toolsold.py"` on his Windows machine.

**Torch logging warning (the real fix, vs. the diagnosis-only note from
2026-06-16):** confirmed it's emitted by `torch.distributed.elastic` via
plain `logging`, not `warnings.warn()`. Fixed by silencing the actual
source: `logging.getLogger("torch.distributed.elastic").setLevel
(logging.ERROR)`, added in `oracle/embedding_model.py`'s `get_model()`
alongside the (harmless, left in place) existing `warnings.filterwarnings()`
calls.

**ROLE-view filtering gap (the bigger issue):** the query returned every
file in the project instead of just the one named. Three independent bugs
stacked:
1. `Filter` (`query_ast.py`) and `_apply_filter` (`query_executor.py`)
   were both fully implemented and planner-validated, but nothing upstream
   ever constructed a `Filter` - `Select.filter` had been `None`
   end-to-end since the algebra was built. Same orphaned-primitive shape
   as drift_signals.
2. `QueryExecutor._select()` applied `Filter` *before* metric projection -
   every real view is a dataclass, not a dict/list, so even a correctly
   built `Filter` would have silently done nothing. Fixed by reordering:
   project the metric first, then filter.
3. `VALID_FILTER_KEYS` had no `"ROLE"` entry at all - added
   `{"file_path"}`.

Fixed deterministically, not via the AI compiler (the buggy run had gone
through Ollama and still produced `metric=None` despite the prompt
preferring `metric="files"` for one-file questions - prompt compliance
isn't guaranteed even at temperature 0.0). `query_compiler.py` gained
`_extract_single_file_filter()` (regex, single `*.py` token) and
`_maybe_scope_to_named_file()` (rescopes a bare unfiltered
`Select("ROLE")` to `metric="files"` plus a `Filter("file_path",
"endswith", name)`, re-validated through the planner) - a new
`"endswith"` operator was added since the question names a bare filename
while `DBOracle` stores full paths. Wired into both `compile_query()` and
`compile_and_explain()`, deliberately narrow (only fires on the exact bug
shape - a compiler that already chose a specific metric is left
untouched).

New suite: `tests/regression/test_single_file_filter_scoping.py` (10
tests). Full sweep: 80/80 (48 regression + 32 pytest).

**Environment note:** all four files touched in this batch were
truncated - the worst single-batch blast radius on record (incident #10,
section 2a).

### 2026-06-17 (later still) - old pre-regression-suite tests audited

Bart asked whether to weed out the old test files under `tests/core/`,
`tests/debug/`, `tests/integration/`, `tests/semantic/`, and
`test_embedding_seeds.py` (predate the `tests/regression/` convention).
Audit, not deletion, was the right call.

Before any change: 105 passed, 5 collection errors, all one root cause -
5 files imported `create_database`/`initialize_database` from the deleted
module path `persistence.persist_file_analysis`. Both functions are alive
in `persistence/persistence_engine.py` - just a stale import path, not
dead code.

Fixing the import alone would have been wrong:
`persistence_engine.create_database()` unconditionally deletes-then-
recreates its target file, and all 5 old tests called it against the same
hardcoded path - so every one of the 4 "assertion-only" tests was silently
wiping whatever the smoke test had just persisted and asserting against
an empty DB, vacuously true every time. Same "looks green, tests nothing"
shape as the drift_signals/orphaned-Filter bugs, in the old test layer.

Fix: moved the shared DB to an OS-temp-dir path
(`test_db_utils.py:SHARED_TEST_DB_PATH`, categorically can't collide with
a real product DB path); the smoke test builds it via a real
`EngineRunner` run and does not delete it afterward; the 4 downstream
tests now open it without wiping and `pytest.skip()` with a clear message
if unpopulated.

Once real, 4 of the 5 failed for real, surfacing genuine findings (not
caused by this change): 710+ `(file_path, name)` duplicate pairs (possibly
a real raw-engine-run duplicate-insertion issue, or dedup that normally
happens later in `persist_all()` but is bypassed by this direct smoke
test - undetermined at the time); stdlib/builtin callees reported as
"unresolved" (predates the noise-filter unification and doesn't know
those are expected not to resolve against the project's own symbols
table); and a "short names only" assumption that doesn't hold for
qualified stdlib call targets. Flagged to Bart rather than silently
patched, since it's a behavioral judgment call about the engine/
persistence layer. Full sweep after: 106 passed, 4 failed, 0 collection
errors.

**Environment note:** all 6 test files touched were truncated, including
one that `ast.parse()` reported as fine despite being cut to a single
half-written comment line (incident #11, section 2a).

### 2026-06-17 (run-on continuation) - bucket-gate bug root-caused; the 4 flagged failures resolved for real

Continuing directly: Bart's instruction was to actually fix the 4 flagged
failures, not leave them as known issues. All 4 shared one root cause,
plus a second, independent environment bug was found verifying the fix.

**Root cause: the function/class -> `symbols` insert was gated on a
condition that could never be true.** `persist_file_analysis()` checked
`if getattr(obj, "bucket", None) == "project"`, but
`FunctionRepresentation`/`ClassRepresentation` have no `bucket` field at
all and nothing ever sets one on them (`bucket` is only ever set on
`SymbolReference` objects). Unconditionally False for every function and
class in this codebase's history - the `symbols` table had never once
held a real function/class declaration. The 710+ "duplicate" finding from
the prior entry was downstream of an earlier patch (commit f7acec9) that
papered over this exact symptom by stuffing raw, uncanonicalized
caller/callee call-site names - including external/stdlib references -
into `symbols` under the wrong taxonomy (`symbol_type='caller'/'callee'`,
with zero live consumers reading that, confirmed via exhaustive grep -
`db_oracle.py`'s `symbol_module_map()` already explicitly filters to
`('function','class')`, defending against exactly this pollution).

Fix: removed the dead `bucket == "project"` gate (now unconditional,
matching the always-run `INSERT INTO functions`/`classes` directly above
each - `EngineRunner` only scans project-corpus files, so every
function/class found IS a project declaration by construction); removed
the caller/callee pollution block entirely. Verified end to end: a real
engine run now populates `symbols` with 660 real rows (552 functions, 108
classes), zero caller/callee noise.

**Second, independent bug found verifying the fix:** the persistence_engine
stale-`.pyc` variant documented in section 2b (Variant 2) - `touch`-ing
the source fixed it.

**Three of the four flagged tests needed real fixes once `symbols` held
real data for the first time:** a duplicate-edge `GROUP BY` was missing
`file_path` (flagging cross-file line-number coincidences as duplicates);
two tests were checking that stdlib/builtin/external callees resolve
against the project's own symbols table (wrong invariant - restricted both
to `WHERE bucket = 'project'`, confirmed 0 unresolved vs. ~170 false
positives before); the uniqueness test's `GROUP BY` was missing
`symbol_type`/`line_number`, flagging legitimate same-named methods on
different classes in the same file as duplicates - now effectively a
regression guard against the `symbols.canonical_id UNIQUE` constraint ever
loosening. The fourth (`test_symbol_storage_format.py`) needed no change,
it passed once the pollution block was gone.

**Full sweep after all fixes: 110 passed, 0 failed, 0 skipped, 0
collection errors** (up from 106 passed / 4 failed at the start of this
run-on session).

**Environment note:** all 3 test files touched here were truncated despite
the Edit tool reporting success (incident #12, section 2a) - at least the
thirteenth recorded incidence of the truncation bug across this project's
sessions, still standing, not noise.

### 2026-06-17 (Pass 2) - older predecessor docs assessed and disposed; CCSS and semantic-identity-reconstruction findings surfaced

Bart's go-ahead to do Pass 2: assess `docs/current predecessors still
useful/` (3 files) and its `pre ccss/` subfolder (7 files) for whether
their vision still aligns, is partially superseded, or fully superseded -
grounded against the actual current codebase, not just read against each
other.

**Disposition of all 10 files:**

- `architectural triage protocol.md` - left in place, unchanged. Already
  carries a 2026-06-16 status note marking the methodology "still a
  reasonable process" with one corrected stale reference
  (`run_analysis_pipeline.py` -> `engine/run_engine.py`). No new findings.
- `old checklist.md` (the "C3" classification model) - left in place, new
  status note added. Still substantially describes current reality:
  `route_symbol()` -> `_route_symbol_core()` is the same single-pipeline,
  no-re-entry model, and `classification_gap` is alive across the current
  codebase. What it predates: the shadow/trace observability layer (see
  DESIGN.md section 4 below).
- `pre ccss/CCSS  execution plan.md`, `pre ccss/Contract Coverage Surface
  System.md`, `pre ccss/prompt.md` - left in place, status note added to
  each. Not superseded - actually built (see item 15 below) - but the
  build only satisfies the structural contract, not the substance.
- `Module Governance.md` - moved to `docs/del/`. Superseded in specifics
  (file paths, `run_analysis_pipeline.py`/reducer ownership - that file is
  deleted) but its module-card methodology (OWNS / DOES NOT OWN / OUTPUTS /
  INVARIANTS / MATURITY) is the direct conceptual ancestor of DESIGN.md
  section 4's Authority Model, which superseded it.
- `pre ccss/Key insight about what we missed and where we are going.txt` -
  moved to `docs/del/`. Its diagnosis (premature semantic flattening in
  `route_symbol()` - leaf names like "dataclass" can't match fully-qualified
  project identities) was correct and was acted on; superseded by the fix
  now documented in DESIGN.md section 4, not by being wrong.
- `pre ccss/Semantic Identity Reconstruction Migration Plan.md` - moved to
  `docs/del/`. Partially superseded - see item 16 below for the full
  finding.
- `pre ccss/status as of 05242026.txt` - moved to `docs/del/`. A
  snapshot-in-motion ("Phase 2 actively working, Phase 2.5 emerging, Phase
  3 not started") whose motion has since stopped/redirected - historical
  waypoint only.
- `pre ccss/test file list.txt` - moved to `docs/del/`. Flat reference
  list, no standalone content to assess.

**New findings, written up in full in DESIGN.md and TRACKER.md (not
repeated here):**

- DESIGN.md section 4 gained a new "shadow/observability layer" subsection
  documenting `route_symbol_shadow()`/`TraceCollector`/CP0-CP4 as real,
  live, currently-undocumented architecture.
- TRACKER.md open items 15 (CCSS: built but Pass2/Pass3 are structural
  stubs, decision needed) and 16 (semantic identity reconstruction: status
  corrected from "Phase 3 not started" to "Phase 3 deliberately
  abandoned, different but stable end state reached") added to section 3.

**Separately, this same session caught and fixed a recurrence of the
silent file-truncation bug** hitting this tracker's own two most recent
edits - see section 2a, incident 13, for the full incident writeup.
