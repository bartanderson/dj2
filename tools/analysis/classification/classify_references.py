# tools/analysis/classification/classify_references.py

# MODULE: classification
# OWNED: TRUE
#
# CONTRACT (LOCKED v2 - aligned with semantic reconstruction phase)
#
# - Classifies SymbolReference edges before graph construction
# - Uses deterministic routing via symbol_router.route_symbol (legacy routing stage)
# - Produces bucket assignment:
#     project | runtime | builtin | stdlib | external | unknown
# - Does NOT perform semantic reconstruction (shadow pipeline owns that responsibility)
# - Does NOT depend on semantic_candidate_builder
# - Does NOT mutate persistence layer structures beyond SymbolReference.bucket
#
# PIPELINE POSITION
# FileAnalysis
#     → classify_references (routing only)
#     → GraphBuilder
#     → build_evaluation_snapshot
#
# IMPORTANT ARCHITECTURAL NOTE
# - Semantic reconstruction is handled in route_symbol_shadow()
# - CP2.5 probe is observational only and must not influence classification
# - This module must remain purely deterministic and non-semantic
#
# GLOBAL INVARIANTS
# - Classification must remain deterministic
# - No semantic identity reconstruction in this stage
# - Graph edges must always be assigned a bucket

from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.symbol_router import route_symbol
from tools.analysis.graph.symbol_router import route_symbol_shadow


def classify_references(analysis, project_prefixes):
    ctx = ProjectGraphContext(
        project_prefixes=project_prefixes,
        project_symbols=getattr(analysis, "project_symbols", None) or set(),
        runtime_bindings=getattr(analysis, "runtime_bindings", {}) or {},
    )

    for ref in analysis.symbol_references:

        # ---------------------------------------
        # 1. PRODUCTION ROUTING (UNCHANGED)
        # ---------------------------------------
        route = route_symbol(
            name=ref.callee,
            runtime_bindings=analysis.runtime_bindings,
            project_symbols=analysis.project_symbols,
        )

        ref.bucket = route

        # ---------------------------------------
        # 2. SHADOW ROUTING (OBSERVABILITY ONLY)
        # ---------------------------------------
        shadow_route, trace = route_symbol_shadow(
            name=ref.callee,
            runtime_bindings=analysis.runtime_bindings,
            project_symbols=analysis.project_symbols,
        )

        # attach trace if your analysis supports it
        if hasattr(ref, "trace"):
            ref.trace = trace

        # ---------------------------------------
        # 3. OPTIONAL DIVERGENCE LOG (SAFE)
        # ---------------------------------------
        if shadow_route != route:
            print("\n[ROUTE DIVERGENCE]")
            print("  symbol:", ref.callee)
            print("  prod:", route)
            print("  shadow:", shadow_route)

    return analysis