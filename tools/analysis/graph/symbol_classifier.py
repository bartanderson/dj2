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
from tools.analysis.contracts.classification_contract import load_classification_contract

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
    project_prefixes=None,
    runtime_bindings=None,
    project_symbols=None,
):
    contract = load_classification_contract()
    routes = contract.routes
    priority = contract.rules["route_override_priority"]

    project_prefixes = project_prefixes or []
    runtime_bindings = runtime_bindings or {}
    project_symbols = project_symbols or set()

    STDLIB_HINTS = {
        "pathlib",
        "collections",
        "os",
        "sys",
        "json",
        "typing",
    }

    leaf = name.split(".")[-1]

    # 1. ROUTE OVERRIDE
    if route in priority:
        if route == "project":
            return routes["project"]["output"]
        if route == "builtin":
            return routes["builtin"]["output"]
        if route == "stdlib":
            return routes["stdlib"]["output"]
        if route == "runtime":
            return routes["runtime"]["output"]

    # 2. BUILTIN
    if name in dir(builtins):
        return routes["builtin"]["output"]

    # 3. STDLIB
    if (
        leaf in ("Path", "defaultdict", "field")
        or name in ("Path", "defaultdict", "field")
    ):
        return routes["stdlib"]["output"]

    if "." in name:
        root = name.split(".")[0]
        if root in STDLIB_HINTS:
            return routes["stdlib"]["output"]

    # 4. RUNTIME
    if name in runtime_bindings:
        return routes["runtime"]["output"]

    # 5. PROJECT (FIXED)
    if name in project_symbols or leaf in project_symbols:
        return routes["project"]["output"]

    # 6. EXTERNAL (FIXED COLLAPSE)
    if "." in name:
        return routes["external"]["output"]

    # 7. FALLBACK (FIXED)
    return "unknown"