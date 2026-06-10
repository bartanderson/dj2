# tools/analysis/api/query_discovery.py

from __future__ import annotations

from typing import Any, List


# =========================================================
# SYMBOL LISTING (GLOBAL TRUTH SURFACE)
# =========================================================

def list_symbols(graph: Any, limit: int = 100) -> List[str]:
    """
    Returns raw symbol universe from graph edges.
    """

    edges = getattr(graph, "edges", [])

    symbols = set()

    for e in edges:
        if getattr(e, "caller", None):
            symbols.add(e.caller)
        if getattr(e, "callee", None):
            symbols.add(e.callee)

    return sorted(symbols)[:limit]


# =========================================================
# SIMPLE SYMBOL SEARCH (TEXT MATCH ONLY)
# =========================================================

def find_symbols(graph: Any, text: str, limit: int = 50) -> List[str]:
    """
    Naive substring match over symbol universe.
    """

    text = text.lower()
    results = []

    for sym in list_symbols(graph, limit=10_000):
        if text in sym.lower():
            results.append(sym)

    return results[:limit]


# =========================================================
# FILE DISCOVERY (FROM GRAPH EDGES ONLY)
# =========================================================

def _extract_file(symbol: str):
    # take module path only (everything before last dot)
    if "." in symbol:
        return ".".join(symbol.split(".")[:-1])
    return symbol

def find_files(graph: Any, text: str, limit: int = 50) -> List[str]:
    """
    Extract file-level symbols if present in graph.
    """

    edges = getattr(graph, "edges", [])

    files = set()

    for e in edges:
        caller = getattr(e, "caller", "")
        callee = getattr(e, "callee", "")

        files.add(_extract_file(caller))
        files.add(_extract_file(callee))

    text = text.lower()

    results = [f for f in files if text in f.lower()]

    return results[:limit]