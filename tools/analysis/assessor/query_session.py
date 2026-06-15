# tools/analysis/assessor/query_session.py
#
# QuerySession — the first true oracle runtime object.
#
# Owns a single query lifecycle:
#   - snapshot binding (graph + seeds at query time)
#   - intent classification
#   - router execution
#   - expansion trace capture
#   - result normalization
#   - reasoning output packaging
#
# Purpose: make query execution reproducible and inspectable.
# Every query that passes through Assessor produces a QuerySession
# that can be replayed, diffed, or logged without re-running the engine.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================
# QUERY SESSION RESULT (normalized output shape)
# =========================================================

@dataclass
class QuerySessionResult:
    # identity
    raw_query: str
    intent: str

    # seeds (DB-authoritative)
    seeds: List[str]

    # expansion
    expanded: List[str]
    expansion_trace: Dict[str, Any]

    # execution
    primitives: List[str]
    execution_plan: Dict[str, Any]

    # graph snapshot facts at query time
    snapshot_edge_count: int

    # reasoning surface (human + AI readable)
    reasoning: Dict[str, Any] = field(default_factory=dict)

    def seed_explanation(self) -> str:
        if not self.seeds:
            return "No seeds found for query."
        return f"Query '{self.raw_query}' matched {len(self.seeds)} seed(s): {', '.join(self.seeds[:5])}"

    def expansion_explanation(self) -> str:
        added = [s for s in self.expanded if s not in self.seeds]
        return (
            f"Expansion added {len(added)} symbol(s) via {self.intent} traversal. "
            f"Total symbols in result: {len(self.expanded)}."
        )

    def intent_mapping_trace(self) -> Dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "detected_intent": self.intent,
            "primitives_selected": self.primitives,
            "seed_count": len(self.seeds),
            "expanded_count": len(self.expanded),
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "query": self.raw_query,
            "intent": self.intent,
            "seeds": self.seeds,
            "expanded": self.expanded,
            "seed_explanation": self.seed_explanation(),
            "expansion_explanation": self.expansion_explanation(),
            "intent_mapping_trace": self.intent_mapping_trace(),
            "snapshot_edge_count": self.snapshot_edge_count,
        }


# =========================================================
# QUERY SESSION
# =========================================================

class QuerySession:
    """
    Owns a single query lifecycle against a fixed oracle snapshot.

    Usage:
        session = QuerySession(oracle)
        result = session.execute("what depends on resolve_analysis_db_path")
        print(result.summary())
        print(result.seed_explanation())
    """

    def __init__(self, oracle):
        self.oracle = oracle
        self._graph = None  # bound once per session on first execute

    def _bind_snapshot(self):
        """Bind the graph snapshot once at query time — not at construction."""
        if self._graph is None:
            self._graph = self.oracle.get_snapshot_graph()
        return self._graph

    def run_query(self, text: str) -> QuerySessionResult:
        from tools.analysis.api.oracle_router import route_query

        graph = self._bind_snapshot()

        route_result = route_query(
            text,
            graph,
            self.oracle.discover_seed_symbols,
        )

        expansion_trace = route_result.execution_plan.get("trace", {})

        result = QuerySessionResult(
            raw_query=text,
            intent=route_result.intent,
            seeds=route_result.seed_symbols,
            expanded=route_result.expanded_symbols,
            expansion_trace=expansion_trace,
            primitives=route_result.execution_plan.get("primitives", []),
            execution_plan=route_result.execution_plan,
            snapshot_edge_count=len(graph.edges),
            reasoning={
                "seed_paths": expansion_trace.get("seed_paths", {}),
                "edges": expansion_trace.get("edges", {}),
            },
        )

        return result

    def run_batch(self, queries: List[str]) -> Dict[str, QuerySessionResult]:
        """
        Execute multiple queries against the same bound snapshot.
        Snapshot is bound on the first query and reused — deterministic
        across the batch.
        """
        return {q: self.run_query(q) for q in queries}