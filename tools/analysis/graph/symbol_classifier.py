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
    leaf = identity.leaf
    fqdn = identity.fqdn or identity.surface

    # ----------------------------
    # 1. runtime wins if explicitly tagged OR bound
    # ----------------------------
    if identity.identity_type == "runtime" or leaf in runtime_bindings:
        return "runtime"

    # ----------------------------
    # 2. builtin detection (hard gate)
    # ----------------------------
    import builtins

    if leaf in dir(builtins):
        return "builtin"

    # ----------------------------
    # 3. project match (exact fqdn or leaf match)
    # ----------------------------
    if fqdn in project_symbols:
        return "project"

    if any(sym.split(".")[-1] == leaf for sym in project_symbols):
        return "project"

    # ----------------------------
    # 4. stdlib heuristic (minimal + stable)
    # ----------------------------
    STDLIB_HINTS = {"os", "sys", "pathlib", "json", "typing", "collections"}

    if fqdn.split(".")[0] in STDLIB_HINTS:
        return "stdlib"

    # ----------------------------
    # 5. fallback
    # ----------------------------
    return "unknown"