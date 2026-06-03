# tools/analysis/truth/query_executor.py

from tools.analysis.truth.query_ast import Select, Filter, Combine

class QueryExecutor:

    def __init__(self, views: dict):
        self.views = views  # injected deterministic truth objects

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
        return self.views[q.view]

    def _combine(self, a, b):
        return {
            "left": a,
            "right": b,
        }

    def _filter(self, f: Filter):
        # deterministic filter pass-through (applied post-view)
        return {
            "filter": {
                "key": f.key,
                "op": f.op,
                "value": f.value,
            }
        }