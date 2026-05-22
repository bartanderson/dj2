# tools/analysis/classification/classify_references.py

# MODULE: classification
# OWNED: TRUE
#
# CONTRACT (LOCKED v1)
# - Classifies SymbolReference edges before graph construction
# - Produces deterministic semantic bucket assignment
# - Must execute before GraphBuilder stage
# - Does NOT construct snapshots
# - Does NOT persist analysis structures
# - Does NOT aggregate metrics
#
# PIPELINE POSITION
# FileAnalysis
#     → classify_references
#     → GraphBuilder
#     → build_evaluation_snapshot
#
# OUTPUT CONTRACT
# SymbolReference.bucket MUST be populated for all graph edges
#
# GLOBAL INVARIANTS
# - Classification must be deterministic
# - Graph edges must never remain semantically unclassified
# - Classification logic must remain independent of persistence

from tools.analysis.graph.project_graph_context import (
    ProjectGraphContext,
)

from tools.analysis.graph.context_classification import (
    classify_symbol_with_context,
)

def classify_references(analysis):

    runtime_bindings = analysis.runtime_bindings

    project_symbols = getattr(
        analysis,
        "project_symbols",
        None,
    ) or set()

    project_prefixes = getattr(
        analysis,
        "project_prefixes",
        [],
    )

    ctx = ProjectGraphContext(
        project_prefixes=project_prefixes,
        project_symbols=project_symbols,
        runtime_bindings=runtime_bindings,
    )

    for ref in analysis.symbol_references:

        print("\n[CLASSIFICATION STAGE]")
        print("callee:", ref.callee)
        print("normalized:", ref.callee.split('.')[-1])
        print(
            "in project symbols:",
            ref.callee.split('.')[-1] in ctx.project_symbols
        )

        result = classify_symbol_with_context(
            ref.callee,
            ctx,
        )

        bucket = (
            result.get("bucket")
            if isinstance(result, dict)
            else str(result or "classification_gap")
        )

        ref.bucket = bucket

    return analysis