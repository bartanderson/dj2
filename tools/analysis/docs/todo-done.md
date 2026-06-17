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
