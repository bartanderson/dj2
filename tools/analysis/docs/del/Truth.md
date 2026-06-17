Phase 0 — Freeze

Goal:

No architecture changes.
No router changes.
No oracle changes.
No assessor changes.

Only verification.

Exit criteria:

Current output reproducible.
No active exceptions.

Status:

COMPLETE
Phase 1 — Prove Truth Layer Exists

Goal:

Determine whether the Truth Layer is a real subsystem or dead code.

Work:

Run QueryPlanner
Run QueryExecutor
Run Views
Against real assessor-generated data

Questions:

Can Select("STRUCTURE") execute?
Can Select("STRUCTURE","hotspots") execute?
Can Select("STABILITY") execute?
Can Combine(...) execute?

Exit criteria:

Truth Layer produces real output from real project data.

Nothing else.

Phase 2 — Compare Router vs Truth Layer

Goal:

Measure overlap.

For each question:

What depends on X?
What affects Y?
Show ingestion surface.

Run:

Router path
Truth path

Compare:

Signal quality
Noise
Determinism
Explainability

Exit criteria:

Know which system is actually producing useful answers.
Phase 3 — Identify Missing Truths

Goal:

Find actual deficiencies.

Not guesses.

Evidence only.

Examples:

Cannot answer dependency chains.
Cannot answer subsystem ownership.
Cannot answer persistence ownership.
Cannot answer drift source.

Every deficiency must be:

Question
Expected answer
Actual answer
Gap

No coding yet.

Phase 4 — Add One Truth At A Time

Only after Phase 3.

Rule:

One missing capability
One implementation
One measurable improvement

Example:

Need dependency path tracing.

Add dependency path tracing.

Measure improvement.

Then stop.

Phase 5 — Determine If Query Algebra Is Needed

Only after several missing truths are identified.

Question:

Are we repeatedly asking the same categories of questions?

If yes:

Promote those patterns into Query AST.

If no:

Keep using direct views.
Phase 6 — AI Compiler (Maybe)

Very late.

Only after:

Truth Views stable
Planner stable
Executor stable
Questions understood

Then:

English
→ Query AST
→ Planner
→ Executor
Forward Ontology Rule

When we complete a phase:

Keep:
    architectural truths
    validated assumptions
    proven capabilities

Delete:
    temporary diagnostics
    disproven assumptions
    obsolete plans

In other words:

The system remembers facts.
The system forgets scaffolding.
Immediate Next Step

Phase 1.

No code changes yet.

I want to verify whether:

Select("STRUCTURE")
Select("STABILITY")
Select("INTEGRITY")
Combine(
    Select("STRUCTURE"),
    Select("STABILITY")
)

can execute against your current assessor-generated views.

If they do not execute, we fix the smallest failure.

If they do execute, we immediately learn whether the Truth Layer is alive or merely present in the repository.

---

## Phase 1 findings (2026-06-16, read directly from current code — not assumed)

**The algebra mechanics are alive and tested.** truth/query_ast.py (Select/
Filter/Combine), truth/query_plan.py (Planner + Registry), and
truth/query_executor.py (Executor) all exist as real, non-stub
implementations. truth/tests/test_query_algebra.py has 25+ passing-shaped
tests covering valid/invalid Combine pairs, valid/invalid metrics, valid/
invalid filter keys, and executor determinism. So: yes, Select and Combine
execute, and they execute deterministically.

**Three of five views are wired to real project data.** assessor.py calls:
- `structure_view()` → `build_structure_view(self.snapshot(), builtin_symbols=self.oracle.builtin_symbols())` — real DB-backed graph, real builtin-exclusion.
- `stability_view()` → `build_stability_view(self.file_contract_reports(), drift_signals=[])` — real contract reports, but `drift_signals` is hardcoded to `[]` at the call site, never populated from anywhere.
- `integrity_view()` → `build_integrity_view(self.validation_summary(), self.snapshot())` — real validation data.

**RESOLVED 2026-06-16 (same day, later session).** Both findings below are
now closed:

