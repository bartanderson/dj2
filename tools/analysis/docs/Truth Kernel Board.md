TRUTH KERNEL BOARD (FINALIZED STRUCTURE)

PURPOSE
Deterministic introspection governance layer for the system.

Nothing enters the Truth Kernel until it is:

1. Testable
2. Deterministic
3. Grounded in existing system truth

The Truth Kernel is not allowed to invent information.

---

## TIER 0 — QUERY INTERFACE HYPOTHESES (AI COMPILER SURFACE)

Purpose:
Define how natural language is mapped into Query Algebra.
Truth Kernel Spec = authoritative document

Promotion Rule:
Must have executable tests.

---

## TIER 1 — VERIFIED (FACT)

All components that are proven correct via execution.

[X] Query AST
[X] Query Planner
[X] Query Executor
[X] Structure View — wired to real DB data (assessor.structure_view(), builtin-filtered)
[X] Stability View — wired to real contract reports (assessor.stability_view()).
    DRIFT_SIGNALS POPULATED 2026-06-17: closed Truth.md Phase 3 Row 3 -
    drift_signals was hardcoded [] at the build_stability_view() call site
    (validated and executed cleanly, silently always empty - the most
    dangerous gap shape, since nothing signals it's missing). ContractDriftClassifier
    (contracts/contract_drift_classifier.py) already existed with the exact
    output shape the view expects (contract_name/classification/count/layer)
    but had zero callers anywhere - same orphaned-primitive shape as
    Summary/Subsystem/Role View below. assessor.stability_view() now calls
    ContractDriftClassifier().classify(reports) and passes the real result
    in. Also hardened ContractDriftClassifier.classify() with a _field()
    shape-safe accessor (dict or attribute access, same principle as
    get_field() below) so it works against both the live dict-shaped
    violations file_contract_reports() produces and the dormant
    attribute-shaped ContractViolation type from contract_observer.py.
    Proven by tests/regression/test_drift_signals_wiring.py (6 tests:
    stability_view() returns non-empty signals from real seeded violations,
    all three classification thresholds transient/recurring/structural,
    zero violations yields zero signals, drift_signals reachable via
    ask()/all_views(), and the _field()/classify() shape-safety cases).
[X] Integrity View — wired to real validation data (assessor.integrity_view())
[X] Summary View — RE-UPGRADED 2026-06-16 (later same day): wired to real
    data via assessor.summary_view() (reduced_snapshot() + bucket_summary()
    + file_count()), with direct test coverage in
    tests/regression/test_run_algebra_end_to_end.py (test_all_views_real_data,
    test_algebra_select_summary_and_subsystem_real_views) — not just the
    stub literal in test_query_algebra.py.
[X] Subsystem View — RE-UPGRADED 2026-06-16: wired via assessor.subsystem_view()
    (real graph snapshot), same direct test coverage as Summary View above.
    GROUPING QUALITY FIXED 2026-06-17: closed Truth.md Phase 3 Row 4 -
    _module() (truth/subsystem_view.py) assumed dotted module-qualified
    symbol names, but this codebase's real symbols are mostly bare names,
    so SUBSYSTEM fragmented into ~355 near-singleton groups. Added
    DBOracle.symbol_module_map() (real `symbols` table declarations,
    file_path's containing directory as the module) and threaded it
    through as an optional module_map param, preferring real DB-backed
    resolution and falling back to the old dotted-name heuristic only
    for symbols absent from the map. assessor.subsystem_view() now passes
    this map in by default. Proven by
    tests/regression/test_discovery_api_and_subsystem_fix.py (7 tests,
    includes a direct with-vs-without-module_map comparison on the same
    fixture data). See REFACTOR OPS BOARD.md's 2026-06-17 "Track A
    completed, Track B item 2 closed" entry for full detail.
[X] Role View — ADDED 2026-06-17: build_role_view() (truth/views.py) wraps
    Assessor.responsibility_map()'s existing DB-backed per-file role
    classification (ingestion/classification/graph/persistence/reporting);
    wired via assessor.role_view(), now the 6th key in all_views(). Closes
    Truth.md Phase 3 Row 2 (computed but unreachable) and the user-facing
    half of Row 1 (purpose-of-file questions had no intent category or
    view to land on). Direct test coverage in
    tests/regression/test_role_view_routing.py (5 tests: real-data view
    construction, Select("ROLE") execution, _detect_intent() routing,
    and ask() end-to-end + deterministic).
    SINGLE-FILE FILTER SCOPING ADDED 2026-06-17 (later session): closed a
    real bug Bart hit on his Windows machine - "what is the purpose of
    db_probe_toolsold.py" returned the full unfiltered ROLE view (every
    file), not just the named one. Three stacked causes, all fixed:
    Filter (query_ast.py) and _apply_filter (query_executor.py) were both
    real and tested but had zero callers anywhere (same orphaned-primitive
    shape as drift_signals above); _select() applied Filter to the bare
    view object BEFORE metric projection, so even a constructed Filter
    would have been a no-op against every dataclass-shaped view (fixed:
    filter now applies AFTER projection); VALID_FILTER_KEYS had no "ROLE"
    entry (added: {"file_path"}). Fix itself is deterministic regex +
    planner-revalidated Filter (query_compiler.py's
    _extract_single_file_filter()/_maybe_scope_to_named_file()), not
    AI-compiler-dependent - the buggy run had gone through Ollama and
    still produced metric=None despite the prompt preferring metric="files"
    for one-named-file questions. New "endswith" filter operator added
    (bare filename vs. full stored path). Proven by
    tests/regression/test_single_file_filter_scoping.py (10 tests). See
    REFACTOR OPS BOARD.md's 2026-06-17 (later session) entry for full
    detail.
[X] QueryResult shape contract — CLOSED 2026-06-17: audited and locked the
    full Select/Combine shape contract across all 6 views / ~15 metrics
    after a real Windows-only AttributeError (consumer assumed
    QueryResult.data always had one fixed shape; metric="files" vs
    metric=None are both legitimate, registry-valid choices). Added
    get_field() (truth/query_executor.py) as the one correct way to read
    a QueryResult regardless of which valid metric was selected; fixed
    SUBSYSTEM to return a SubsystemView dataclass instead of a bare dict
    (was the one view of 6 with a different full-view shape); removed a
    dead+wrong validate_metric() (zero callers, checked the wrong dict).
    Proven, not just patched: tests/regression/test_query_result_shape_
    contract.py asserts get_field() agrees with direct metric-selection
    for every (view, metric) pair against real DB-backed data. See
    REFACTOR OPS BOARD.md's 2026-06-17 "algebra shape contract audit"
    entry for full detail.
[X] Determinism test invariant — CLOSED 2026-06-17 (later): Bart hit a
    real failure on his Windows machine (the only place the live Ollama
    compiler is reachable) — test_ask_role_question_is_deterministic
    asserted byte-identical compiled_ast across two calls of the same
    question, but Select("ROLE") and Select("ROLE", metric="files") are
    both valid for a one-file question and an LLM compiler at
    temperature=0.0 isn't guaranteed to pick the same one twice. Same bug
    class as the shape-contract entry above, one level up. Fixed the test
    to compare answer content via get_field() instead of raw AST text —
    "same question -> same answer", not "same question -> same AST
    string". See REFACTOR OPS BOARD.md's 2026-06-17 "determinism test
    fix" entry for full detail.

Criteria:

Passes Truth Harness
No structural contradictions
Deterministic outputs

CORRECTION 2026-06-16 (morning): Summary View and Subsystem View were marked [X] but
on inspection of the actual code, only the algebra plumbing around them is
tested (via hardcoded stub dicts) — the real build_* functions that would
produce them from project data have never been called or tested directly.
Downgraded to [!] (needs decision / needs a real test) rather than removed,
since the code itself looks correct, it's just unexercised.

RE-CORRECTION 2026-06-16 (later same day): both wired up for real via
Assessor.summary_view()/subsystem_view(), both have real test coverage
against real seeded data (not stubs). Re-upgraded to [X] above. Note:
"Passes Truth Harness" in the Criteria line above is now stale phrasing —
truth/test_harness.py (TruthTestHarness) was a non-asserting print-only
runner with zero real callers and has been deleted; the real verification
path is the assert-based regression suite under tests/regression/.

---

## TIER 2 — USEFUL (SIGNAL QUALITY)

Components that are correct but being evaluated for practical value.

[x] Hotspot ranking quality (print/len/getattr dominance issue)
    RESOLVED — confirmed in truth/views.py: build_structure_view() takes a
    builtin_symbols set and excludes them from the degree-count ranking
    before computing hotspots (edges/adjacency stay intact as structural
    truth; only the ranked hotspot list is filtered). assessor.structure_view()
    already passes self.oracle.builtin_symbols() — the same DB-authoritative
    set unified this session in oracle/symbol_noise.py — so builtins no
    longer dominate hotspot rankings.
[ ] Stability signal usefulness
[ ] Integrity signal usefulness
[ ] Subsystem interpretability — NOTE 2026-06-17: the underlying
    grouping-quality bug (see Tier 1 Subsystem View entry above) is now
    fixed, so SUBSYSTEM groups by real module instead of fragmenting into
    singletons. This item is still open because that's a correctness
    fix, not yet an evaluation against real debugging/onboarding tasks -
    same distinction as the Role classification interpretability item
    below.
[ ] Role classification interpretability — NEW 2026-06-17: role view is
    wired and tested for correctness (keyword-match classification ==
    what responsibility_map() computes), but not yet evaluated against
    real debugging/onboarding tasks the way the other Tier 2 items are
    framed. Same "correct but unevaluated for practical value" shape as
    Subsystem interpretability above.

Criteria:

Produces correct outputs
Needs evaluation against real debugging tasks
May be mathematically correct but semantically noisy

---

## TIER 3 — AUTHORITATIVE (SYSTEM REPLACEMENT)

Components eligible to replace legacy paths.

[ ] Assessor fully uses Truth Layer exclusively
[ ] Oracle fully routed through Truth Layer
[ ] Engine introspection migrated
[ ] Legacy dual-path removed

Criteria:

No parallel systems exist
Only Truth Layer is used for introspection

---

## TIER 4 — KERNEL (CLOSED WORLD COMPLETE)

[ ] All introspection flows through Truth Query Algebra
[ ] No alternate query systems exist
[ ] No ad-hoc graph inspection paths remain
[ ] Query language is frozen (no expansion allowed)

Status: FUTURE STATE

---

## CURRENT KNOWN ISSUE — RESOLVED 2026-06-16

Was: structure hotspots dominated by Python builtins (print, len, getattr).
Now: build_structure_view() excludes the DB-authoritative builtin set from
hotspot ranking (see Tier 2 above). The SUMMARY/SUBSYSTEM verification gap
flagged here earlier the same day is also resolved — see Tier 1 above.
No open known issue at this tier as of 2026-06-16.

UPDATE 2026-06-17: Truth.md Phase 3 Row 2 (responsibility/role
classification computed but unreachable from ask()) is resolved — see the
Role View entry under Tier 1 above. Row 4 (subsystem grouping fragmenting
on undotted symbol names) is also resolved — see the Subsystem View entry
under Tier 1 above. Row 3 (drift_signals hardcoded []) is now ALSO
resolved as of this same date (later session) — see the Stability View
entry under Tier 1 above. All four Phase 3 rows from the original pass
that were the "captured/computable but not wired or wired wrong" shape
(Rows 2, 3, 4) are now closed; Row 1's remainder and Row 5 (genuinely
never-captured data, e.g. no intent/description field on MutationEvent)
remain open and require new ingestion, not just wiring.

---

## CORE PRINCIPLE

AI role:

1.Interpret request
2.Map to Query Algebra (only allowed primitives)
3.Execute deterministically (via executor)
4.Narrate result (no invention) but based on intent
- summarized human response
- direct AI context

Truth Kernel remains deterministic.
