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
from tools.analysis.representation.symbol_environment import SymbolEnvironment

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
    env: SymbolEnvironment,
):
    leaf = identity.leaf
    fqdn = identity.fqdn or identity.surface

    # ----------------------------
    # 1. runtime wins if explicitly tagged OR bound
    # ----------------------------
    runtime_target = env.resolve_runtime(leaf)

    # ----------------------------
    # 2. PROJECT ALWAYS WINS
    # ----------------------------
    if env.is_project_symbol(fqdn) or env.has_project_leaf(leaf):
        return "project"

    # ----------------------------
    # 3. BUILTIN
    # ----------------------------
    if leaf in BUILTINS:
        return "builtin"

    # ----------------------------
    # 4. RUNTIME (weak signal only)
    # ----------------------------
    if identity.identity_type == "runtime" or runtime_target:
        return "runtime"

    # ----------------------------
    # 5. builtin detection (hard gate)
    # ----------------------------
    import builtins

    if leaf in dir(builtins):
        return "builtin"

    # ----------------------------
    # 6. project match (exact fqdn or leaf match)
    # ----------------------------
    if env.is_project_symbol(fqdn):
        return "project"

    if env.has_project_leaf(leaf):
        return "project"

    # ----------------------------
    # 7. stdlib heuristic (minimal + stable)
    # ----------------------------
    STDLIB_HINTS = {"os", "sys", "pathlib", "json", "typing", "collections"}

    if fqdn.split(".")[0] in STDLIB_HINTS:
        return "stdlib"

    # ----------------------------
    # 8. fallback
    # ----------------------------
    return "unknown"