# tools\analysis\assessor\assessor.py

from collections import defaultdict
from dataclasses import dataclass, field
from tools.analysis.oracle.db_oracle import DBOracle

from tools.analysis.truth.views import (
    build_structure_view,
    build_stability_view,
    build_integrity_view,
)
from tools.analysis.reducer.reduce import reduce
from tools.analysis.api.oracle_router import route_query
from tools.analysis.engine.responsibility_map import ROLE_PATTERNS, print_responsibility_map
from tools.analysis.engine.responsibility_snapshot import build_responsibility_snapshot


# =========================================================
# DB-DERIVED SHAPES (assessor analogues of the in-memory
# ContractReport / ValidationResult used by run_engine)
# =========================================================

@dataclass
class ContractReport:
    file_path: str
    violations: list
    ok: bool


@dataclass
class ValidationSummary:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


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

        symbol_reference_count = self.oracle.symbol_reference_count()

        if len(edges) != symbol_reference_count:
            errors.append((
                "edge_count_mismatch",
                {"graph_edges": len(edges), "symbol_references": symbol_reference_count},
            ))

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

        for e in graph:
            node_degree[e.caller] = node_degree.get(e.caller, 0) + 1
            node_degree[e.callee] = node_degree.get(e.callee, 0) + 1

        # NOTE: bucket info lives in symbol_references, not graph_edges —
        # GraphEdge has no .bucket attribute, so deriving bucket_summary
        # from the graph snapshot always reported everything as
        # "classification_gap". Pull it from the DB directly instead.
        bucket_summary = self.oracle.bucket_summary()

        ranked = sorted(node_degree.items(), key=lambda x: -x[1])
        top_nodes = ranked[:10]
        high_fanout = [(n, d) for n, d in top_nodes if d > 3]

        return {
            "file_count": self.oracle.file_count(),
            "edge_count": len(graph),
            "symbol_reference_count": self.oracle.symbol_reference_count(),
            "bucket_summary": bucket_summary,
            "graph_insights": {
                "top_nodes_by_degree": top_nodes,
            },
            "structural_signals": {
                "high_fanout_nodes": high_fanout,
            },
            "node_degree": node_degree,
        }

    # =====================================================
    # SEED DISCOVERY
    # 
    # =====================================================

    def query(self, text: str):
        return route_query(
            text,
            self.snapshot(),
            self.oracle.discover_seed_symbols,
        )

    # =====================================================
    # STRUCTURE VIEW (run_engine Phase 3)
    # =====================================================

    def structure_view(self):
        return build_structure_view(self.snapshot())

    # =====================================================
    # DB-DERIVED CONTRACT REPORTS
    #
    # run_engine built these from in-memory file_analyses via
    # evaluate_file_contracts() (a no-op stub) + SystemValidator's
    # symbol-reference check. Both checks reduce to "does this file's
    # persisted symbol_references contain a null caller/callee" —
    # which is now a DB query, not an in-memory pass.
    # =====================================================

    def file_contract_reports(self):
        files = self.oracle.file_reference_map()
        reports = []

        for file_path, refs in files.items():
            violations = []

            for ref in refs:
                if not ref["caller"] or not ref["callee"]:
                    violations.append({
                        "contract_name": "symbol_reference_integrity",
                        "severity": "error",
                        "message": f"Invalid symbol reference at line {ref['line_number']}",
                    })

            reports.append(ContractReport(
                file_path=file_path,
                violations=violations,
                ok=len(violations) == 0,
            ))

        return reports

    def stability_view(self):
        return build_stability_view(self.file_contract_reports(), drift_signals=[])

    def validation_summary(self):
        errors = []
        warnings = []

        for report in self.file_contract_reports():
            for v in report.violations:
                if v["severity"] == "error":
                    errors.append(f"{report.file_path}: {v['message']}")

        edges = self.snapshot().edges

        if len(edges) == 0:
            errors.append("Graph has zero edges (possible ingestion failure)")

        if len(edges) < 10:
            warnings.append("Low edge count detected (possible under-analysis)")

        return ValidationSummary(errors=errors, warnings=warnings)

    def integrity_view(self):
        return build_integrity_view(self.validation_summary(), self.snapshot())

    # =====================================================
    # RESPONSIBILITY MAP / SNAPSHOT
    #
    # DB-derived equivalent of build_responsibility_map(), grouping
    # persisted symbol_references by file_path instead of needing
    # in-memory file_analyses.
    # =====================================================

    def responsibility_map(self):
        files_data = self.oracle.file_reference_map()

        files = []
        totals = defaultdict(int)

        for file_path, refs in files_data.items():
            text = " ".join(
                [file_path] + [r["callee"] or "" for r in refs]
            ).lower()

            roles = {
                role_name: any(p in text for p in patterns)
                for role_name, patterns in ROLE_PATTERNS.items()
            }

            for role_name, enabled in roles.items():
                if enabled:
                    totals[role_name] += 1

            files.append({
                "file_path": file_path,
                "roles": roles,
                "edge_count": len(refs),
            })

        return {
            "files": files,
            "totals": dict(totals),
        }

    def responsibility_snapshot(self):
        return build_responsibility_snapshot(
            responsibility_map=self.responsibility_map(),
            db_totals=self.build_snapshot(),
        )

    # =====================================================
    # REDUCED SNAPSHOT (run_engine Phase 4 fold step)
    # =====================================================

    def reduced_snapshot(self):
        return reduce([self.build_snapshot()])

    # =====================================================
    # SYSTEM REPORT
    #
    # Bundles everything run_engine produced AFTER db creation +
    # validation: Phase 3 views, Phase 4 snapshot/reduction, the
    # responsibility map, the invariants check, and (optionally)
    # the discovery/oracle-router debug queries from __main__.
    # =====================================================

    def system_report(self, sample_queries=None):
        report = {
            "snapshot": self.build_snapshot(),
            "reduced": self.reduced_snapshot(),
            "structure_view": self.structure_view(),
            "stability_view": self.stability_view(),
            "integrity_view": self.integrity_view(),
            "responsibility": self.responsibility_snapshot(),
            "run_integrity_check": self.run_integrity_check(),
        }

        if sample_queries:
            report["queries"] = {
                q: self.query(q)
                for q in sample_queries
            }

        return report

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

    # -----------------------------------------------------
    # SYSTEM REPORT (migrated from run_engine post-persist phases)
    # -----------------------------------------------------
    report = assessor.system_report(sample_queries=[
        "what depends on resolve_analysis_db_path",
        "show ingestion surface",
        "what affects engine snapshot",
    ])

    print("\n=== REDUCED SNAPSHOT ===")
    print(report["reduced"])

    print("\n=== STRUCTURE VIEW ===")
    print("edges:", len(report["structure_view"].edges))
    print("hotspots:", report["structure_view"].hotspots[:10])

    print("\n=== STABILITY VIEW ===")
    print(report["stability_view"])

    print("\n=== INTEGRITY VIEW ===")
    print(report["integrity_view"])

    print_responsibility_map(report["responsibility"])

    print("\n=== RUN INTEGRITY CHECK ===")
    print(report["run_integrity_check"])

    print("\n=== ORACLE ROUTER ===")
    for q, res in report["queries"].items():
        print("\nQUERY:", q)
        print("intent:", res.intent)
        print("seeds:", res.seed_symbols[:5])
        print("expanded:", res.expanded_symbols[:5])


if __name__ == "__main__":
    main()