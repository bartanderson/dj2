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
    if (
        name in project_symbols
        or leaf in project_leafs
        or module in project_modules
    ):
        return "project"

    # ----------------------------
    # 2. BUILTINS
    # ----------------------------
    if root in BUILTINS:
        return "builtin"

    # ----------------------------
    # 3. STDLIB
    # ----------------------------
    if parts[0] in STDLIB_PREFIXES:
        return "stdlib"

    # ----------------------------
    # 4. RUNTIME
    # ----------------------------
    if name in runtime_bindings:
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
    # 5. External root tagging (simple heuristic grouping)
    # ----------------------------

    if "." in name:
        return f"external_lib.{external_root(name)}"

    return "external_unknown"