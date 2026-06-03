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

        if q.view not in self.views:
            raise ValueError(f"Unknown view: {q.view}")

        return ViewResult(
            view=q.view,
            data=self.views[q.view]
        )

    def _combine(self, a, b):

        left_name = self._resolve_view_name(a)
        right_name = self._resolve_view_name(b)

        if self.registry is not None:
            if not self.registry.validate_combine(left_name, right_name):
                raise ValueError(f"Invalid semantic combine: {left_name} + {right_name}")

        return {
            "type": "COMBINE",
            "left": a,
            "right": b,
            "meta": {
                "left_view": left_name,
                "right_view": right_name,
            }
        }

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