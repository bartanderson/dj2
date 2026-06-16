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

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


# =========================================================
# QUERY SESSION RESULT (normalized output shape)
# =========================================================

@dataclass
class QuerySessionResult:
    # identity
    raw_query: str
    intent: str

    # reproducibility
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    queried_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # seeds (DB-authoritative)
    seeds: List[str] = field(default_factory=list)

    # expansion
    expanded: List[str] = field(default_factory=list)
    expansion_trace: Dict[str, Any] = field(default_factory=dict)

    # execution
    primitives: List[str] = field(default_factory=list)
    execution_plan: Dict[str, Any] = field(default_factory=dict)

    # graph snapshot facts at query time
    snapshot_edge_count: int = 0

    # reasoning surface (human + AI readable)
    reasoning: Dict[str, Any] = field(default_factory=dict)

    def seed_explanation(self) -> str:
        if not self.seeds:
            return "No seeds found for query."
        return (
            f"Query '{self.raw_query}' matched {len(self.seeds)} seed(s): "
            f"{', '.join(self.seeds[:5])}"
        )
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

    def seed_paths(self) -> Dict[str, Any]:
        """Which graph paths were followed to reach each seed."""
        return self.reasoning.get("seed_paths", {})

    def expansion_edges(self) -> Dict[str, Any]:
        """Edge-level trace of how expansion propagated from seeds."""
        return self.reasoning.get("edges", {})

    def node_reasons(self) -> Dict[str, str]:
        """Per-node explanation of why each expanded symbol was included."""
        trace = self.expansion_trace
        return trace.get("node_reasons", {})

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "queried_at": self.queried_at,
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
        result = session.run_query("what depends on resolve_analysis_db_path")
        print(result.summary())

    For observability:
        session = QuerySession(oracle, logger=print)
        result = session.run_query("what depends on X")
    """

    def __init__(self, oracle, logger: Optional[Callable] = None):
        self.oracle = oracle
        self.logger = logger
        self._graph = None
        self._history: List[QuerySessionResult] = []

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
            logger=self.logger,
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

        self._history.append(result)
        return result

    def replay(self, result: QuerySessionResult) -> QuerySessionResult:
        """
        Re-run a prior query against the same bound snapshot.
        Produces a new QuerySessionResult with a fresh session_id and
        queried_at — allowing diff comparison against the original.
        Snapshot is NOT re-fetched; determinism is guaranteed by the
        bound graph state.
        """
        return self.run_query(result.raw_query)

    def history(self) -> List[QuerySessionResult]:
        """All results produced by this session in execution order."""
        return list(self._history)

    def run_batch(self, queries: List[str]) -> Dict[str, QuerySessionResult]:
        """
        Execute multiple queries against the same bound snapshot.
        Snapshot is bound on the first query and reused — deterministic
        across the batch.
        """
        return {q: self.run_query(q) for q in queries}

    def run_algebra(self, text: str, views: dict) -> dict:
        """
        Full pipeline: natural language → oracle expansion + algebra result.

        Steps:
          1. run_query() — oracle router gives intent + expansion trace
          2. compile_query(intent) — maps intent → AST via query compiler
          3. QueryExecutor.execute() — runs AST against provided views

        Returns a dict with both the oracle result and the algebra result
        so callers can see the expansion trace AND the structured view output
        side by side.

        views: dict of {view_name: view_object} — same format as TruthTestHarness
        """
        from tools.analysis.truth.query_compiler import compile_and_explain
        from tools.analysis.truth.query_executor import QueryExecutor

        oracle_result = self.run_query(text)

        compiled = compile_and_explain(oracle_result.intent, text=text)
        plan = compiled["plan"]

        executor = QueryExecutor(views=views)
        algebra_result = executor.execute(plan.root)

        return {
            "text": text,
            "intent": oracle_result.intent,
            "oracle": oracle_result,
            "compiled_ast": compiled["ast"],
            "compiler_explanation": compiled["explanation"],
            "algebra_result": algebra_result,
        }