- ~~Two views are orphaned~~ — `Assessor.summary_view()` and
  `Assessor.subsystem_view()` (assessor/assessor.py) now wire
  `build_system_summary_view()` and `build_subsystem_view()` to real
  DB-backed data (`reduced_snapshot()`/`bucket_summary()`/`file_count()`
  for SUMMARY, the real graph snapshot for SUBSYSTEM). Both have direct
  test coverage against real seeded data in
  `tests/regression/test_run_algebra_end_to_end.py`
  (`test_all_views_real_data`,
  `test_algebra_select_summary_and_subsystem_real_views`) — not just the
  stub dict literal in test_query_algebra.py.
- ~~The full pipeline has never been run end-to-end~~ — `Assessor.ask(text)`
  is a thin wrapper over `session().run_algebra(text, views=self.all_views())`
  and now has real callers: `tools/analysis/ask.py` (CLI entrypoint, run
  successfully against the live project DB) and
  `test_ask_runs_end_to_end_without_stubs` / `test_ask_is_deterministic` in
  the same regression file.

**Verdict on exit criteria ("Truth Layer produces real output from real
project data"): MET.** All 5 views produce real output from real DB-backed
data, the assembled pipeline (NL → router → compiler → AST → executor →
views) has been run end-to-end against both a seeded test DB and the real
project DB, and it has permanent regression coverage proving it stays
that way. Phase 1 is closed — Phase 2 (Router vs Truth Layer comparison)
can start whenever it's prioritized.

Original findings below, kept for the record:

**Two views are orphaned.** `build_system_summary_view()` (SUMMARY) and
`build_subsystem_view()` (SUBSYSTEM) exist in truth/views.py and
truth/subsystem_view.py respectively, but nothing in assessor.py (or
anywhere else) calls them. They have no real caller and no direct unit
test — the only place "SUMMARY"/"SUBSYSTEM" appear in a test is as a
hand-written stub dict literal in test_query_algebra.py, which never
touches the actual builder functions.

**The full pipeline has never been run end-to-end.** `QuerySession.run_algebra(text, views)`
(assessor/query_session.py) is the one place that would chain real NL →
oracle intent → AI compiler → AST → QueryExecutor → real views. It is
correctly implemented but **has zero callers anywhere in the codebase** —
it has never actually been invoked outside of being written. So: the
algebra is alive, three of five views are alive and DB-backed, but nobody
has yet pressed the button that connects them together on real data.

**Smallest next step to actually close Phase 1:** write one script/test that does
```python
views = {
    "STRUCTURE": assessor.structure_view(),
    "STABILITY": assessor.stability_view(),
    "INTEGRITY": assessor.integrity_view(),
}
result = assessor.session().run_algebra("some real question", views)
```
against a real project DB and confirms `algebra_result` contains real,
non-stub data. (DONE - see `tools/analysis/ask.py`, which builds on all
5 views via `Assessor.all_views()` rather than just 3.)


---

## Phase 3 findings (2026-06-16, evidence-only, no code changes)

Trigger: Bart noticed `ask()` has no way to answer "what is the purpose of
this file" and asked whether that's one hole or a symptom of several.
This section is the Phase 3 exercise: real questions run against a real
DB, actual output recorded, gap stated. Nothing below is a guess.

NOTE - environment caveat, not a project bug: the committed
`C_Users_bartl_dev_dj2_tools_analysis.db` reports
`sqlite3.DatabaseError: database disk image is malformed` when read from
this sandbox (PRAGMA integrity_check fails to even run). Likely a
binary-file sync artifact of the Windows-to-sandbox mount, same family as
the sqlite file-handle caveat already on file in CLAUDE.md - not
something to chase from here. Worked around by re-running the real
ingestion pipeline (`EngineRunner.run()`) against the real
`tools/analysis` source tree into a fresh temp DB (1932 real symbol
references / edges) and using that for every probe below. Bart: worth
a `PRAGMA integrity_check` on your end next session to see if the
Windows-side file is actually fine (probable) or actually corrupt.

**Row 1 - "what is the purpose of assessor.py" (and "why does
symbol_noise.py exist", "what is the role of oracle_router" - all three,
verbatim, via `python tools/analysis/ask.py <db> "<question>"`)**
- Question: what is the purpose of assessor.py
- Expected answer: a sentence describing what assessor.py is for.
- Actual answer: intent classified as `general_query` (oracle/api/oracle_router.py
  `_detect_intent`: only `impact_query`/`surface_query`/`general_query`
  exist, matched on substrings "what depends"/"impact",
  "what uses"/"used by", "what does"/"surface" - "purpose", "why", and
  "role" match none of them and fall to the catch-all). Compiler then
  emits the fixed fallback for `general_query`:
  `Combine(Select(STABILITY), Select(INTEGRITY))`, narrated as
  "full diagnostic view of system health." The result is the entire
  project's file list under `stable_contracts` (every file with no
  contract violations - which on this DB is nearly all of them) plus
  empty errors/warnings. All three differently-worded questions about
  three different symbols produced the byte-identical answer, because the
  symbol mentioned in the question is never used past seeding/expansion -
  it has no path into the STABILITY/INTEGRITY views at all.
