# tools/analysis/graph/symbol_classifier.py

from __future__ import annotations

# MODULE: classifier
# OWNED: TRUE
#
# CONTRACT (LOCKED v1)
# - Owns symbol → bucket classification
# - Must produce deterministic bucket labels
# - Does NOT own snapshot aggregation or metrics

import builtins
import sys
from typing import Literal, Tuple, Dict, Any
from tools.analysis.graph.symbol_identity import normalize_symbol

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


# def normalize_symbol(name: str) -> str:
#     if not name:
#         return name
#     return name.replace("<module>.", "").strip()

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
) -> str:

    name = normalize_symbol(name)
    print("CLASSIFY INPUT:", repr(name), "ROUTE:", route)

    runtime_bindings = runtime_bindings or {}
    project_symbols = {normalize_symbol(s) for s in (project_symbols or set())}

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
    
    # runtime binding override (VERY IMPORTANT)
    if name in runtime_bindings:
        return "runtime"
    # ----------------------------
    # PROJECT MATCHING
    # ----------------------------
    if name in project_symbols:
        return "project"

    if module in project_modules and len(parts) > 1:
        return "project"

    if project_prefixes:
        for p in project_prefixes:
            if name == p or name.startswith(p + "."):
                return "project"

    # ----------------------------
    # SYSTEM CATEGORIES
    # ----------------------------
    if root in BUILTINS:
        return "builtin"

    # stdlib module detection (module-level only)
    if parts[0] in STDLIB_PREFIXES:
        return "stdlib"

    # common stdlib symbol-level aliases
    STD_SYMBOL_HINTS = {
        "Path": "stdlib",
        "defaultdict": "stdlib",
        "field": "stdlib",
    }

    if name in STD_SYMBOL_HINTS:
        return STD_SYMBOL_HINTS[name]  # type: ignore

    if route == "external":
        if "." in name:
            return f"external_lib.{parts[0]}"  # keep, but treat as bucket string, not SymbolClass
        return "unresolved_qualified_reference"

    # ----------------------------
    # FALLBACK
    # ----------------------------
    return "unresolved_qualified_reference"