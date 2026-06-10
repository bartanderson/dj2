# tools/analysis/engine/run_engine.py

from dataclasses import dataclass
from typing import Any, Dict
import sqlite3
from pathlib import Path

from tools.analysis.ingestion.scan_project_files import scan_project_files
from tools.analysis.classification.classify_references import classify_references
from tools.analysis.graph.graph_builder import GraphBuilder

from tools.analysis.engine.structural_parity_diff import (
    run_structural_diff,
    print_structural_diff,
)

from tools.analysis.engine.engine_snapshot import EngineSnapshotBuilder
from tools.analysis.engine.engine_snapshot_diff import diff_snapshots, print_snapshot_diff
from tools.analysis.engine.engine_evaluation_snapshot import EngineEvaluationSnapshotBuilder
from tools.analysis.engine.responsibility_snapshot import build_responsibility_snapshot
from tools.analysis.engine.responsibility_map import build_responsibility_map, print_responsibility_map
from tools.analysis.truth.views import build_structure_view
from tools.analysis.truth.views import build_stability_view
from tools.analysis.truth.views import build_integrity_view
from tools.analysis.validation.system_validator import SystemValidator
from tools.analysis.graph.reachability_stage import build_reachability_view
from tools.analysis.persistence.persistence_engine import persist_all, initialize_database
from tools.analysis.engine.db_resolver import resolve_analysis_db_path
from tools.analysis.api.query_graph import context, surface, impact
from tools.analysis.api.engine_query import engine_query


ENABLE_FAULTS = False  # hard off for now

@dataclass
class ContractReport:
    file_path: str
    violations: list
    ok: bool

class ValidationResultShim:
    def __init__(self, errors):
        self.errors = errors
        self.warnings = []
        self.ok = len(errors) == 0


def evaluate_file_contracts(file_path, file_analysis, graph):
    return ContractReport(
        file_path=file_path,
        violations=[],
        ok=True,
    )

# ----------------------------
# SINGLE SOURCE OF TRUTH
# ----------------------------
DB_PATH = "tools.analysis.data.analysis.db"


@dataclass
class EngineResult:
    ingestion: Any
    graph: Any
    facts: Dict[str, Any]
    snapshot: Dict[str, Any]
    reduced: Any | None = None