- Gap: there is no intent category for "what is this / why does this
  exist / what is its role" anywhere in the router, and no view in the
  algebra that could express the answer even if one existed. This isn't
  a tuning problem, it's an absent category.

**Row 2 - responsibility/role classification exists, but is not reachable**
- Question: does the system have any real (non-AI) signal for "what kind
  of work does this file do"?
- Expected answer (going in): probably no, same gap as Row 1.
- Actual answer: it exists and is real. `engine/responsibility_map.py` +
  `Assessor.responsibility_map()` classifies every file into
  ingestion/classification/graph/persistence/reporting by keyword-matching
  file path + callee names, computed from the real DB. Ran it against the
  fresh probe DB:
  `TOTALS: {'classification': 51, 'graph': 59, 'persistence': 21, 'reporting': 46, 'ingestion': 23}`,
  e.g. `assessor/assessor.py -> {classification, graph, reporting}`,
  `ask.py -> {reporting}`. Confirmed by direct call that
  `assessor.all_views()` (the only thing `Assessor.ask()` ever passes to
  the algebra) returns exactly `['STRUCTURE', 'STABILITY', 'INTEGRITY',
  'SUMMARY', 'SUBSYSTEM']` - `responsibility_map` is not in it and has no
  path into `Select()`/`Combine()` at all.
- Gap: not a missing-data problem like Row 1 - a missing-wiring problem,
  same shape as the SUMMARY/SUBSYSTEM orphaning fixed earlier this session.
  The fix pattern already exists in this file (see "RESOLVED 2026-06-16"
  above): register it as a sixth view, the same way summary_view()/
  subsystem_view() were wired in.

**Row 3 - drift signal source**
- Question: what's drifting, and why?
- Expected answer: a list of drift signals with classification/layer.
- Actual answer: called `assessor.stability_view()` directly against the
  fresh probe DB - `drift_signals: []`. Confirmed in code: `assessor.py`
  calls `build_stability_view(self.file_contract_reports(), drift_signals=[])`
  - the empty list is a literal at the call site, not a query result.
  Already flagged in Truth Kernel Board Tier 1 ("drift_signals arg is
  hardcoded [], never populated") - reconfirmed live here, not fixed.
- Gap: the field exists in the view's dataclass and in
  `QueryPlan.VALID_METRICS["STABILITY"]`, so a query against it would
  validate and execute cleanly and silently return nothing real. This is
  the most dangerous shape of gap, since the algebra can't tell you it
  doesn't know - it answers fine, the answer is just always empty.

**Row 4 - how do subsystems relate to each other**
- Question: how does subsystem A relate to subsystem B (conceptually)?
- Expected answer: groupings that track actual architectural boundaries.
- Actual answer: called `assessor.subsystem_view()` against the real
  probe DB. `_module()` in truth/subsystem_view.py does
  `symbol.split(".")[:2]` - when the caller is a bare function name with
  no dots (which is most of this codebase's call graph, since calls are
  recorded as `function_name -> callee_name`, not
  `module.function_name -> callee_name`), that truncation can't truncate,
  so the "subsystem" key IS the function name. Real output:
  `get_llm_context_for_file -> {modules: [str, tools.analysis]}`,
  `_route_expand -> {modules: [add, expand_forward, expand_reverse, frozenset...]}`.
  355 "subsystems" total, for a project with roughly 60-70 real files.
- Gap: the view isn't wrong, it's doing exactly what `_module()` says -
  but `_module()`'s assumption (symbols arrive dotted at module
  granularity) doesn't hold for this graph's actual caller format, so the
  output is a function-level fragmentation, not a subsystem map. Any
  question whose honest answer requires "subsystem" to mean something a
  human would recognize will be wrong, not absent - arguably worse than a
  hole, since it looks like an answer.

