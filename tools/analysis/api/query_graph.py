# tools/analysis/api/query_graph.py

from collections import defaultdict, deque

# =========================================================
# CORE GRAPH QUERY SURFACE
# =========================================================

def _build_index(graph):
    forward = defaultdict(set)
    reverse = defaultdict(set)

    for e in getattr(graph, "edges", []):
        forward[e.caller].add(e.callee)
        reverse[e.callee].add(e.caller)

    return forward, reverse


# ---------------------------------------------------------
# 1. NEIGHBORHOOD (local structural context)
# ---------------------------------------------------------

def neighbors(graph, symbol: str):
    forward, reverse = _build_index(graph)

    return {
        "symbol": symbol,
        "calls": sorted(forward.get(symbol, [])),
        "called_by": sorted(reverse.get(symbol, [])),
    }


# ---------------------------------------------------------
# 2. FORWARD DEPENDENCY (what this symbol touches)
# ---------------------------------------------------------

def depends_on(graph, symbol: str, depth: int = 1):
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


# ---------------------------------------------------------
# 3. REVERSE DEPENDENCY (impact surface)
# ---------------------------------------------------------

def used_by(graph, symbol: str, depth: int = 1):
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