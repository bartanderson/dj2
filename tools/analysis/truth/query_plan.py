# tools/analysis/truth/query_plan.py

from dataclasses import dataclass
from typing import Any

from tools.analysis.truth.query_ast import Select, Filter, Combine


@dataclass
class QueryPlan:
    root: Any

    VALID_METRICS = {
        "STRUCTURE": {"edges", "adjacency", "hotspots"},
        "STABILITY": {"stable_contracts", "unstable_contracts", "drift_signals"},
        "INTEGRITY": {"errors", "warnings", "db_mismatches"},
        "SUMMARY": {"edge_count", "file_count", "metrics"},
        "SUBSYSTEM": {"subsystems"},
    }

class QuerySemanticsRegistry:

    VALID_COMBINES = {
        ("STRUCTURE", "STABILITY"),
        ("STRUCTURE", "INTEGRITY"),
        ("SUMMARY", "STABILITY"),
        ("SUBSYSTEM", "STRUCTURE"),
    }

    VALID_FILTER_KEYS = {
        "STRUCTURE": {"edges", "callee", "caller"},
        "STABILITY": {"stable_contracts", "unstable_contracts"},
        "SUBSYSTEM": {"modules", "edge_count"},
    }

    def validate_combine(self, left, right):
        return (
            (left, right) in self.VALID_COMBINES
            or (right, left) in self.VALID_COMBINES
        )

    def validate_filter_key(self, view: str, key: str):
        allowed = self.VALID_FILTER_KEYS.get(view, set())
        return key in allowed

    def validate_metric(self, view: str, metric: str | None):
        if metric is None:
            return True
        allowed = self.VALID_FILTER_KEYS.get(view, set())
        return metric in allowed

class QueryPlanner:

    def __init__(self, registry: QuerySemanticsRegistry):
        self.registry = registry

    def plan(self, query):
        query = self._validate(query)
        return QueryPlan(root=query)

    def _extract_view(self, q):
        if isinstance(q, Select):
            return q.view

        if isinstance(q, Combine):
            raise ValueError("Cannot extract view from Combine during validation")

        if isinstance(q, Filter):
            raise ValueError("Cannot extract view from Filter during validation")

        raise ValueError(f"Unknown AST node type: {type(q)}")

    def _validate_filter(self, f: Filter):

        # optional: enforce registry rules here
        if not self.registry.validate_filter_key("STRUCTURE", f.key):
            # NOTE: in real version you'd route by view context
            pass

        return f

    def _validate(self, query):

        if isinstance(query, Combine):

            if isinstance(query.left, Combine) or isinstance(query.right, Combine):
                raise ValueError("Nested Combine not supported (flat-only AST)")

            left_view = self._extract_view(query.left)
            right_view = self._extract_view(query.right)

            if not self.registry.validate_combine(left_view, right_view):
                raise ValueError(f"Invalid combine: ({left_view}, {right_view})")

            left = self._validate(query.left)
            right = self._validate(query.right)

            if isinstance(left, Filter) or isinstance(right, Filter):
                raise ValueError("Combine cannot directly include Filter-only branches")

            return Combine(left=left, right=right)

    def _validate_select(self, q: Select):

        if q.view not in QueryPlan.VALID_METRICS:
            raise ValueError(f"Unknown view: {q.view}")

        if q.metric is None:
            return q

        allowed = QueryPlan.VALID_METRICS[q.view]

        if q.metric not in allowed:
            raise ValueError(
                f"Invalid metric '{q.metric}' for view '{q.view}'"
            )

        return q