**Row 5 - why was this changed / what was the intent of this mutation**
- Question: why does this code mutate `target`?
- Expected answer: a stated intent (e.g. "to cache the resolved path").
- Actual answer: `MutationEvent` (shared/types.py) has exactly
  `line_number`, `target`, `operation`, `raw_expression` - confirmed by
  reading the dataclass directly. No description/intent/reason field
  exists in the type, so there is nothing to recover regardless of view
  or query - this is the same shape as Row 1 (no capture), not Row 3 (capture
  exists but unwired) or Row 4 (capture exists but wrong granularity).
- Gap: absent at the ingestion/type level, same as Row 1.

### Pattern across all 5 rows

Two distinct failure shapes, not five unrelated ones:

1. **Never captured** (Rows 1, 5): no field, anywhere, holds this
   information. Requires new ingestion + a new view + a new intent
   category - real, multi-layer work.
2. **Captured or computable, but not wired into the one algebra `ask()`
   uses, or wired but never populated** (Rows 2, 3, 4): the fix is
   "connect/populate an existing thing," same pattern as the
   SUMMARY/SUBSYSTEM orphaning already fixed this session - cheap relative
   to category 1, and there are at least three of them sitting there
   right now.

Exit criteria for this phase ("evidence only, no guesses") is met: every
row above is a question actually run, or a value actually read, against
real data - not a prediction.

---

## Phase 4 entry (2026-06-17) - Row 1/Row 2 closed: ROLE view added

Per Phase 4's own rule ("one missing capability, one implementation, one
measurable improvement"): Row 2's gap (responsibility/role classification
computed and DB-backed, but not reachable from `ask()`) is now closed,
and as a direct consequence so is the user-facing half of Row 1 (the
"what is the purpose of this file" question class).

What changed (one capability, the smallest version of Row 2's fix
pattern - "connect an existing thing," not new ingestion):
- `truth/views.py`: added `RoleView` dataclass + `build_role_view()`,
  a pure transform wrapping `Assessor.responsibility_map()`'s existing
  DB-backed per-file role classification (ingestion/classification/
  graph/persistence/reporting) into the view shape the algebra expects.
  No new heuristics, no new DB queries - same principle as
  `build_system_summary_view()`/`build_subsystem_view()` when those were
  wired in earlier on 2026-06-16.
- `assessor/assessor.py`: `role_view()` added, `all_views()` now returns
  6 keys (`STRUCTURE, STABILITY, INTEGRITY, SUMMARY, SUBSYSTEM, ROLE`).
- `api/oracle_router.py`: `_detect_intent()` gained a `role_query` branch
  ("purpose"/"why does"/"why is"/"role of"/"what role"/"what kind of");
  `_select_primitives()` maps `role_query -> ["role"]`; `_route_expand()`'s
  `intent_budget` gained a `role_query` entry with zero forward/reverse
  depth (ROLE is a file-level classification, not graph-traversal-
  dependent - zero budget is the honest answer, not a placeholder).
- `truth/query_plan.py` / `truth/query_compiler.py`: ROLE registered as a
  valid Select target with `totals`/`files` metrics, and `role_query`
  compiles to `Select("ROLE", ...)` directly (not a `Combine` fallback).

Measured improvement (Row 1's actual repro, re-run against a seeded DB
after the fix, see `tests/regression/test_role_view_routing.py`):
`assessor.ask("what is the purpose of ingest.py")` now returns
`intent == "role_query"`, a compiled AST containing `Select` (not
`Combine`), and `algebra_result.data` whose `totals`/`files` reflect the
real per-file role classification (e.g. `ingest.py` correctly flagged
`roles.ingestion == True`) - not the byte-identical
`Combine(Select(STABILITY), Select(INTEGRITY))` fallback that all three
Row 1 questions previously produced regardless of which file was named.