class EngineRunner:

    def run(self, corpus, project_prefixes, repo_root, connection=None, chaos_mode: bool = False):

        # ==================================================
        # PHASE 0: INGESTION
        # ==================================================
        file_analyses = list(
            scan_project_files(
                corpus.root_path,
                project_prefixes,
                repo_root,
            )
        )

        # ----------------------------
        # CHAOS MODE (controlled fault injection)
        # ----------------------------
        if chaos_mode:
            print("\n=== CHAOS MODE ACTIVE ===")

            # 1. drop half the files
            file_analyses = file_analyses[: max(1, len(file_analyses) // 2)]

            # 2. corrupt bucket metadata slightly
            for a in file_analyses:
                for r in getattr(a, "symbol_references", []):
                    r.bucket = "unknown"

        if not file_analyses:
            raise RuntimeError("Engine ingestion produced no analyses")

        processed_count = len(file_analyses)

        file_analyses = [
            classify_references(a, project_prefixes)
            for a in file_analyses
        ]

        symbol_reference_count = sum(
            len(a.symbol_references) for a in file_analyses
        )

        ingestion = {
            "file_analyses": file_analyses,
            "processed_count": processed_count,
            "symbol_reference_count": symbol_reference_count,
        }

        # ==================================================
        # PHASE 0.5: GLOBAL INIT (MUST EXIST BEFORE ANYTHING ELSE)
        # ==================================================
        validator = SystemValidator(strict=False)

        all_reports = []
        drift_signals = []
        validation_errors = []

        # ==================================================
        # PHASE 1: GRAPH BUILD (NO ANALYSIS HERE)
        # ==================================================
        builder = GraphBuilder()

        for analysis in file_analyses:
            for ref in analysis.symbol_references:
                builder.add_reference(
                    caller=ref.caller,
                    callee=ref.callee,
                    line_number=ref.line_number,
                    bucket=getattr(ref, "bucket", "unknown"),
                )

        graph = builder.build()

        if ENABLE_FAULTS:
            from tools.analysis.observability.fault_injector import (
                inject_edge_drop,
                inject_classification_drift,
            )

            graph = inject_edge_drop(graph, rate=0.1)
            file_analyses = inject_classification_drift(file_analyses, rate=0.1)

        edge_count = len(getattr(graph, "edges", []))

        # Obeservability begin
        from tools.analysis.observability.signal_contract import prune_signals
        from tools.analysis.observability.instruments import (
            ingestion_instrument,
            graph_instrument,
            classification_instrument,
        )

        signals = []

        signals += ingestion_instrument(file_analyses)
        signals += graph_instrument(graph)
        signals += classification_instrument(file_analyses)

        signals = prune_signals(signals)

        print("\n=== OBSERVABILITY SIGNALS ===")

        for s in signals:
            print(
                f"{s.stage} | {s.signal_class} | {s.name} = {s.value}"
            )
        # Obeservability end

        print("\n=== SYMBOL REFERENCE SANITY CHECK ===")

        sample = file_analyses[:3]

        for a in sample:
            print(a.file_path)
            print("  symbol_references:", len(a.symbol_references))

        print("TOTAL symbol refs:", sum(len(a.symbol_references) for a in file_analyses))
        print("EDGE COUNT:", edge_count)

        persist_all(
            connection=connection,
            file_analyses=file_analyses,
            graph=graph,
            project_prefixes=project_prefixes,
        )

        facts = {
            "file_count": processed_count,
            "symbol_reference_count": ingestion["symbol_reference_count"],
            "edge_count": edge_count,
        }

        # ==================================================
        # PHASE 2: PER-FILE ANALYSIS (CONTRACT + VALIDATION)
        # ==================================================
        for analysis in file_analyses:

            report = evaluate_file_contracts(
                file_path=analysis.file_path,
                file_analysis=analysis,
                graph=graph,
            )

            all_reports.append(report)

            validation = validator.validate(
                analysis=analysis,
                graph=graph,
                contract_report=report,
            )

            if hasattr(validation, "errors"):
                validation_errors.extend(validation.errors)

        validation_summary = ValidationResultShim(validation_errors)

        # ==================================================
        # PHASE 3: VIEWS (READ-ONLY DERIVATION)
        # ==================================================
        structure_view = build_structure_view(graph)
        stability_view = build_stability_view(all_reports, drift_signals)
        integrity_view = build_integrity_view(
            validation_summary,
            graph
        )
        subsystem_view = {"stub": True}

        # ==================================================
        # PHASE 4: SNAPSHOT + REDUCTION
        # ==================================================
        snapshot = EngineEvaluationSnapshotBuilder().build(
            file_analyses=file_analyses,
            graph=graph,
        )

        from tools.analysis.reducer.reduce import reduce
        reduced = reduce([snapshot])

        # ==================================================
        # OPTIONAL DEBUG OUTPUT (KEEP OR REMOVE LATER)
        # ==================================================
        print("\n=== STRUCTURE VIEW CHECK ===")
        print(len(getattr(structure_view, "edges", structure_view)))

        print("\n=== STABILITY VIEW CHECK ===")
        print(stability_view)

        print("\n=== INTEGRITY VIEW CHECK ===")
        print(integrity_view)

        print("\n=== REDUCE CHECK ===")
        print(reduced)

        # ==================================================
        # RETURN
        # ==================================================
        return EngineResult(
            ingestion=ingestion,
            graph={
                "graph": graph,
                "edge_count": edge_count,
            },
            facts=facts,
            snapshot=snapshot,
            reduced=reduced,
        )


if __name__ == "__main__":

    # ----------------------------
    # DB TARGETS (explicit roles)
    # ----------------------------

    print("RUNNING ENGINE TEST")
    project_prefixes = []
    repo_root = "."

    #ENGINE_DB = "tools.analysis.data.analysis.db"

    import tkinter as tk 
    from tkinter import filedialog

    root = tk.Tk()

    root.withdraw() # hide the empty window

    # select analysis target path
    selected_target = filedialog.askdirectory(initialdir=Path(__file__).parent) 
    
    corpus = type(
        "Corpus",
        (),
        {"root_path": selected_target},
    )()
 
    db_path = resolve_analysis_db_path(corpus.root_path) # path selected normalized with _ + .db
    print(f"Target: {corpus.root_path}")
    print(f"Database: {db_path}")
    runner = EngineRunner()

    engine_result = runner.run(
        corpus=corpus,
        project_prefixes=project_prefixes,
        repo_root=repo_root,
        connection=sqlite3.connect(db_path),
    )
    print("RESULT TYPE:", type(engine_result))
    print("RESULT KEYS:", engine_result.keys() if isinstance(engine_result, dict) else None)
    # -----------------------------------
    # ENGINE SNAPSHOT (derived from facts)
    # -----------------------------------
    engine_snapshot = {
        "file_count": engine_result.facts["file_count"],
        "symbol_reference_count": engine_result.facts["symbol_reference_count"],
        "edge_count": engine_result.facts["edge_count"],
    }

    print("\n=== ENGINE SNAPSHOT ===")
    for k, v in engine_snapshot.items():
        print(f"{k}: {v}")



    graph = engine_result.graph["graph"] if isinstance(engine_result.graph, dict) else engine_result.graph

    print("\n=== QUERY LAYER SELF-CHECK ===")

    sample_symbol = None

    if graph.edges:
        sample_symbol = graph.edges[0].caller

    if sample_symbol:
        print("\n=== ENGINE QUERY SURFACE TEST ===")

        query_result = engine_query(graph, sample_symbol, depth=2)

        print("symbol:", query_result["symbol"])
        print("context:", query_result["context"])
        print("surface:", query_result["surface"][:10])
        print("impact:", query_result["impact"][:10])


    # ===================================
    # PIPELINE REPRESENTATION LAYER
    # ===================================
    print("DEBUG RESULT TYPE BEFORE INGESTION ACCESS:", type(query_result))
    print("DEBUG RESULT VALUE:", query_result)

    responsibility_map = build_responsibility_map(
        engine_result.ingestion["file_analyses"]
    )

    responsibility_snapshot = build_responsibility_snapshot(
        responsibility_map=responsibility_map,
        db_totals=engine_snapshot,
    )

    print_responsibility_map(responsibility_snapshot)