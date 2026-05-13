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


def classify_symbol(name: str, project_prefixes: list[str]) -> SymbolClass:
    if not name:
        return "external"

    # BUILTINS
    if name in BUILTINS:
        return "builtin"

    # STD LIB
    if any(name.startswith(prefix) for prefix in STDLIB_PREFIXES):
        return "stdlib"

    # RUNTIME
    if name in RUNTIME_NAMES:
        return "runtime"

    # PROJECT (ONLY SOURCE OF TRUTH)
    if any(name.startswith(prefix) for prefix in project_prefixes):
        return "project"

    return "external"