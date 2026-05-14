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
# LANGUAGE-LEVEL RUNTIME RECEIVERS
# ----------------------------
RUNTIME_PREFIXES = (
    "self.",
    "cls.",
)


SymbolClass = Literal[
    "project",
    "builtin",
    "stdlib",
    "runtime",
    "external",
]


def classify_symbol(
    name: str,
    project_prefixes: list[str],
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
) -> SymbolClass:

    if not name:
        return "external"

    runtime_bindings = runtime_bindings or {}

    parts = name.split(".")
    root = parts[-1]

    # ----------------------------
    # 0. LOCAL PROJECT SYMBOLS
    # AST-derived semantic truth
    # ----------------------------

    if project_symbols and root in project_symbols:
        return "project"

    # ----------------------------
    # 1. BUILTINS
    # ----------------------------
    if root in BUILTINS:
        return "builtin"


    # ----------------------------
    # 2. LANGUAGE RUNTIME RECEIVERS
    # ----------------------------
    
    if any(p in ("self", "ctx", "app") for p in parts):
        return "runtime" # context-bound object access
        
    if parts[0] in ("get", "generate"):
        return "runtime" # runtime dispatch entry

    # ----------------------------
    # 3. DYNAMIC RUNTIME BINDINGS
    # ----------------------------
    if any(part in runtime_bindings for part in parts):
        return "runtime"

    # ----------------------------
    # 4. STDLIB
    # ----------------------------
    if parts[0] in STDLIB_PREFIXES:
        return "stdlib"

    # ----------------------------
    # 5. PROJECT
    # ----------------------------
    if any(name.startswith(prefix) for prefix in project_prefixes):
        return "project"

    # ----------------------------
    # 6. EVERYTHING ELSE
    # ----------------------------
    # print("EXTERNAL TRACE:", {
    #     "name": name,
    #     "root": name.split(".")[0],
    # })
    return "external"