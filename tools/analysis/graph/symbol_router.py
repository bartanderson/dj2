# tools/analysis/graph/symbol_router.py

from __future__ import annotations

import builtins
import sys

from typing import Literal

from tools.analysis.graph.symbol_identity import (
    project_key,
    module_key,
)

from tools.analysis.graph.project_graph_context import (
    ProjectGraphContext,
)

RouteType = Literal[
    "project",
    "runtime",
    "builtin",
    "stdlib",
    "external",
    "unknown",
]


BUILTINS = set(dir(builtins))
STDLIB_PREFIXES = set(sys.stdlib_module_names)


def is_builtin_symbol(name: str) -> bool:
    if not name:
        return False

    root = name.split(".")[0]
    return root in BUILTINS


def is_stdlib_symbol(name: str) -> bool:
    if not name:
        return False

    root = name.split(".")[0]
    return root in STDLIB_PREFIXES


def is_runtime_symbol(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
) -> bool:

    if not name:
        return False

    runtime_bindings = runtime_bindings or {}

    parts = name.split(".")
    root = parts[0]

    # explicit runtime alias root
    if root in runtime_bindings:
        return True

    # implicit instance/runtime contexts
    if root in ("self", "cls", "ctx", "app"):
        return True

    # synthetic call-chain artifacts
    if root in ("get", "generate"):
        return True

    return False


def is_project_symbol(
    name: str,
    project_symbols: set[str] | None = None,
) -> bool:

    if not name or not project_symbols:
        return False

    from tools.analysis.graph.symbol_identity import (
        project_key,
        module_key,
    )

    project_leafs = {
        project_key(s)
        for s in project_symbols
    }

    project_modules = {
        module_key(s)
        for s in project_symbols
    }

    leaf = project_key(name)
    module = module_key(name)

    return (
        name in project_symbols
        or leaf in project_leafs
        or module in project_modules
    )


def route_symbol(
    name: str,
    runtime_bindings: dict[str, str] | None = None,
    project_symbols: set[str] | None = None,
) -> RouteType:

    if not name:
        return "unknown"

    # HIGH-CONFIDENCE DOMAINS FIRST

    if is_builtin_symbol(name):
        return "builtin"

    if is_runtime_symbol(name, runtime_bindings):
        return "runtime"

    if is_stdlib_symbol(name):
        return "stdlib"

    # PROJECT MATCHING IS FUZZIER
    # SO IT MUST COME LATER

    if is_project_symbol(name, project_symbols):
        return "project"

    if "." in name:
        return "external"

    return "unknown"

def route_symbol_with_context(
    name: str,
    context: ProjectGraphContext,
) -> RouteType:

    return route_symbol(
        name=name,
        runtime_bindings=context.runtime_bindings,
        project_symbols=context.project_symbols,
    )