# tools/analysis/query/graph_query.py

from collections import defaultdict
from typing import Any


# =========================================================
# CORE QUERY PRIMITIVES (DB-TRUTH GRAPH VIEW)
# =========================================================

def surface(graph: Any, symbol: str) -> list[str]:
    """
    Outgoing edges: what this symbol directly calls.
    """
    return [
        e.callee
        for e in getattr(graph, "edges", [])
        if e.caller == symbol
    ]


def impact(graph: Any, symbol: str) -> list[str]:
    """
    Incoming edges: what depends on this symbol.
    """
    return [
        e.caller
        for e in getattr(graph, "edges", [])
        if e.callee == symbol
    ]


def context(graph: Any, symbol: str) -> dict[str, Any]:
    """
    Combined local neighborhood (1-hop view).
    Deterministic structural snapshot.
    """
    outgoing = surface(graph, symbol)
    incoming = impact(graph, symbol)

    return {
        "symbol": symbol,
        "calls": outgoing,
        "called_by": incoming,
    }


# =========================================================
# OPTIONAL: MULTI-HOP EXPANSION (SAFE, STRUCTURAL ONLY)
# =========================================================

def depends_on(graph: Any, symbol: str, depth: int = 2) -> list[str]:
    """
    Forward traversal (bounded).
    """
    seen = set()
    frontier = {symbol}
    result = []

    for _ in range(depth):
        next_frontier = set()

        for node in frontier:
            for e in getattr(graph, "edges", []):
                if e.caller == node and e.callee not in seen:
                    seen.add(e.callee)
                    next_frontier.add(e.callee)
                    result.append(e.callee)

        frontier = next_frontier

    return result


def used_by(graph: Any, symbol: str, depth: int = 2) -> list[str]:
    """
    Reverse traversal (bounded).
    """
    seen = set()
    frontier = {symbol}
    result = []

    for _ in range(depth):
        next_frontier = set()

        for node in frontier:
            for e in getattr(graph, "edges", []):
                if e.callee == node and e.caller not in seen:
                    seen.add(e.caller)
                    next_frontier.add(e.caller)
                    result.append(e.caller)

        frontier = next_frontier

    return result