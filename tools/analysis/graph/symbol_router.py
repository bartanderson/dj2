# tools/analysis/graph/symbol_router.py

from __future__ import annotations

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

import builtins
import sys

from typing import Literal

from tools.analysis.graph.symbol_identity import (
    project_key,
    module_key,
)

from tools.analysis.graph.project_graph_context import (
    ProjectGraphContext,
)
from tools.analysis.graph.symbol_classifier import normalize_symbol
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder
from tools.analysis.graph.route_trace import (TraceCollector, SemanticObservation, SemanticCandidate)
from tools.analysis.graph.semantic_identity_contract import SemanticIdentityContract
from tools.analysis.representation.symbol_environment import SymbolEnvironment

RouteType = Literal[
    "project",
    "runtime",
    "builtin",
    "stdlib",
    "external",
    "unknown",
]


BUILTINS = set(dir(builtins))
STDLIB_PREFIXES = set(sys.stdlib_module_names)


def is_builtin_symbol(name: str) -> bool:
    if not name:
        return False

    root = name.split(".")[0]
    return root in BUILTINS


def is_stdlib_symbol(name: str) -> bool:
    if not name:
        return False

    root = name.split(".")[0]
    return root in STDLIB_PREFIXES


def is_runtime_symbol(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
) -> bool:

    if not name:
        return False

    runtime_bindings = runtime_bindings or {}

    root = name.split(".")[0]

    # explicit runtime alias root
    if root in runtime_bindings:
        return True

    return False

def is_project_symbol(
    name: str,
    project_symbols: set[str] | None,
) -> bool:

    if not project_symbols:
        return False

    # exact canonical match
    if name in project_symbols:
        return True

    # semantic short-name match
    short_name = name.split(".")[-1]

    for symbol in project_symbols:
        if symbol.split(".")[-1] == short_name:
            print(
                "[PROJECT SHORT MATCH]",
                {
                    "input": name,
                    "matched": symbol,
                }
            )
            return True

    return False

def terminal_symbol(name: str) -> str:
    return name.split(".")[-1]

