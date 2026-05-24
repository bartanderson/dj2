# tools/analysis/graph/symbol_router.py

from __future__ import annotations

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
from tools.analysis.graph.route_trace import TraceCollector
from tools.analysis.graph.semantic_candidate_builder import SemanticCandidateBuilder

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

    parts = name.split(".")
    root = parts[0]

    # explicit runtime alias root
    if root in runtime_bindings:
        return True

    # implicit instance/runtime contexts
    if root in ("self", "cls", "ctx", "app"):
        return True

    # synthetic call-chain artifacts
    if root in ("get", "generate"):
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

def route_symbol_shadow(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
    project_prefixes: list[str] | None = None,
):
    tracer = TraceCollector(name)

    builder = SemanticCandidateBuilder()

    candidates = builder.from_trace(
        name=name,
        alias_map=runtime_bindings,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols or set(),
    )

    tracer.record(
        "semantic_candidates",
        [c.__dict__ for c in candidates]
    )

    result = _route_symbol_core(
        name=name,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
        project_prefixes=project_prefixes,
        trace_collector=tracer,
    )

    return result, tracer.get()

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

    print("\n[PROJECT SYMBOL SAMPLE]")
    print(list(project_symbols)[:5])

    print("\n[PROJECT SYMBOL SAMPLE NORMALIZED]")
    print(list(normalized_project_symbols)[:5])

    print("\n[CP2 CLASSIFY INPUT]", name)
    if trace_collector:
        trace_collector.snapshot_semantic_identity(
        cp2_input=name,
    )

    print("\n[ROUTE DEBUG]", {
        "name": name,
        "project_symbols_count": len(project_symbols),
        "runtime_bindings_count": len(runtime_bindings),
    })

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
    # Normalization stage
    # -------------------------
    normalized_name = normalize_symbol(name)
    print("\n[CP1 NORMALIZED]", normalized_name)

    # -------------------------
    # Project match probe (FULL)
    # -------------------------
    print("\n[CP3 SEMANTIC PROJECT MATCH]")

    leaf_name = normalized_name.split(".")[-1]

    print("  normalized_name:", normalized_name)
    print("  leaf_name:", leaf_name)

    # 1. exact fqdn match
    if normalized_name in project_symbols:
        print("  MATCH TYPE: fqdn exact")
        return "project"

    # 2. leaf match (what you were implicitly relying on)
    leaf_matches = [
        s for s in project_symbols
        if terminal_symbol(normalize_symbol(s)) == leaf_name
    ]

    print("  leaf_matches:", len(leaf_matches))

    if leaf_matches:
        print("  MATCH TYPE: leaf semantic")

        # optional trace hook (safe additive)
        if trace_collector:
            trace_collector.record("project_match_leaf", {
                "input": normalized_name,
                "leaf": leaf_name,
                "candidates": leaf_matches[:5],
            })

        return "project"

    # 3. normalized-set fallback (your existing idea, but now last resort)
    if normalized_name in normalized_project_symbols:
        print("  MATCH TYPE: normalized set fallback")
        return "project"

    print("  MISS TYPE: no semantic project match")

    # -------------------------
    # External / fallback
    # -------------------------
    if "." in normalized_name:
        print("[CP3.5 external]", normalized_name)
        if trace_collector:
            trace_collector.record("external_match", name)
        return "external"

    print("[CP4 FALLBACK UNKNOWN]", normalized_name)
    if trace_collector:
        trace_collector.record("unknown_match", name)
    return "unknown"

def route_symbol(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
    project_prefixes: list[str] | None = None,
) -> RouteType:

    if not name:
        print("[CP0 EMPTY INPUT]")
        return "unknown"

    print("\n[CP0 RAW INPUT]", name)

    runtime_bindings = runtime_bindings or {}
    project_symbols = project_symbols or set()
    project_prefixes = project_prefixes or []

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

    print("\n[PROJECT SYMBOL SAMPLE]")
    print(list(project_symbols)[:5])

    print("\n[PROJECT SYMBOL SAMPLE NORMALIZED]")
    print(list(normalized_project_symbols)[:5])

    print("\n[CP2 CLASSIFY INPUT]", name)

    print("\n[ROUTE DEBUG]", {
        "name": name,
        "project_symbols_count": len(project_symbols),
        "runtime_bindings_count": len(runtime_bindings),
    })

    # -------------------------
    # Builtin / runtime / stdlib
    # -------------------------
    if is_builtin_symbol(name):
        print("[MATCH]", name, "-> builtin")
        return "builtin"

    if is_runtime_symbol(name, runtime_bindings):
        print("[MATCH]", name, "-> runtime")
        return "runtime"

    if is_stdlib_symbol(name):
        print("[MATCH]", name, "-> stdlib")
        return "stdlib"

    # -------------------------
    # Normalization stage
    # -------------------------
    normalized_name = normalize_symbol(name)
    print("\n[CP1 NORMALIZED]", normalized_name)

    # -------------------------
    # Project match probe (FULL)
    # -------------------------
    print("\n[PROJECT MATCH DEEP PROBE]")
    print("  name:", repr(normalized_name))

    exact_match = normalized_name in project_symbols
    normalized_match = normalized_name in normalized_project_symbols

    print("  exact_match:", exact_match)
    print("  normalized_match:", normalized_match)

    if not exact_match and not normalized_match:
        print("  MISS TYPE: no identity match at all")
    elif not exact_match and normalized_match:
        print("  MISS TYPE: normalization mismatch")
    elif exact_match:
        print("  HIT TYPE: exact match")
        print("[CP3 project]", normalized_name)
        return "project"

    # -------------------------
    # External / fallback
    # -------------------------
    if "." in normalized_name:
        print("[CP3.5 external]", normalized_name)
        return "external"

    print("[CP4 FALLBACK UNKNOWN]", normalized_name)
    return "unknown"

def route_symbol_with_context(
    name: str,
    context: ProjectGraphContext,
) -> RouteType:

    return route_symbol(
        name=name,
        runtime_bindings=context.runtime_bindings,
        project_symbols=context.project_symbols,
    )