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