What's still open (deliberately not touched here, per the "one truth at
a time" rule):
- Row 1's non-Row-2 remainder: questions whose answer was genuinely never
  captured anywhere (e.g. Row 5's "why was this mutation made" - no
  intent/description field exists on `MutationEvent` to surface even with
  perfect wiring). Out of scope for this entry.
- Row 3 (drift_signals hardcoded `[]`) and Row 4 (subsystem grouping
  fragmenting on undotted symbol names) remain open, same "captured/
  computable but not wired or wired wrong" shape as Row 2 was - good
  candidates for the next Phase 4 pass.

New permanent regression coverage: `tests/regression/test_role_view_routing.py`
(5 tests - ROLE in `all_views()` against real data, `Select("ROLE")`
executing via the algebra, `_detect_intent()` routing purpose/why/role
phrasing to `role_query` specifically, and `ask()` running the full
purpose-question pipeline end-to-end and deterministically), plus the
pre-existing `test_run_algebra_end_to_end.py` updated for the 6-view
contract. Full sweep: 47/47 passing (see REFACTOR OPS BOARD.md
2026-06-17 entry for the complete count breakdown and the two
environment bugs - a locked stale `.pyc` cache and a recurring silent
file-truncation bug in this session's write tooling - found and worked
around while landing this fix).

---

## Phase 4 entry (2026-06-17, later session) - Row 3 closed: drift_signals populated

Per Phase 4's own rule ("one missing capability, one implementation, one
measurable improvement"): Row 3's gap (drift_signals hardcoded `[]` at the
`build_stability_view()` call site - the "most dangerous gap shape" flagged
when this row was first written, since the algebra validates and executes
the query cleanly and just silently returns nothing real) is now closed.

What changed (one capability, "connect an existing thing" - same fix
pattern as Row 2/ROLE, no new heuristics):
- `contracts/contract_drift_classifier.py` already existed with exactly
  the output shape `build_stability_view()` expects
  (`ContractDriftSignal`: `contract_name`/`severity`/`layer`/
  `classification`/`count`) but had zero callers anywhere in the
  codebase - confirmed via grep before touching anything, same
  orphaned-primitive shape as the original SUMMARY/SUBSYSTEM gap.
- `assessor/assessor.py`'s `stability_view()` now calls
  `ContractDriftClassifier().classify(reports)` and passes the real
  result into `build_stability_view()`, replacing the hardcoded `[]`.
