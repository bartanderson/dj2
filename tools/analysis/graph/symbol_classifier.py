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
# FRAMEWORK ROOT EXTRACTOR
# ---------------------------------------------------------
def external_root(name: str) -> str:
    """
    Extracts top-level external namespace:
    flask.jsonify → flask
    io.BytesIO → io
    """
    if "." not in name:
        return "unknown"
    return name.split(".")[0]

# ---------------------------------------------------------
# STABLE PROJECT IDENTITY KEY
# ---------------------------------------------------------
def project_key(name: str) -> str:
    return name.split(".")[-1]


# ---------------------------------------------------------
# MODULE KEY (FIXED: STABLE TOP-LEVEL MODULE GROUPING)
# ---------------------------------------------------------
def module_key2(name: str) -> str:
    parts = name.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]


# ---------------------------------------------------------
# MAIN CLASSIFIER
# ---------------------------------------------------------
def classify_symbol(
    name: str,
    route: str,
    project_prefixes: list[str],
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
) -> SymbolClass:

    # ROUTE IS ONLY AUTHORITATIVE FOR CONFIRMED SIGNALS
    if route in {"builtin", "runtime", "stdlib"}:
        return route

    # NEVER trust project route without validation
    if route == "project":
        if project_symbols and name in project_symbols:
            return "project"
        
    # ----------------------------
    # EMPTY SAFETY
    # ----------------------------
    if not name:
        return "external_unknown"

    runtime_bindings = runtime_bindings or {}

    print("\n--- MATCH DEBUG ---")
    print("NAME:", name)
    print("PROJECT_SYMBOLS SAMPLE:", list(project_symbols)[:10] if project_symbols else None)
    print("PROJECT_PREFIXES:", project_prefixes)
    print("PROJECT KEY NAME:", project_key(name))
    print("IN PROJECT_SYMBOLS (leaf):",
          project_key(name) in {project_key(s) for s in project_symbols}
          if project_symbols else False)
    print("-------------------\n")

    parts = name.split(".")
    root = parts[0] if "." in name else name

    # ---------------------------------------------------------
    # PROJECT CACHE
    # ---------------------------------------------------------
    project_symbols = project_symbols or set()

    project_leafs = {project_key(s) for s in project_symbols}
    project_modules = {module_key2(s) for s in project_symbols}

    leaf = project_key(name)

    # FIXED: module comparison uses consistent 2-level grouping
    module = module_key2(name)

    # ----------------------------
    # 1. PROJECT (AUTHORITATIVE)
    # ----------------------------
    is_strong_match = name in project_symbols
    is_leaf_match = leaf in project_leafs
    is_module_match = module in project_modules

    # prevent garbage promotion
    if is_strong_match:
        return "project"

    if is_module_match and len(name.split(".")) > 1:
        return "project"

    # leaf match ONLY if prefix resolves to a real project module boundary
    if is_leaf_match and project_prefixes:
        for p in project_prefixes:
            if name == p or name.startswith(p + "."):
                return "project"

    if route == "builtin":
        return "builtin"

    if route == "stdlib":
        return "stdlib"

    if route == "runtime":
        return "runtime"

    if route == "external":
        if "." in name:
            return f"external_lib.{parts[0]}"
        return "external_unknown"

    # ----------------------------
    # 2. DEBUG FALLTHROUGH
    # ----------------------------
    print(
        "CLASSIFY FALLTHROUGH:",
        {
            "name": name,
            "project_key": project_key(name),
            "root": root,
            "parts": parts,
            "has_dot": "." in name,
            "runtime_match": name in runtime_bindings,
            "builtin_match": root in BUILTINS,
            "stdlib_match": parts[0] in STDLIB_PREFIXES,
        }
    )

    # ----------------------------
    # 3. UNROUTED SYMBOL
    # ----------------------------

    print("⚠ UNROUTED SYMBOL:", name, "| route =", route)
    return "external_unknown"