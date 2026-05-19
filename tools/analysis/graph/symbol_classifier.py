# tools/analysis/graph/symbol_classifier.py

from __future__ import annotations

import builtins
import sys
from typing import Literal, Tuple, Dict, Any

BUILTINS = set(dir(builtins))
STDLIB_PREFIXES = set(sys.stdlib_module_names)

SymbolClass = Literal[
    "project",
    "builtin",
    "stdlib",
    "runtime",
    "external_lib",
    "external_unknown",
    "classification_gap",
    "unresolved_qualified_reference",
]

# ----------------------------
# HELPERS
# ----------------------------
def external_root(name: str) -> str:
    if "." not in name:
        return "unknown"
    return name.split(".")[0]


def project_key(name: str) -> str:
    return name.split(".")[-1]


def module_key2(name: str) -> str:
    parts = name.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]


# ----------------------------
# CORE CLASSIFIER
# ----------------------------
def classify_symbol(
    name: str,
    route: str,
    project_prefixes: list[str],
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
) -> SymbolClass:

    print("CLASSIFY INPUT:", repr(name), "ROUTE:", route)

    runtime_bindings = runtime_bindings or {}
    project_symbols = project_symbols or set()

    if not name:
        return "classification_gap"

    parts = name.split(".")
    root = parts[0]

    leaf = project_key(name)
    module = module_key2(name)

    project_leafs = {project_key(s) for s in project_symbols}
    project_modules = {module_key2(s) for s in project_symbols}

    # ----------------------------
    # ROUTE TRUSTED LAYER
    # ----------------------------
    if route == "project":
        return "project"

    if route in {"builtin", "stdlib", "runtime"}:
        return route  # type: ignore

    # ----------------------------
    # PROJECT MATCHING
    # ----------------------------
    if name in project_symbols:
        return "project"

    if module in project_modules and len(parts) > 1:
        return "project"

    if leaf in project_leafs and project_prefixes:
        for p in project_prefixes:
            if name == p or name.startswith(p + "."):
                return "project"

    # ----------------------------
    # SYSTEM CATEGORIES
    # ----------------------------
    if root in BUILTINS:
        return "builtin"

    if parts[0] in STDLIB_PREFIXES:
        return "stdlib"

    if route == "external":
        if "." in name:
            return f"external_lib.{parts[0]}"  # type: ignore
        return "unresolved_qualified_reference"

    # ----------------------------
    # FALLBACK
    # ----------------------------
    print("⚠ CLASSIFICATION GAP:", name, route)
    return "classification_gap"