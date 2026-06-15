# Runs Truth Kernel algebra queries AND integrated QuerySession pipeline

from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.assessor.assessor import Assessor
from tools.analysis.assessor.query_session import QuerySession

from tools.analysis.truth.views import (
    build_structure_view,
    build_stability_view,
    build_integrity_view,
)

from tools.analysis.truth.query_ast import Select, Combine
from tools.analysis.truth.test_harness import TruthTestHarness


oracle = DBOracle("C_Users_bartl_dev_dj2_tools_analysis_engine.db")
assessor = Assessor(oracle)

views = {
    "STRUCTURE": assessor.structure_view(),
    "STABILITY": assessor.stability_view(),
    "INTEGRITY": assessor.integrity_view(),
    "SUMMARY":   assessor.build_snapshot(),
    "SUBSYSTEM": {"subsystems": []},
}

# =========================================================
# SECTION 1 — TRUTH KERNEL ALGEBRA (direct AST queries)
# =========================================================

queries = [
    Select("STRUCTURE"),
    Select("STRUCTURE", "hotspots"),

    Select("STABILITY"),
    Select("STABILITY", "stable_contracts"),
    Select("STABILITY", "drift_signals"),

    Select("INTEGRITY"),
    Select("INTEGRITY", "errors"),

    Combine(Select("STRUCTURE"), Select("STABILITY")),
    Combine(Select("STABILITY", "stable_contracts"), Select("INTEGRITY", "errors")),
    Combine(Select("STABILITY"), Select("INTEGRITY")),
]

harness = TruthTestHarness(views)
results = harness.run(queries)
harness.print_report(results)

# =========================================================
# SECTION 2 — INTEGRATED PIPELINE (NL → oracle → algebra)
# =========================================================

print("\n\n=== INTEGRATED PIPELINE (NL → oracle router → algebra) ===\n")

session = QuerySession(oracle)

nl_queries = [
    "what depends on resolve_analysis_db_path",
    "show ingestion surface",
    "what affects engine snapshot",
    "what depends on build_snapshot",
]

for q in nl_queries:
    print(f"\nQUERY: {q}")
    print("-" * 60)

    result = session.run_algebra(q, views)

    print(f"intent:       {result['intent']}")
    print(f"compiled_ast: {result['compiled_ast']}")
    print(f"explanation:  {result['compiler_explanation']}")
    print(f"seeds:        {result['oracle'].seeds[:5]}")
    print(f"expanded:     {result['oracle'].expanded[:5]}")
    print(f"algebra type: {type(result['algebra_result']).__name__}")

    ar = result["algebra_result"]
    if hasattr(ar, "left") and hasattr(ar, "right"):
        print(f"  left  ({ar.left.view}): {type(ar.left.data).__name__}")
        print(f"  right ({ar.right.view}): {type(ar.right.data).__name__}")
    elif hasattr(ar, "data"):
        print(f"  data: {type(ar.data).__name__}")

print()