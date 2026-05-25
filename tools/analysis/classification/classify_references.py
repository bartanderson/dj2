# tools/analysis/classification/classify_references.py

# MODULE: classification
# OWNED: TRUE
#
# CONTRACT (LOCKED v3 - IR1-aware classification boundary)
#
# PURPOSE
# - Assign bucket labels to SymbolReference edges after IR1 reconstruction exists
#
# RESPONSIBILITY
# - Consume IR1 (SemanticIdentity) or resolved symbol strings
# - Apply deterministic routing via symbol_router.route_symbol
# - Emit bucket classification:
#     project | runtime | builtin | stdlib | external | unknown
#
# STRICT BOUNDARIES
# - Does NOT perform semantic reconstruction (IR1 owns this)
# - Does NOT compute identity resolution
# - Does NOT use SemanticCandidateBuilder or identity inference logic
# - Does NOT mutate IR1 objects
#
# PIPELINE POSITION
# FileAnalysis ingestion pipeline:
#
#   IR1 semantic_identity_reconstruction
#       → produces SemanticIdentity (single resolved representation)
#
#   classify_references (THIS MODULE)
#       → assigns deterministic routing buckets only
#       → does NOT perform identity reconstruction
#       → consumes IR1 + runtime context only
#
#   GraphBuilder
#       → builds structural call/reference graph
#
#   build_evaluation_snapshot
#       → aggregates final analytical view (read-only)
#
# IMPORTANT ARCHITECTURAL NOTE
# - IR1 is authoritative identity source
# - CP2.5 remains observational only
# - routing is deterministic decision layer only
#
# GLOBAL INVARIANTS
# - Classification must remain deterministic
# - No identity reconstruction allowed here
# - No cross-symbol inference
# - Every edge must resolve to exactly one bucket

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