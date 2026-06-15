# th2.py — Truth Harness 2
#
# Simulates the AI compiler slot using hand-crafted NL → AST translations.
# These are real queries a user would ask, manually mapped to valid AST.
# When a real LLM compiler is wired in, it replaces the COMPILED_QUERIES
# table below — the rest of the pipeline is identical.
#
# Run against the engine DB:
#   python th2.py

from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.assessor.assessor import Assessor
from tools.analysis.assessor.query_session import QuerySession
from tools.analysis.truth.query_ast import Select, Combine, Filter
from tools.analysis.truth.query_plan import QueryPlanner, QuerySemanticsRegistry
from tools.analysis.truth.query_executor import QueryExecutor
from tools.analysis.truth.test_harness import TruthTestHarness

# =========================================================
# HAND-CRAFTED NL → AST TABLE
# (simulates AI compiler output)
#
# Format: (natural_language, ast, explanation)
# =========================================================

COMPILED_QUERIES = [

    # --- IMPACT / DEPENDENCY QUERIES ---

    (
        "what depends on route_query",
        Combine(Select("STRUCTURE"), Select("INTEGRITY")),
        "Who calls route_query, and are those callers healthy?",
    ),
    (
        "what depends on build_snapshot",
        Combine(Select("STRUCTURE"), Select("INTEGRITY")),
        "Dependency zone of build_snapshot with integrity check.",
    ),
    (
        "what breaks if resolve_analysis_db_path changes",
        Combine(Select("STRUCTURE"), Select("INTEGRITY")),
        "Impact surface of a path resolution change.",
    ),

    # --- SURFACE / FORWARD QUERIES ---

    (
        "show ingestion surface",
        Combine(Select("STRUCTURE"), Select("STABILITY")),
        "What does ingestion call, and is that surface stable?",
    ),
    (
        "what does the oracle layer call",
        Combine(Select("STRUCTURE"), Select("STABILITY")),
        "Forward projection of oracle layer with stability signal.",
    ),
    (
        "show me the structure view hotspots",
        Select("STRUCTURE", metric="hotspots"),
        "Top structural hubs by degree — builtins excluded.",
    ),

    # --- DIAGNOSTIC QUERIES ---

    (
        "is the system stable",
        Combine(Select("STABILITY"), Select("INTEGRITY")),
        "Full diagnostic: stability signals + integrity errors.",
    ),
    (
        "show integrity errors",
        Select("INTEGRITY", metric="errors"),
        "Direct projection of integrity error list.",
    ),
    (
        "what contracts are stable",
        Select("STABILITY", metric="stable_contracts"),
        "Stable contract list from stability view.",
    ),

    # --- FILTERED QUERIES ---

    (
        "show edges from route_query",
        Select("STRUCTURE", filter=Filter("caller", "==", "route_query")),
        "Filter structure view to edges originating from route_query.",
    ),
    (
        "show hotspots with high degree",
        Select("STRUCTURE", metric="hotspots"),
        "Hotspot ranking — top nodes by degree, builtins excluded.",
    ),

    # --- SUMMARY QUERIES ---

    (
        "how many edges does the system have",
        Select("SUMMARY", metric="edge_count"),
        "Total edge count from summary view.",
    ),
    (
        "how many files were analyzed",
        Select("SUMMARY", metric="file_count"),
        "Total file count from summary view.",
    ),
]


# =========================================================
# RUNNER
# =========================================================

def run(oracle, assessor, session):

    views = {
        "STRUCTURE": assessor.structure_view(),
        "STABILITY": assessor.stability_view(),
        "INTEGRITY": assessor.integrity_view(),
        "SUMMARY":   assessor.build_snapshot(),
        "SUBSYSTEM": {"subsystems": []},
    }

    planner = QueryPlanner(QuerySemanticsRegistry())
    executor = QueryExecutor(views=views)

    print("=" * 70)
    print("TH2 — SIMULATED AI COMPILER PIPELINE")
    print(f"{len(COMPILED_QUERIES)} hand-crafted NL → AST translations")
    print("=" * 70)

    passed = 0
    failed = 0

    for nl, ast, explanation in COMPILED_QUERIES:

        print(f"\nNL:  {nl}")
        print(f"AST: {repr(ast)}")
        print(f"WHY: {explanation}")

        # --- PLANNER VALIDATION ---
        try:
            plan = planner.plan(ast)
        except Exception as e:
            print(f"[FAIL] PLANNER REJECTED: {e}")
            failed += 1
            continue

        # --- EXECUTOR ---
        try:
            result = executor.execute(plan.root)
        except Exception as e:
            print(f"[FAIL] EXECUTOR ERROR: {e}")
            failed += 1
            continue

        # --- ORACLE EXPANSION (seeds + node_reasons) ---
        oracle_result = session.run_query(nl)

        # --- REPORT ---
        print(f"[PASS] intent={oracle_result.intent}  "
              f"seeds={len(oracle_result.seeds)}  "
              f"expanded={len(oracle_result.expanded)}")

        if oracle_result.seeds:
            print(f"       seeds: {oracle_result.seeds[:3]}")

        if oracle_result.node_reasons():
            sample = list(oracle_result.node_reasons().items())[:2]
            for node, reason in sample:
                print(f"       {node}: {reason}")

        passed += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)


if __name__ == "__main__":
    oracle  = DBOracle("C_Users_bartl_dev_dj2_tools_analysis_engine.db")
    assessor = Assessor(oracle)
    session  = QuerySession(oracle)

    run(oracle, assessor, session)