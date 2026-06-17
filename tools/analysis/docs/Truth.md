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
non-stub data. (DONE — see `tools/analysis/ask.py`, which builds on all
5 views via `Assessor.all_views()` rather than just 3.)
