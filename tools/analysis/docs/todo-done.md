Thinkgs you notices before:
split.i.surface and cursor.self.oracle.conn showing up as seeds — those are internal dotted accessor symbols that ingestion is capturing but aren't really meaningful query targets. That's the ingestion granularity question — whether to filter those out at the seed level or leave them as structural truth.
[x] RESOLVED 2026-06-16 — unified into oracle/symbol_noise.py
    (is_accessor_chain_noise), applied at both discovery time
    (db_oracle._discover_token) and expansion time (oracle_router._is_valid_symbol).
    cursor.self.oracle.conn-style chains and dotted accessor noise are now
    filtered consistently in both places, no drift between them anymore.
And "what does the oracle layer call" seeded on builtin_symbols.self.oracle, cursor.self.oracle.conn — semantic is finding the oracle layer correctly but through accessor symbols rather than the class itself. The model connected "oracle layer" to those dotted oracle references. Interesting but slightly noisy.


[x] If you want the system to feel real → wire the AI compiler (replace the rule-based stub with an actual LLM call that produces AST)
    DONE — truth/query_compiler.py rewritten (see CLAUDE-EDIT 2026-06-16 header):
    tries local Ollama (llama3.2:3b) first, validates output through
    QueryPlanner, falls back to the original rule-based intent→AST table
    on any failure. No Anthropic API call, local-only.

[x] If you want to push toward Tier 4 → audit remaining direct view calls in assessor that bypass the query algebra
    DUPLICATE — removed 2026-06-17. Same item already tracked in Truth
    Kernel Board.md's Tier 3 entry and REFACTOR OPS BOARD.md's
    ARCHITECTURE SPLIT section; those two stay the source of truth for
    it going forward.

The torch warning is noise from sentence-transformers pulling in PyTorch on
Windows. NOTE (2026-06-17): PYTHONWARNINGS=ignore does NOT suppress it —
confirmed it's emitted via logging.warning() (torch.distributed.elastic's
own glog-style logger), not via warnings.warn(), so the `warnings` module's
env var has no effect on it. Real fix: raise that logger's level directly,
e.g. logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(logging.ERROR)
— now wired into tests/regression/run_all.py.

---

## 2026-06-16 (later same day) — agent readiness gaps closed

[x] RESOLVED — SUMMARY and SUBSYSTEM Truth Layer views were orphaned
    (build_system_summary_view()/build_subsystem_view() existed, zero real
    callers, stub-only test coverage). Wired via new Assessor.summary_view()/
    subsystem_view()/all_views() in assessor/assessor.py.

[x] RESOLVED — QuerySession.run_algebra() had zero callers anywhere in the
    codebase, never run end-to-end. New Assessor.ask(text) wraps
    session().run_algebra(text, views=self.all_views()) and is now called
    from tools/analysis/ask.py (new CLI entrypoint) — run successfully
    against the real project DB.

[x] RESOLVED — deleted oracle/agent.py (GraphOracleAgent) and
    oracle/nl_agent.py (NaturalLanguageGraphAgent): legacy dead-end agents
    that bypassed oracle_router/QuerySession/Truth Layer entirely, with no
    real callers except each other and tests/debug/oracle_compare_harness.py
    (also deleted). Bart's call: "If you have something better they can
    both go" — ask.py/Assessor.ask() is that something better.

[x] RESOLVED — deleted truth/test_harness.py (TruthTestHarness): manual
    print-based runner, pass/fail = absence of exception only, zero real
    callers. Per Bart's stated preference for real assertion-based tests
    over decorative harnesses. Real coverage now lives in
    tests/regression/test_run_algebra_end_to_end.py (4 assert-based tests).

[x] RESOLVED — full regression sweep run in sandbox after the above:
    test_oracle_router_persistence_lock.py (6 tests), test_query_algebra.py
    (32 tests), test_run_algebra_end_to_end.py (4 tests) — 42/42 passing.
    Also caught and fixed an environment bug along the way: a small Edit
    to query_session.py was silently truncated on disk mid-statement
    (10041 of ~10222 bytes); rewritten correctly via direct bash write,
    re-verified with ast.parse() and a full test re-run. Worth treating
    as a standing caveat — verify any file with `wc -c`/`python3 -c
    "import ast; ast.parse(...)"` after edits in this environment if a
    SyntaxError shows up that the Read tool doesn't corroborate.

---

## 2026-06-16 (same day, loose-script cleanup pass)

