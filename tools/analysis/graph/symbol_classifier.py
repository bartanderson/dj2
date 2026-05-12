# tools/analysis/graph/symbol_classifier.py

from __future__ import annotations

from typing import Literal

SymbolClass = Literal[
    "project",
    "builtin",
    "stdlib",
    "runtime",
    "external",
]

# ----------------------------
# BUILTIN NAMES (Python runtime primitives)
# ----------------------------
BUILTINS = {
    "str",
    "len",
    "set",
    "list",
    "dict",
    "any",
    "range",
    "print",
    "isinstance",
    "sorted",
    "dict",
    "set",
    "bool",
    "int",
    "float",
    "tuple",
}

# ----------------------------
# STDLIB MODULE PREFIXES (import-based noise)
# ----------------------------
STDLIB_PREFIXES = (
    "pathlib.",
    "collections.",
    "dataclasses.",
    "typing.",
    "sqlite3.",
    "json.",
    "ast.",
)

# ----------------------------
# RUNTIME / AST HELPERS (optional keep/debug)
# ----------------------------
RUNTIME_NAMES = {
    "visit",
    "generic_visit",
    "walk",
    "NodeVisitor",
    "AST",
}


def classify_symbol(name: str) -> SymbolClass:
    """
    Deterministic symbol classification for filtering + graph purity.
    Used by:
        - persistence layer
        - AST extraction
        - indexing layer
    """

    if not name:
        return "external"

    # 1. BUILTINS
    if name in BUILTINS:
        return "builtin"

    # 2. STD LIB IMPORT PATHS
    if any(name.startswith(prefix) for prefix in STDLIB_PREFIXES):
        return "stdlib"

    # 3. RUNTIME / AST INTERNALS
    if name in RUNTIME_NAMES:
        return "runtime"

    # 4. PROJECT SYMBOLS (heuristic boundary)
    # anything dot-qualified that is NOT stdlib is assumed project or external package
    if "." in name:
        # project code in your system uses tools.analysis.*
        if name.startswith("tools."):
            return "project"
        return "external"

    # 5. Only treat fully-qualified internal namespace as project
    if name.startswith("tools."):
        return "project"

    return "external"