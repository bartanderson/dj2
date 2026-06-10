# tools/analysis/api/query_graph.py

from collections import defaultdict, deque
from typing import Any, Dict, List


# =========================================================
# INTERNAL INDEX BUILDER (STRUCTURAL ONLY)
# =========================================================

def _edges(graph):
    return getattr(graph, "edges", [])


def _build_index(graph):
    forward = defaultdict(set)
    reverse = defaultdict(set)

    for e in _edges(graph):
        forward[e.caller].add(e.callee)
        reverse[e.callee].add(e.caller)

    return forward, reverse


# =========================================================
# CONTEXT (was neighbors)
# =========================================================

def context(graph: Any, symbol: str) -> Dict[str, Any]:
    forward, reverse = _build_index(graph)

    return {
        "symbol": symbol,
        "calls": sorted(forward.get(symbol, [])),
        "called_by": sorted(reverse.get(symbol, [])),
    }


# =========================================================
# SURFACE (forward dependency)
# =========================================================

def surface(graph: Any, symbol: str, depth: int = 1) -> List[str]:
    forward, _ = _build_index(graph)

    visited = set()
    queue = deque([(symbol, 0)])
    result = set()

    while queue:
        node, d = queue.popleft()

        if node in visited:
            continue
        visited.add(node)

        if d > 0:
            result.add(node)

        if d < depth:
            for nxt in forward.get(node, []):
                queue.append((nxt, d + 1))

    return sorted(result)


# =========================================================
# IMPACT (reverse dependency)
# =========================================================

def impact(graph: Any, symbol: str, depth: int = 1) -> List[str]:
    _, reverse = _build_index(graph)

    visited = set()
    queue = deque([(symbol, 0)])
    result = set()

    while queue:
        node, d = queue.popleft()

        if node in visited:
            continue
        visited.add(node)

        if d > 0:
            result.add(node)

        if d < depth:
            for nxt in reverse.get(node, []):
                queue.append((nxt, d + 1))

    return sorted(result)


# =========================================================
# ALIASES (optional backward compatibility)
# =========================================================

depends_on = surface
used_by = impact