[x] RESOLVED — audited every loose top-level .py file in tools/analysis/
    plus two test files that surfaced as dependents. Confirmed and
    deleted 7 dead files, all tracing back to one root cause:
    tools/analysis/run_analysis_pipeline.py does not exist anywhere in
    the repo (not even in __pycache__) and never did in this session's
    visibility — it was the orchestration entrypoint an earlier
    architecture iteration was built around, since superseded by
    engine/run_engine.py (ingestion) + ask.py (querying).
    Deleted:
      - run.py (subprocessed into the missing module)
      - debug_run.py (imported it directly)
      - run_parity_test.py (imported 5 more nonexistent
        engine.core.* modules plus engine.parity.ParityChecker; had an
        internal NameError bug and "YOU MUST PROVIDE THESE" placeholder
        comments — never finished. Superseded by the real, working
        engine/parity_contract.py + engine/structural_parity_diff.py.)
      - load_config_profiles.py (expected analysis_profiles.yaml,
        which doesn't exist; zero callers anywhere)
      - tests/core/test_pipeline_smoke.py and
        tests/core/test_reference_extraction_integrity.py (both
        imported run_analysis_pipeline; verified test_db_utils.py and
        graph/project_context.py, which they also imported, are still
        legitimately used by other live tests — only these two test
        files themselves were dead)
      - rewrite plan for routing to classification.md (top-level,
        outside docs/ — a near-duplicate early draft of
        docs/Symbol Classification Stabilization Plan.md; deleted the
        messier duplicate-paste copy, kept the other)

    Kept, dormant but functional (standalone diagnostic CLIs, no
    broken imports, just no current callers): db_probe_toolsold.py,
    db_toolsold_audit.py (heavy overlap with each other — candidates
    to merge if ever revived), debug_gap_report.py.

    Confirmed REFACTOR OPS BOARD.md is unaffected and still accurate —
    its scope is the oracle/Truth-Kernel track specifically, never
    covered these loose scripts, so this isn't a staleness gap in that
    doc.

    Added STATUS NOTE headers (no other content changed) to three
    older planning docs that all assumed the now-dead
    run_analysis_pipeline.py/debug_run.py were the live entrypoints —
    flagging the architecture shift to engine/run_engine.py + ask.py
    rather than rewriting them:
      - docs/Symbol Classification Stabilization Plan.md (otherwise
        still accurate as a historical record — its iteration target
        files mostly exist under the planned names)
      - docs/current predecessors still useful/architectural triage
        protocol.md (methodology still fine, one stale module-ownership
        line)
      - docs/contracts  + visibility.md (exploratory brainstorming,
        effectively superseded by the Truth Kernel/oracle work that's
        since landed; flagged as such rather than deleted, since it's
        Bart's call whether to keep)

---

## 2026-06-17 — ROLE view added (Truth.md Phase 3 Row 1/Row 2 closed)

[x] RESOLVED — "what is the purpose of this file" / "why does X exist" /
    "role of X" questions had no path to an answer: _detect_intent()
    (api/oracle_router.py) had no category for them so they fell to
    general_query and got a content-blind Combine(Select(STABILITY),
    Select(INTEGRITY)) regardless of which file was named, even though
    Assessor.responsibility_map() already had real, DB-backed per-file
    role classification with zero callers wiring it into the algebra
    (all_views() only returned 5 keys, ROLE wasn't one of them).
    Fixed: build_role_view() (truth/views.py) wraps responsibility_map()
    into the view shape the algebra expects; Assessor.role_view() wires
    it into all_views() (now 6 keys); _detect_intent() gained a
    role_query branch; _select_primitives()/the compiler route
    role_query straight to Select("ROLE") (no Combine fallback);
    _route_expand()'s intent_budget gained a role_query entry with zero
    traversal depth (ROLE is file-level, not graph-dependent).

[x] RESOLVED — new permanent regression coverage:
    tests/regression/test_role_view_routing.py (5 tests: ROLE present in
    all_views() against real seeded data, Select("ROLE") executing via
    QueryExecutor, _detect_intent() routing 6 purpose/why/role phrasings
    correctly, ask() routing a real purpose-question end-to-end to the
    ROLE view, and ask() being deterministic on repeat). Updated
    test_run_algebra_end_to_end.py for the new 6-view contract. Full
    sweep after this work: 47/47 passing (5 new + 4 + 6 +
    32-via-pytest).

[x] RESOLVED (environment bug, not a project bug) — a stale/locked
    __pycache__ .pyc for oracle_router.py had a recorded mtime+size that
    coincidentally matched an intermediate pre-fix save of the source,
    so Python's default timestamp-based cache check treated it as valid
    and silently ran old bytecode even after the source was fixed and
    __pycache__ was "cleared" (the file itself was undeletable —
    `rm` → Operation not permitted). Diagnosed by comparing
    inspect.getsource(fn) against the function's actual return value in
    the same process; fixed by touch-ing the source file to force a new
    mtime and invalidate the cache.

[x] RESOLVED (environment bug, not a project bug) — this session's file
    write tooling silently truncated files on disk multiple times (both
    Edit and full-file Write calls) while the Read tool's in-context view
    kept showing the complete, correct content — once landing exactly on
    a comment boundary inside _route_expand() and dropping its final
    return statement with no SyntaxError to flag it. Confirmed Write-tool
    retries are not a reliable fix (one retry reproduced the identical
    truncated byte count). The only confirmed-reliable fix found: a
    direct bash heredoc write/append, always followed by `wc -l -c` +
    (for .py files) `ast.parse()` + a tail diff to confirm the intended
    ending actually landed. See REFACTOR OPS BOARD.md 2026-06-17 entry
    for the full incident log.

---

## 2026-06-17 (later session) — Track A: oracle_router intent budget calibration

[x] RESOLVED — closed the "forward-vs-reverse weighting calibration and
    depth-limit tuning per intent are still open" gap in
    `api/oracle_router.py`'s `_route_expand()` `intent_budget` table:
    - `surface_query` forward_depth 1→2 (a single hop wasn't a real
      "structural zone").
    - `reverse_query` reverse_depth 2→1 — it was sharing impact_query's
      transitive reverse_depth=2 budget, making "what uses X" (direct
      usage) and "what depends on X" (transitive impact) structurally
      identical despite being different questions. `impact_query` itself
      (reverse-only, depth 2) and `general_query` (balanced depth 1/1)
      were already correctly calibrated per the ROUTING LAYER notes and
      left unchanged.
    - removed the dead `two_hop` key from every `intent_budget` entry —
      grep-confirmed it was never read anywhere in `_route_expand()`,
      same "looks like a feature, isn't" shape as the deleted
      `_apply_intent_weights` stub.
    New regression coverage: `tests/regression/test_intent_budget_calibration.py`
    (5 tests — reverse_query stops at 1 hop where impact_query still
    reaches 2, surface_query now reaches a 2-hop forward node,
    general_query stays balanced at 1/1, two_hop key absent). Full sweep
    after this work: 52/52 passing (47 prior + 5 new).

    Also confirmed and documented an architectural fact while doing this:
    `_route_expand()`'s output only feeds the explainability trace
    (`seed_explanation`/`node_reasons`/the persisted `query_sessions`
    row) — `QuerySession.run_algebra()` answers from
    `Assessor.all_views()` (the full graph snapshot) independent of the
    expansion budget. So this calibration improves trace quality, not
    algebra answer content yet — see REFACTOR OPS BOARD.md NEXT STEPS
    Track A for the full note.

    Hit one instance of the silent file-truncation bug again while
    writing the new test file (Write tool reported success, content
    cut off mid-token on disk) — fixed via the now-standard bash heredoc
    rewrite + `wc -l -c` + `ast.parse()` verification, per the procedure
    documented just above.

[x] 2026-06-17 — fixed the real Windows test_role_view_routing failure
    (`AttributeError: 'list' object has no attribute 'totals'`) by fixing
    root cause, not symptom: a consumer assumed QueryResult.data always
    had one fixed shape, when Select("ROLE", metric="files") is an
    equally valid choice the real local Ollama compiler made on Bart's
    machine for a one-file question. Per Bart's "fix it thoroughly, full
    mapping, handle all existing cases" direction, audited the whole
    Select/Combine shape contract (6 views, ~15 metrics):
    - added `get_field()` (truth/query_executor.py) — the one correct
      way to read a QueryResult regardless of which valid metric came
      back.
    - found + fixed a real inconsistency: SUBSYSTEM was the only one of
      6 views returning a bare dict instead of a dataclass for its full
      view. Added `SubsystemView` (truth/views.py), updated
      `build_subsystem_view()` to return it.
    - removed dead+wrong `QuerySemanticsRegistry.validate_metric()` (zero
      callers, checked the wrong dict — same shape as the deleted
      `two_hop` key / `_apply_intent_weights` stub).
    - made the AI-prompt spec (`query_compiler.py`'s `_ALGEBRA_SPEC`)
      generate from the registry instead of hand-duplicating it, closing
      a drift risk between what the model is told and what's enforced.
    - fixed the two consumers that broke (`test_role_view_routing.py`,
      `test_run_algebra_end_to_end.py`'s SUBSYSTEM bracket access) to
      handle real shapes instead of assuming one.
    - new suite: `tests/regression/test_query_result_shape_contract.py`
      (4 tests, the actual full-mapping proof).
    Full sweep: 57/57 passing (25 regression + 32 pytest).
    Full detail: REFACTOR OPS BOARD.md's 2026-06-17 "algebra shape
    contract audit" entry, Truth Kernel Board.md's Tier 1 "QueryResult
    shape contract" entry.

    Hit the silent-truncation bug on every single Edit made during this
    work (5 source files + this doc) — all recovered via bash heredoc
    rewrite, verified via `wc -l -c` + `ast.parse()` + tail inspection
    against the real on-disk bytes, per the mandatory procedure above.

[x] 2026-06-17 (later) — fixed a real failure Bart hit running the suite on
    his Windows machine (the only place the live Ollama compiler is
    actually reachable): `test_ask_role_question_is_deterministic` failed
    on `first["compiled_ast"] == second["compiled_ast"]` — two calls of
    the same question compiled to two different, both-valid ASTs
    (`Select("ROLE")` vs `Select("ROLE", metric="files")` — same kind of
    "more than one correct choice" shape as the shape-contract bug fixed
    just above, one level up: an LLM compiler at temperature=0.0 isn't
    guaranteed to pick the same valid AST twice across separate calls).
    Fixed the test itself, not the compiler — rewrote it to compare
    answer content via `get_field()` instead of raw AST text, matching
    the principle already applied to `test_ask_purpose_question_routes_
    to_role_view`. No code change needed elsewhere.
    Full sweep after fix (sandbox, rule-based-fallback path): 57/57.
    Full detail: REFACTOR OPS BOARD.md's 2026-06-17 "determinism test
    fix" entry, Truth Kernel Board.md's Tier 1 "Determinism test
    invariant" entry.

    Hit the silent-truncation bug again on this exact test file edit —
    recovered via the same bash heredoc + `head`/`tail` reconstruction
    pattern. Per Bart's request, the truncation bug itself is now queued
    as its own discussion/investigation track rather than just being
    re-fixed silently each time.

[x] 2026-06-17 (later still) — Track A (DB-backed symbol discovery API)
    completed, then used immediately to fix Track B item 2 (SUBSYSTEM
    fragmentation), per Bart's explicit direction ("Track A, then also
    fix subsystem fragmentation").
    - Added list_symbols/find_symbols/find_files/find_modules/
      symbol_module_map to oracle/db_oracle.py — all DBReader-only,
      single SELECT against symbols/files tables, no engine/in-memory
      fallback. Distinct from discover_seed_symbols (NL-query relevance
      scoring for route_query) — these are general-purpose lookup
      primitives.
    - Closed "seed discipline enforcement": confirmed production seeding
      was already 100% DB-backed (QuerySession.run_query() already
      passes self.oracle.discover_seed_symbols), then removed the dead
      _seed_symbols() decoy wrapper in api/oracle_router.py (defined,
      never actually called — same "looks like a feature, isn't" shape
      as _apply_intent_weights and the deleted legacy agent files).
    - Fixed SUBSYSTEM fragmentation (truth/subsystem_view.py): _module()
      now takes an optional module_map (symbol_module_map() — real
      `symbols` table declarations), preferring real DB-backed module
      resolution over the old dotted-name-split heuristic, which assumed
      module-qualified names this codebase's real symbols mostly don't
      have. Old heuristic kept as fallback for symbols absent from the
      map. assessor.subsystem_view() wired to pass the map by default.
    - New suite: tests/regression/test_discovery_api_and_subsystem_fix.py
      (7 tests — 5 for the discovery methods, 2 for the subsystem fix
      including a direct with-vs-without-module_map comparison).
    Full sweep: 64/64 passing (57 prior + 7 new).
    Full detail: REFACTOR OPS BOARD.md's 2026-06-17 "Track A completed,
    Track B item 2 closed" entry, Truth Kernel Board.md's Tier 1
    "Subsystem View" GROUPING QUALITY FIXED note.

    Hit the silent-truncation bug a fifth time, on the Edit call that
    added the dotted-name-fallback test case to the new regression file
    — same shape as every prior incident (no error, plausible in-context
    view, on-disk byte count provably unchanged via wc -c before/after).
    Recovered via the mandatory bash heredoc rewrite + diff procedure,
    not by retrying Edit.
