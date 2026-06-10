# tools/analysis/oracle/semantic_graph.py

from tools.analysis.oracle.edge_semantics import interpret_edge


class SemanticGraphView:
    def __init__(self, graph):
        self.graph = graph

    def edges(self):
        return [
            interpret_edge(e)
            for e in getattr(self.graph, "edges", [])
        ]

    def raw_edges(self):
        return getattr(self.graph, "edges", [])