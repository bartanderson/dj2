# tools/analysis/graph/graph_builder.py

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from tools.analysis.graph.symbol_classifier import project_key


@dataclass
class GraphEdge:
    caller: str
    callee: str
    line_number: int


@dataclass
class GraphBundle:
    edges: list[GraphEdge] = field(default_factory=list)
    bucket_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class GraphBuilder:
    """
    Pure transformation layer:
    - no DB access
    - no classification logic
    - no side effects
    """

    def __init__(self):
        self.seen = set()
        self.edges = []
        self.bucket_counts = defaultdict(int)

    def add_reference(self, caller: str, callee: str, line_number: int, bucket: str):
        key = (caller, callee, line_number)

        if key in self.seen:
            return

        self.seen.add(key)

        self.edges.append(
            GraphEdge(
                caller=caller,
                callee=callee,
                line_number=line_number,
            )
        )

        self.bucket_counts[bucket] += 1

    def build(self) -> GraphBundle:
        return GraphBundle(
            edges=self.edges,
            bucket_counts=dict(self.bucket_counts),
        )

    def edges_for(self, callee: str):
        return [e for e in self.edges if e.callee == callee]

    def callers_of(self, callee: str):
        return {e.caller for e in self.edges if e.callee == callee}

    def callees_of(self, caller: str):
        return {
            e.callee
            for e in self.edges
            if e.caller == caller
        }

    def callers_of(self, callee: str):
        return {
            e.caller
            for e in self.edges
            if e.callee == callee
        }

    def adjacency(self):
        graph = {}
        for e in self.edges:
            graph.setdefault(e.caller, set()).add(e.callee)
        return graph

    def top_callees(self, limit: int = 10):
        counts = {}

        seen = set()

        for e in self.edges:
            key = (e.caller, e.callee)

            if key in seen:
                continue
            seen.add(key)

            counts[e.callee] = counts.get(e.callee, 0) + 1

        return sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def top_callers(self, limit: int = 10):
        counts = {}

        seen = set()

        for e in self.edges:
            key = (e.caller, e.callee)

            if key in seen:
                continue
            seen.add(key)

            counts[e.caller] = counts.get(e.caller, 0) + 1

        return sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def connectivity_score(self):
        score = {}

        for e in self.edges:
            score[e.caller] = score.get(e.caller, 0) + 1
            score[e.callee] = score.get(e.callee, 0) + 1

        return score

    def module_projection(self):
        """
        Converts symbol-level edges → module-level dependency edges.
        """

        edges = set()

        for e in self.edges:
            caller_parts = e.caller.split(".")
            callee_parts = e.callee.split(".")

            caller_module = ".".join(caller_parts[:2]) if len(caller_parts) >= 2 else caller_parts[0]
            callee_module = ".".join(callee_parts[:2]) if len(callee_parts) >= 2 else callee_parts[0]

            if caller_module == callee_module:
                continue

            edges.add((caller_module, callee_module))

        return sorted(edges)