def canonical_symbol(name: str, project_prefixes: list[str] | None = None) -> str:
    if not name:
        return name
    return name

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

    # -----------------------------
    # 2. SEMANTIC RECONSTRUCTION (POST-HOC ONLY)
    # -----------------------------
    builder = SemanticIdentityBuilder()

    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings=runtime_bindings or {},
        project_symbols=project_symbols or set(),
    )

    identity = builder.build(
        name=name,
        env=env,
    )

    if identity is None:
        identity = type("EmptyIdentity", (), {
            "fqdn": None,
            "confidence": 0.0,
            "surface": name,
            "leaf": name.split(".")[-1],
            "module": None,
        })()

    sico = SemanticIdentityContract(
        surface=name,
        normalized=normalize_symbol(name),
        leaf=name.split(".")[-1],
        root=name.split(".")[0],
        depth=len(name.split(".")),

        routing_result=result,

        identity=(
            {
                "fqdn": identity.fqdn,
                "confidence": identity.confidence,
                "surface": identity.surface,
                "leaf": identity.leaf,
                "module": identity.module,
            }
            if identity is not None else None
        ),

        candidates=[
            {
                "fqdn": identity.fqdn,
                "confidence": identity.confidence,
                "surface": getattr(identity, "surface", name),
                "leaf": getattr(identity, "leaf", name.split(".")[-1]),
                "module": getattr(identity, "module", None),
            }
        ] if identity is not None else [],

        observation=(
            {
                k: getattr(tracer.trace.semantic_observation, k)
                for k in tracer.trace.semantic_observation.__slots__
            }
            if tracer.trace.semantic_observation is not None
            else None
        )
    )
    tracer.trace.semantic_identity = sico



    print("\n[SEMANTIC OBSERVATION]")
    print(tracer.trace.semantic_observation)

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

    if not name:
        print("[CP0 EMPTY INPUT]")
        return "unknown"

    print("\n[CP0 RAW INPUT]", name)

    runtime_bindings = runtime_bindings or {}
    project_symbols = project_symbols or set()
    project_prefixes = project_prefixes or []

    if trace_collector:
    trace_collector.record(
        "runtime_bindings_snapshot",
        list(runtime_bindings.keys())
    )

    # -------------------------
    # Canonicalization stage
    # -------------------------
    original_name = name
    name = canonical_symbol(name, project_prefixes)

    print("\n[NAME TRANSFORM TRACE]")
    print("  original:", repr(original_name))
    print("  after canonical:", repr(name))

    # -------------------------
    # Project symbol preparation
    # -------------------------
    normalized_project_symbols = {
        normalize_symbol(s) for s in project_symbols
    }

    project_leaves = {
        terminal_symbol(normalize_symbol(s))
        for s in project_symbols
    }

    print("\n[PROJECT SYMBOL SAMPLE]")
    print(list(project_symbols)[:5])

    print("\n[PROJECT SYMBOL SAMPLE NORMALIZED]")
    print(list(normalized_project_symbols)[:5])

    print("\n[CP2 CLASSIFY INPUT]", name)

    # -------------------------
    # CP2.5 SEMANTIC OBSERVATION LAYER (TRACE ONLY)
    # THIS LAYER IS OBSERVATIONAL ONLY.
    # It must not influence upstream logic, routing, or classification decisions.
    # -------------------------
    if trace_collector:

        leaf = terminal_symbol(name)
        root = name.split(".")[0]

        observation = SemanticObservation(
            surface=name,
            normalized=normalize_symbol(name),
            leaf=leaf,
            root=root,
            has_dots=("." in name),
            depth=len(name.split(".")),
            runtime_root_hit=(root in (runtime_bindings or {})),
            project_leaf_hit=leaf in project_leaves,
        )

        trace_collector.trace.semantic_observation = observation

        trace_collector.record(
            "cp25_semantic_probe",
            {
                "surface": observation.surface,
                "normalized": observation.normalized,
                "leaf": observation.leaf,
                "root": observation.root,
                "has_dots": observation.has_dots,
                "depth": observation.depth,
                "runtime_root_hit": observation.runtime_root_hit,
                "project_leaf_hit": observation.project_leaf_hit,
            },
        )

    print("\n[CP2.5 SEMANTIC OBSERVATION CAPTURED]")

    # -------------------------
    # Builtin / runtime / stdlib
    # -------------------------
    if is_builtin_symbol(name):
        if trace_collector:
            trace_collector.record("builtin_match", name)
        print("[MATCH]", name, "-> builtin")
        return "builtin"

    if is_runtime_symbol(name, runtime_bindings):
        if trace_collector:
            trace_collector.record("runtime_match", name)
        print("[MATCH]", name, "-> runtime")
        return "runtime"

    if is_stdlib_symbol(name):
        if trace_collector:
            trace_collector.record("stdlib_match", name)
        print("[MATCH]", name, "-> stdlib")
        return "stdlib"

    # -------------------------
    # CP1 Normalization stage
    # -------------------------
    normalized_name = normalize_symbol(name)
    leaf_name = terminal_symbol(normalized_name)

    print("\n[CP1 NORMALIZED]", normalized_name)

    # -------------------------
    # CP3 PROJECT MATCH
    # -------------------------
    print("\n[CP3 SEMANTIC PROJECT MATCH]")
    print("  normalized_name:", normalized_name)
    print("  leaf_name:", leaf_name)

    routing_result: RouteType | None = None

    # 1. exact fqdn match
    if normalized_name in project_symbols:
        print("  MATCH TYPE: fqdn exact")
        routing_result = "project"
        return routing_result

    # 2. leaf semantic match
    leaf_matches = [
        s for s in project_symbols
        if terminal_symbol(normalize_symbol(s)) == leaf_name
    ]

    print("  leaf_matches:", len(leaf_matches))

    if leaf_matches:
        print("  MATCH TYPE: leaf semantic")

        if trace_collector:
            trace_collector.record("project_match_leaf", {
                "input": normalized_name,
                "leaf": leaf_name,
                "candidates": leaf_matches[:5],
            })

        routing_result = "project"
        return routing_result

    # 3. normalized fallback match
    if normalized_name in normalized_project_symbols:
        print("  MATCH TYPE: normalized set fallback")
        routing_result = "project"
        return routing_result

    # -------------------------
    # CP3.1 ROUTE OBSERVATION
    # -------------------------
    if trace_collector:
        trace_collector.record(
            "cp31_route_observation",
            {
                "input": name,
                "normalized": normalized_name,
                "leaf": leaf_name,
                "routing_result": routing_result,
            },
        )

    print("  MISS TYPE: no semantic project match")

    # -------------------------
    # External / fallback
    # -------------------------
    if "." in normalized_name:
        print("[CP3.5 external]", normalized_name)
        if trace_collector:
            trace_collector.record("external_match", name)
        routing_result = "external"
        return routing_result

    print("[CP4 FALLBACK UNKNOWN]", normalized_name)
    if trace_collector:
        trace_collector.record("unknown_match", name)

    routing_result = "unknown"
    return routing_result

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