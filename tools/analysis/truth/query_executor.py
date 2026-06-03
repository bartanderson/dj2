# tools/analysis/truth/query_executor.py

from tools.analysis.truth.query_ast import Select, Filter, Combine
from dataclasses import dataclass
from typing import Any

from tools.analysis.truth.views import (
    StructureView,
    StabilityView,
    IntegrityView,
    SystemSummaryView,
)

@dataclass
class ViewResult:
    view: str
    data: Any
    
@dataclass
class FilterResult:
    key: str
    op: str
    value: Any

@dataclass
class CombineResult:
    left: Any
    right: Any

class QueryExecutor:

    def __init__(self, views: dict, registry=None):
        self.views = views  # injected deterministic truth objects
        self.registry = registry

    def execute(self, query):

        if isinstance(query, Select):
            return self._select(query)

        if isinstance(query, Combine):
            return self._combine(
                self.execute(query.left),
                self.execute(query.right),
            )

        if isinstance(query, Filter):
            return self._filter(query)

        raise ValueError(f"Invalid query node: {type(query)}")

    def _select(self, q: Select):

        view = self.views[q.view]

        # no metric → full object
        if q.metric is None:
            return view

        # dataclass projection
        if hasattr(view, q.metric):
            return getattr(view, q.metric)

        # dict projection fallback (subsystem safe)
        if isinstance(view, dict):
            return view.get(q.metric)

        raise ValueError(
            f"Metric '{q.metric}' not resolvable for view '{q.view}'"
        )

    def _combine(self, a, b):
        return CombineResult(left=a, right=b)

    def _filter(self, f: Filter):
        return FilterResult(
            key=f.key,
            op=f.op,
            value=f.value,
        )

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
        return (left, right) in self.VALID_COMBINES or (right, left) in self.VALID_COMBINES

    def validate_filter_key(self, view: str, key: str):
        allowed = self.VALID_FILTER_KEYS.get(view, set())
        return key in allowed

    def validate_metric(self, view: str, metric: str | None):

        if metric is None:
            return True

        allowed = self.VALID_FILTER_KEYS.get(view, set())

        return metric in allowed