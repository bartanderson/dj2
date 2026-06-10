# tools/analysis/api/engine_query.py

from tools.analysis.api.query_graph import context, surface, impact


def engine_query(graph, symbol: str, depth: int = 1):
    """
    Single deterministic reasoning surface over the graph.

    This is the ONLY supported external query abstraction.
    """

    return {
        "symbol": symbol,
        "context": context(graph, symbol),
        "surface": surface(graph, symbol, depth=depth),
        "impact": impact(graph, symbol, depth=depth),
    }