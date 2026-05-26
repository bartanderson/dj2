# tools/analysis/api/inspect_symbol.py

from tools.analysis.graph.symbol_router import route_symbol
from tools.analysis.graph.symbol_classifier import classify_symbol


def inspect_symbol(
    name: str,
    *,
    route: str = "unknown",
    project_prefixes=None,
    runtime_bindings=None,
    project_symbols=None,
):
    project_prefixes = project_prefixes or []
    runtime_bindings = runtime_bindings or {}
    project_symbols = project_symbols or set()

    resolved_route = route_symbol(name) if route == "unknown" else route

    classification = classify_symbol(
        name=name,
        route=resolved_route,
        project_prefixes=project_prefixes,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
    )

    return {
        "name": name,
        "route": resolved_route,
        "classification": classification,
    }