- `file_contract_reports()` violations gained a `"layer": "graph"` key
  (the only contract this method currently produces -
  `symbol_reference_integrity` - is not registered in
  `contracts/contract_map.py`'s declared-contract registry, so `"graph"`
  was chosen as the most accurate available layer label for a
  graph-edge-validity check, not pulled from a registry lookup that
  doesn't cover this ad-hoc contract name).
- `ContractDriftClassifier.classify()` hardened with a `_field(v, name,
  default)` shape-safe accessor (dict-or-attribute access, same
  principle as `truth/query_executor.py`'s `get_field()`): the violations
  `file_contract_reports()` actually produces are plain dicts, not the
  attribute-style `ContractViolation` dataclass from the dead
  `contracts/contract_observer.py` path. The classifier now works
  correctly against the real (dict) shape without breaking the dormant
  (attribute) shape if that path is ever revived.

Measured improvement (Row 3's actual repro, re-run after the fix): a
seeded DB with N broken symbol references (`null` caller/callee) now
makes `assessor.stability_view().drift_signals` return
`[{"contract": "symbol_reference_integrity", "class": <transient|
recurring|structural per count>, "count": N, "layer": "graph"}]` instead
of `[]` - confirmed for `count=1` (transient), `count=3` (recurring), and
`count=5` (structural), and confirmed reachable through the full
`ask()`/`all_views()` path, not just the direct method call.

New permanent regression coverage:
`tests/regression/test_drift_signals_wiring.py` (6 tests - stability_view()
returns real, non-empty drift_signals from real seeded violations; all
three classification thresholds; zero violations yields zero signals, not
a wrong-shaped empty result; drift_signals reachable via
`all_views()`/`ask()`; and the `_field()`/`classify()` shape-safety cases
covering both dict and attribute-style violations explicitly). Full sweep
after this work: 7 (discovery/subsystem) + 6 (oracle_router_persistence_
lock) + 4 (run_algebra_end_to_end) + 5 (role_view_routing) + 6 (drift_
signals_wiring, new) + 32 (truth/tests/test_query_algebra, via pytest) =
60/60 passing.

What's still open: Row 1's non-Row-2 remainder and Row 5 (genuinely
never-captured data - no intent/description field exists on
`MutationEvent` to surface even with perfect wiring). Both require new
ingestion, not just wiring, so they're out of scope for this entry per
the "one truth at a time" rule. With Rows 2, 3, and 4 all now closed,
every "captured/computable but not wired or wired wrong" gap from the
original Phase 3 pass is resolved - what remains is exclusively the
"never captured" category.

**Environment note:** hit the same silent-truncation bug yet again while
landing this fix - `contracts/contract_drift_classifier.py` was truncated
mid-comment (missing the entire classification loop and `return signals`
statement) in a way that stayed syntactically valid (`ast.parse()` alone
did not catch it - the function simply fell off the end and would have
implicitly returned `None`), and a subsequent edit to this very doc
truncated mid-word right after "[ ] No" on the very next line. Both
recovered via the mandatory bash heredoc rewrite + full diff verification
in CLAUDE.md, not by retrying `Edit`/`Write`. This is at least the sixth
documented incident this week - continues to support treating it as a
standing environment defect that every edit in this repo must be checked
against, not isolated noise.

## Phase 4 entry (2026-06-17, later session) - single-file ROLE filter scoping closed

Closes a gap that surfaced through real usage rather than the original Phase 3 audit: Bart ran `ask.py` against "what is the purpose of db_probe_toolsold.py" on his Windows machine and got back the full unfiltered ROLE view - every file in the project - instead of just the one named. This is a refinement of Row 1/Row 2 (closed earlier this date): routing purpose-of-file questions to ROLE was correct, but nothing scoped the result down to the single file actually asked about once it got there.

Root cause was three independent bugs stacked together: `Filter` (`truth/query_ast.py`) and `_apply_filter` (`truth/query_executor.py`) were both fully implemented and planner-validated but had zero callers anywhere - same orphaned-primitive shape as Row 3's drift_signals; `QueryExecutor._select()` applied `Filter` to the bare view object before metric projection, so even a constructed `Filter` would have been a no-op against every dataclass-shaped view (every real view is a dataclass, and `_apply_filter`'s `isinstance(dict)`/`isinstance(list)` checks always fell through); and `VALID_FILTER_KEYS` had no `"ROLE"` entry, so a `Filter` on ROLE would have failed planner validation even if one had existed.

Fixed deterministically rather than via the AI compiler: the buggy run had gone through Ollama and still produced `metric=None` despite the prompt explicitly preferring `metric="files"` for one-named-file questions, proving prompt compliance isn't guaranteed even at temperature 0.0. `query_compiler.py` gained `_extract_single_file_filter()` (regex, single `*.py` token) and `_maybe_scope_to_named_file()` (rescopes a bare unfiltered `Select("ROLE")` to `metric="files"` plus a `Filter("file_path", "endswith", name)`, re-validated through the planner), wired into both `compile_query()` and `compile_and_explain()`. New `"endswith"` filter operator added since the question gives a bare filename and `DBOracle` stores full paths.

New permanent regression coverage: `tests/regression/test_single_file_filter_scoping.py` (10 tests - filter extraction unit behavior, rescoping behavior including the cases that must NOT be touched, the executor actually narrowing real DB-backed data, and an end-to-end `ask()` test reproducing Bart's exact question against a real seeded DB). Full sweep after this work: 80/80 passing (48 regression + 32 pytest).

Full detail: `REFACTOR OPS BOARD.md`'s 2026-06-17 (later session) entry; `Truth Kernel Board.md`'s Tier 1 "Role View" SINGLE-FILE FILTER SCOPING note, same date.

**Environment note:** hit the silent-truncation bug again landing this fix - four files truncated in a single edit batch this time (the worst blast radius yet), recovered via the same mandatory bash heredoc rewrite + diff procedure as every prior incident. See REFACTOR OPS BOARD.md's entry for the per-file breakdown.
