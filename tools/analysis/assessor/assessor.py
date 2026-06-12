# tools\analysis\assessor\assessor.py

from collections import defaultdict
from tools.analysis.oracle.db_oracle import DBOracle

class Assessor:
    def __init__(self, oracle):
        self.oracle = oracle

    def run(self, symbol: str):
        graph = self.oracle.get_snapshot_graph()

        return {
            "symbol": symbol,

            # existing DB capability
            "neighbors": self.oracle.neighbors(symbol),
            "surface": self.oracle.surface(symbol, 1),
            "influence": self.oracle.influence(symbol, 1),

            # NEW assessor capabilities (now actually executed)
            "validation": self.validate_graph(),
            "snapshot": self.build_snapshot(),
        }

    def snapshot(self):
        return self.oracle.get_snapshot_graph()

    def neighbors(self, symbol: str):
        return self.oracle.neighbors(symbol)

    def surface(self, symbol: str, depth: int = 1):
        return self.oracle.surface(symbol, depth)

    def influence(self, symbol: str, depth: int = 1):
        return self.oracle.influence(symbol, depth)

    def semantic(self):
        return self.oracle.get_semantic_edges()

    def degree(self):
        edges = self.oracle.get_snapshot_graph().edges

        degree_map = {}

        for e in edges:
            degree_map[e.caller] = degree_map.get(e.caller, 0) + 1
            degree_map[e.callee] = degree_map.get(e.callee, 0) + 1

        return degree_map

    def hotspots(self, top_n=10):
        deg = self.degree()
        return sorted(deg.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def module_projection(self):
        edges = self.oracle.get_snapshot_graph().edges

        pairs = []

        for e in edges:
            caller_mod = e.caller.split(".")[0]
            callee_mod = e.callee.split(".")[0]

            if caller_mod != callee_mod:
                pairs.append((caller_mod, callee_mod))

        return pairs

    def subsystems(self):
        proj = self.module_projection()

        graph = defaultdict(set)

        for caller, callee in proj:
            graph[caller].add(callee)

        return {k: sorted(v) for k, v in graph.items()}

    def subsystem_degree(self):
        proj = self.module_projection()

        fanout = {}

        for caller, callee in proj:
            fanout[caller] = fanout.get(caller, 0) + 1

        return fanout

    def impact(self, symbol: str, depth: int = 1):
        return {
            "symbol": symbol,
            "surface": self.oracle.surface(symbol, depth),
            "influence": self.oracle.influence(symbol, depth),
            "neighbors": self.oracle.neighbors(symbol),
            "semantic": self.oracle.get_semantic_edges(),
        }

    def run_integrity_check(self):
        edges = self.snapshot().edges

        errors = []

        for e in edges:
            if not e.caller or not e.callee:
                errors.append(("invalid_edge", e))

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def structural_diff(self, engine_edges, db_edges):
        engine_set = set((e.caller, e.callee) for e in engine_edges)
        db_set = set((e.caller, e.callee) for e in db_edges)

        missing_in_db = engine_set - db_set
        missing_in_engine = db_set - engine_set

        return {
            "missing_in_db": list(missing_in_db),
            "missing_in_engine": list(missing_in_engine)
        }

    def validate_graph(self):
        graph = self.snapshot().edges

        errors = []
        warnings = []

        for e in graph:
            if not e.caller:
                errors.append(("missing_caller", e))
            if not e.callee:
                errors.append(("missing_callee", e))

            if e.caller == e.callee:
                warnings.append(("self_edge", e))

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "edge_count": len(graph)
        }

    def build_snapshot(self):
        graph = self.oracle.get_snapshot_graph().edges

        node_degree = {}
        bucket_summary = {
            "project": 0,
            "builtin": 0,
            "classification_gap": 0,
        }

        for e in graph:
            node_degree[e.caller] = node_degree.get(e.caller, 0) + 1
            node_degree[e.callee] = node_degree.get(e.callee, 0) + 1

            bucket = getattr(e, "bucket", None)
            if bucket not in bucket_summary:
                bucket = "classification_gap"
            bucket_summary[bucket] += 1

        ranked = sorted(node_degree.items(), key=lambda x: -x[1])
        top_nodes = ranked[:10]
        high_fanout = [(n, d) for n, d in top_nodes if d > 3]

        return {
            "file_count": self.oracle.file_count(),
            "edge_count": len(graph),
            "bucket_summary": bucket_summary,
            "graph_insights": {
                "top_nodes_by_degree": top_nodes,
            },
            "structural_signals": {
                "high_fanout_nodes": high_fanout,
            },
            "node_degree": node_degree,
        }
# ---------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------

def main():
    oracle = DBOracle("C_Users_bartl_dev_dj2_tools_analysis_engine.db")
    assessor = Assessor(oracle)

    result = assessor.run("re.sub")

    print("symbol:", result["symbol"])
    print("neighbors:", result["neighbors"])
    print("surface:", result["surface"])
    print("influence:", result["influence"])

    print("\nvalidation:", result["validation"])
    print("\nsnapshot:", result["snapshot"])


if __name__ == "__main__":
    main()