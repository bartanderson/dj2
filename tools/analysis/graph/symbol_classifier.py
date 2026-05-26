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
from tools.analysis.representation.semantic_identity import SemanticIdentity

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
    identity: SemanticIdentity,
    project_symbols: set[str] | None = None,
    runtime_bindings: dict[str, str] | None = None,
):
    project_symbols = project_symbols or set()
    runtime_bindings = runtime_bindings or {}

    name = identity.fqdn or identity.surface
    leaf = identity.leaf or name.split(".")[-1]

    contract = load_classification_contract()
    routes = contract.routes
    priority = contract.rules["route_override_priority"]

    STDLIB_HINTS = {
        "pathlib",
        "collections",
        "os",
        "sys",
        "json",
        "typing",
    }

    # 1. ROUTE OVERRIDE
    if identity.identity_type in priority:
        if identity.identity_type == "project":
            return routes["project"]["output"]
        if identity.identity_type == "builtin":
            return routes["builtin"]["output"]
        if identity.identity_type == "stdlib":
            return routes["stdlib"]["output"]
        if identity.identity_type == "runtime":
            return routes["runtime"]["output"]

    # 2. BUILTIN
    import builtins
    if name in dir(builtins):
        return routes["builtin"]["output"]

    # 3. STDLIB
    if leaf in ("Path", "defaultdict", "field") or name in ("Path", "defaultdict", "field"):
        return routes["stdlib"]["output"]

    if "." in name:
        root = name.split(".")[0]
        if root in STDLIB_HINTS:
            return routes["stdlib"]["output"]

    # 4. RUNTIME
    if leaf in runtime_bindings:
        return routes["runtime"]["output"]

    # 5. PROJECT
    if name in project_symbols or leaf in project_symbols:
        return routes["project"]["output"]

    # 6. EXTERNAL
    if "." in name:
        return routes["external"]["output"]

    return "unknown"