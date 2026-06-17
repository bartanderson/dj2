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

[ ] If you want to push toward Tier 4 → audit remaining direct view calls in assessor that bypass the query algebra
    Still open.

The torch warning is just noise from sentence-transformers pulling in PyTorch on Windows — harmless, but worth noting you could suppress it with PYTHONWARNINGS=ignore

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
