from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.assessor.assessor import Assessor

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
}

# queries = [
#     Select("STRUCTURE"),
#     Select("STRUCTURE", "hotspots"),
#     Select("STABILITY"),
#     Select("INTEGRITY"),
#     Combine(
#         Select("STRUCTURE"),
#         Select("STABILITY"),
#     ),
# ]

queries = [
    Select("STRUCTURE"),
    Select("STRUCTURE", "hotspots"),

    Select("STABILITY"),
    Select("STABILITY", "stable_contracts"),
    Select("STABILITY", "drift_signals"),

    Select("INTEGRITY"),
    Select("INTEGRITY", "errors"),

    Combine(
        Select("STRUCTURE"),
        Select("STABILITY"),
    ),

    Combine(
        Select("STABILITY", "stable_contracts"),
        Select("INTEGRITY", "errors"),
    ),
]

harness = TruthTestHarness(views)

results = harness.run(queries)
harness.print_report(results)