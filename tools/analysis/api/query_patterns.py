# tools/analysis/api/query_patterns.py

from tools.analysis.api.query_graph import neighbors, depends_on, used_by

def impact(graph, symbol):
    return used_by(graph, symbol, depth=2)

def surface(graph, symbol):
    return depends_on(graph, symbol, depth=2)

def context(graph, symbol):
    return neighbors(graph, symbol)