# tools/analysis/graph/symbol_classifier.py

from __future__ import annotations

import builtins
import sys

from typing import Literal


# ----------------------------
# BUILTIN NAMES
# ----------------------------
BUILTINS = set(dir(builtins))


# ----------------------------
# STDLIB MODULE PREFIXES
# ----------------------------
STDLIB_PREFIXES = set(sys.stdlib_module_names)


# ----------------------------
# SYMBOL CLASSIFICATION TYPES
# ----------------------------
SymbolClass = Literal[
    "project",
    "builtin",
    "stdlib",
    "runtime",
    "external",
    "external_lib",
    "external_unknown",
]


# ---------------------------------------------------------
# STABLE PROJECT IDENTITY KEY
#
# Converts:
#   ai.ai_boundary.AIBoundary.classify_intent
#
# into:
#   classify_intent
#
# This is now the ONLY allowed project identity rule.
# ---------------------------------------------------------
def project_key(name: str) -> str:
    return name.split(".")[-1]


# ---------------------------------------------------------
# MAIN CLASSIFIER
# ---------------------------------------------------------
def classify_symbol(
    name: str,
    project_prefixes: list[str],
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
) -> SymbolClass:

    # ----------------------------
    # EMPTY SAFETY
    # ----------------------------
    if not name:
        return "external_unknown"

    runtime_bindings = runtime_bindings or {}

    parts = name.split(".")
    root = parts[-1]

    # ---------------------------------------------------------
    # PROJECT ROOT CACHE
    #
    # Example:
    #   ai.ai_boundary.AIBoundary.classify_intent
    #
    # becomes:
    #   classify_intent
    # ---------------------------------------------------------
    project_roots = (
        {project_key(symbol) for symbol in project_symbols}
        if project_symbols
        else set()
    )

    # ----------------------------
    # 1. PROJECT
    #
    # SINGLE AUTHORITATIVE RULE
    # ----------------------------
    if project_key(name) in project_roots:
        return "project"

    # ----------------------------
    # 2. BUILTINS
    # ----------------------------
    if root in BUILTINS:
        return "builtin"

    # ----------------------------
    # 3. STDLIB
    # ----------------------------
    if root in STDLIB_PREFIXES:
        return "stdlib"

    # ----------------------------
    # 4. RUNTIME
    # ----------------------------
    if runtime_bindings.get(name):
        return "runtime"

    if any(p in ("self", "cls", "ctx", "app") for p in parts):
        return "runtime"

    if parts and parts[0] in ("get", "generate"):
        return "runtime"

    # ----------------------------
    # DEBUG FALLTHROUGH
    # ----------------------------
    print(
        "CLASSIFY FALLTHROUGH:",
        {
            "name": name,
            "root": root,
            "project_key": project_key(name),
            "project_match": project_key(name) in project_roots,
            "has_dot": "." in name,
        }
    )

    # ----------------------------
    # 5. EXTERNAL
    # ----------------------------
    if "." in name:
        return "external_lib"

    return "external_unknown"