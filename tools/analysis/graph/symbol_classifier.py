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

SymbolClass = Literal[
    "project",
    "builtin",
    "stdlib",
    "runtime",
    "external",
    "external_lib",
    "external_unknown",
]

def _match_project(name: str, project_symbols: set[str]) -> bool:
    if name in project_symbols:
        return True
    if name.split(".")[-1] in project_symbols:
        return True
    return False

def classify_symbol_v2(
    name: str,
    project_prefixes: list[str],
    project_symbols: set[str],
    runtime_bindings: dict[str, str] | None = None,
):
    if not name:
        return SymbolClassification(
            origin="external",
            binding="unknown",
            resolution="unresolved",
        )

    root = name.split(".")[-1]
    parts = name.split(".")

    # ----------------------------
    # ORIGIN (global truth layer)
    # ----------------------------
    if project_symbols and root in project_symbols:
        origin = "project"
    elif root in BUILTINS:
        origin = "builtin"
    elif any(name.startswith(p) for p in project_prefixes):
        origin = "project"
    else:
        origin = "external"

    # ----------------------------
    # BINDING (structural role)
    # ----------------------------
    if root in BUILTINS:
        binding = "builtin"
    elif name.startswith("self.") or name.startswith("cls."):
        binding = "method"
    elif "." in name:
        binding = "attribute"
    elif parts and parts[0] in ("get", "generate"):
        binding = "function"
    else:
        binding = "unknown"

    # ----------------------------
    # RESOLUTION (runtime awareness)
    # ----------------------------
    if runtime_bindings:
        resolution = "dynamic" if name in runtime_bindings else "static"
    else:
        resolution = "static"

    # ----------------------------
    # FINAL STRUCTURE
    # ----------------------------
    return SymbolClassification(
        origin=origin,
        binding=binding,
        resolution=resolution,
    )

#---v2 above, v1 below ----------------

def classify_symbol(
    name: str,
    project_prefixes: list[str],
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
) -> SymbolClass:

    if not name:
        return "external_unknown"

    runtime_bindings = runtime_bindings or {}

    parts = name.split(".")
    root = parts[-1]

    # ----------------------------
    # 1. PROJECT (highest priority)
    # ----------------------------
    if project_symbols and _match_project(name, project_symbols):
        return "project"

    if any(name.startswith(p) for p in project_prefixes):
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
    # 4. RUNTIME (strict match only)
    # ----------------------------
    if name in runtime_bindings:
        return "runtime"

    if any(p in ("self", "cls", "ctx", "app") for p in parts):
        return "runtime"

    if parts and parts[0] in ("get", "generate"):
        return "runtime"

    # debug print
    print(
        "CLASSIFY FALLTHROUGH:",
        {
            "name": name,
            "root": root,
            "project_match": root in project_symbols if project_symbols else None,
            "has_dot": "." in name,
        }
    )

    # ----------------------------
    # 5. EXTERNAL (split cleanly)
    # ----------------------------
    if "." in name:
        return "external_lib"

    return "external_unknown"