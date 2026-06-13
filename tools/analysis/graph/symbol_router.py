# tools/analysis/graph/symbol_router.py

from __future__ import annotations

# ---------------------------------------------------
# ARCHIVED DESIGN NOTES
# ---------------------------------------------------

# CP2.5 SEMANTIC OBSERVATION LAYER (DEPRECATED)

# This layer has been removed from execution.

# It previously handled:
# - lexical decomposition of symbols
# - semantic observation objects
# - pre-routing interpretation hints

# It has been replaced by:

# SEED DISCOVERY LAYER
# - DB-backed symbol lookup
# - no semantic interpretation
# - no identity reconstruction
# - router receives only candidate seeds

# CP2.5 SEMANTIC OBSERVATION LAYER (TRACE-ONLY)
# -------------------------------------------------
# PURPOSE:
#   Deterministic capture of semantic context signals for
#   downstream reconstruction and auditability.
#
# THIS IS THE ONLY DETERMINISTIC AUTHORITY LAYER.
# All routing decisions in this module are final within the pipeline.
#
# BEHAVIORAL GUARANTEE:
#   - MUST NOT influence CP3 routing decisions
#   - MUST NOT mutate control flow
#   - MUST NOT be used for classification
#
# ROLE IN PIPELINE:
#   This layer is a PURE OBSERVATION STAGE that runs in parallel
#   to routing logic.
#
#   It exists to emit structured signals derived from:
#     - lexical form (surface token)
#     - local decomposition (leaf/root/depth)
#     - runtime bindings proximity
#     - project symbol proximity (non-authoritative)
#
#   These signals are consumed ONLY by:
#     - SemanticCandidateBuilder
#     - TraceCollector inspection tooling
#     - future semantic reconstruction layers
#
# DATA NATURE:
#   - All outputs are NON-BINDING hints
#   - All signals are advisory metadata only
#   - No signal is a classification truth
#
# ARCHITECTURAL NOTE:
#   This layer is the first step in semantic identity recovery,
#   but it does NOT participate in identity resolution.
#
# DO NOT:
#   - return values from this layer
#   - branch logic on these signals
#   - treat any probe as ground truth
#
# NOTE: CP2.5 outputs are consumed only by trace + shadow reconstruction. They are not part of identity resolution.


from tools.analysis.graph.project_graph_context import (
    ProjectGraphContext,
)
from tools.analysis.identity.symbol_identity import normalize_symbol
from tools.analysis.graph.route_trace import TraceCollector
from tools.analysis.graph.symbol_resolution_engine import (
    RouteType,
    resolve_symbol_type,
    is_runtime_symbol,
    resolve_runtime_binding,
)

# ============================================================
# PARITY / OBSERVABILITY LAYER (CONTRACT GATE)
# ============================================================
# This function is the ONLY place where:
#   - routing output
#   - semantic identity reconstruction
#   - trace observation
# are compared or combined.
#
# This is NOT a production routing path.
# ============================================================
def route_symbol_shadow(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
    project_prefixes: list[str] | None = None,
):
    tracer = TraceCollector(name)

    # -----------------------------
    # 1. RUN ORIGINAL ROUTER FIRST
    # -----------------------------
    result = _route_symbol_core(
        name=name,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
        project_prefixes=project_prefixes,
        trace_collector=tracer,
    )

    return result, tracer.get()


# ============================================================
# LEGACY ROUTING ENGINE (DO NOT EXTEND LOGIC)
# ============================================================
# This function is the historical routing truth source.
# It must remain deterministic and structurally stable.
# All semantic enhancements belong in identity layer or shadow layer.
# ============================================================
def _route_symbol_core(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
    project_prefixes: list[str] | None = None,
    trace_collector=None,
) -> RouteType:
    assert runtime_bindings is not None, "router received None runtime_bindings"

    print("\n[ROUTER INPUT]")
    print(" name:", name)
    print(" runtime_bindings:", runtime_bindings)
    print(" project_symbols sample:", list(project_symbols or [])[:3])
    print("[RUNTIME CHECK]", is_runtime_symbol(name, runtime_bindings))
    print("[RESOLVE RESULT]", resolve_runtime_binding(name, runtime_bindings))

    result = resolve_symbol_type(
        name=name,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
        project_prefixes=project_prefixes,
    )

    # -------------------------------------------------
    # TRACE LAYER ONLY
    # -------------------------------------------------
    if trace_collector:

        trace_collector.record(
            "resolved_route",
            {
                "name": name,
                "route": result,
            },
        )
    print("[ROUTE DECISION]", result)
    return result

# ============================================================
# PUBLIC ROUTING API (STABLE CONTRACT)
# ============================================================
# This is the ONLY supported entrypoint for routing decisions.
# It must remain a thin wrapper over core routing logic.
# ============================================================
def route_symbol(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
    project_prefixes: list[str] | None = None,
) -> RouteType:

    return _route_symbol_core(
        name=name,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
        project_prefixes=project_prefixes,
        trace_collector=None,
    )

def route_symbol_with_context(
    name: str,
    context: ProjectGraphContext,
) -> RouteType:

    return route_symbol(
        name=name,
        runtime_bindings=context.runtime_bindings,
        project_symbols=context.project_symbols,
    )