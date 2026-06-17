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
[X] Stability View — wired to real contract reports (assessor.stability_view()); NOTE: drift_signals arg is hardcoded [] at the call site, never populated
[X] Integrity View — wired to real validation data (assessor.integrity_view())
[X] Summary View — RE-UPGRADED 2026-06-16 (later same day): wired to real
    data via assessor.summary_view() (reduced_snapshot() + bucket_summary()
    + file_count()), with direct test coverage in
    tests/regression/test_run_algebra_end_to_end.py (test_all_views_real_data,
    test_algebra_select_summary_and_subsystem_real_views) — not just the
    stub literal in test_query_algebra.py.
[X] Subsystem View — RE-UPGRADED 2026-06-16: wired via assessor.subsystem_view()
    (real graph snapshot), same direct test coverage as Summary View above.

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
[ ] Subsystem interpretability

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
