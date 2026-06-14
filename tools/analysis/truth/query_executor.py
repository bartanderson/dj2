# tools/analysis/truth/query_executor.py

from dataclasses import dataclass
from typing import Any, Optional

from tools.analysis.truth.query_ast import Select, Filter, Combine


# -------------------------
# RESULT TYPES (grounded)
# -------------------------

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


@dataclass
class QueryResult:
    view: str
    metric: Optional[str]
    data: Any


# -------------------------
# EXECUTOR
# -------------------------

class QueryExecutor:

    def __init__(self, views: dict, registry=None):
        self.views = views
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

    # -------------------------
    # SELECT (deterministic projection)
    # -------------------------

    def _select(self, q: Select):

        view = self.views[q.view]

        # APPLY FILTER EARLY (before projection)
        if q.filter:
            view = self._apply_filter(view, q.filter)

        # full view
        if q.metric is None:
            return QueryResult(
                view=q.view,
                metric=None,
                data=view
            )

        # attribute projection
        if hasattr(view, q.metric):
            return QueryResult(
                view=q.view,
                metric=q.metric,
                data=getattr(view, q.metric),
            )

        # dict projection
        if isinstance(view, dict):
            return QueryResult(
                view=q.view,
                metric=q.metric,
                data=view.get(q.metric),
            )

        raise ValueError(
            f"Metric '{q.metric}' not resolvable for view '{q.view}'"
        )

    # -------------------------
    # COMBINE (pure structural join)
    # -------------------------

    def _combine(self, a, b):

        # deterministic wrapper only
        return CombineResult(
            left=a,
            right=b,
        )

    # -------------------------
    # FILTER (pure descriptor node)
    # -------------------------

    def _filter(self, f: Filter):

        return FilterResult(
            key=f.key,
            op=f.op,
            value=f.value,
        )

    def _apply_filter(self, data, f: Filter):

        key, op, value = f.key, f.op, f.value

        if isinstance(data, dict):
            if op == "==":
                return data if data.get(key) == value else None
            return data

        if isinstance(data, list):
            if op == "==":
                return [x for x in data if x.get(key) == value]
            if op == ">":
                return [x for x in data if x.get(key, 0) > value]
            if op == "<":
                return [x for x in data if x.get(key, 0) < value]

        return data