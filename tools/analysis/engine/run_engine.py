# tools/analysis/engine/run_engine.py

from dataclasses import dataclass
from typing import Any, Dict
import sqlite3

from tools.analysis.ingestion.scan_project_files import scan_project_files
from tools.analysis.classification.classify_references import classify_references
from tools.analysis.persistence.persist_file_analysis import persist_file_analysis
from tools.analysis.graph.graph_builder import GraphBuilder

from tools.analysis.engine.parity_check import run_parity_check, print_parity_report
from tools.analysis.engine.structural_parity_diff import (
    run_structural_diff,
    print_structural_diff,
)

from tools.analysis.persistence.persist_file_analysis import initialize_database
from tools.analysis.engine.engine_snapshot import EngineSnapshotBuilder
from tools.analysis.engine.engine_snapshot_diff import diff_snapshots, print_snapshot_diff
from tools.analysis.engine.engine_evaluation_snapshot import EngineEvaluationSnapshotBuilder
from tools.analysis.engine.snapshot_stub import build_snapshot_stub
from tools.analysis.engine.pipeline_inventory import build_pipeline_inventory, print_pipeline_inventory
from tools.analysis.truth.views import build_structure_view
from tools.analysis.truth.views import build_stability_view
from tools.analysis.truth.views import build_integrity_view
from tools.analysis.validation.system_validator import SystemValidator

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

    def run(self, corpus, project_prefixes, repo_root, connection=None):

        # ==================================================
        # 1. INGESTION
        # ==================================================
        file_analyses = list(
            scan_project_files(
                corpus.root_path,
                project_prefixes,
                repo_root,
            )
        )

        if not file_analyses:
            raise RuntimeError("Engine ingestion produced no analyses")

        processed_count = len(file_analyses)

        # ==================================================
        # 2. CLASSIFICATION
        # ==================================================
        file_analyses = [
            classify_references(a, project_prefixes)
            for a in file_analyses
        ]

        # ==================================================
        # 3. PERSISTENCE
        # ==================================================
        if connection is not None:
            for analysis in file_analyses:
                persist_file_analysis(connection, analysis, project_prefixes)

        # ==================================================
        # 4. GRAPH BUILD
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
        edge_count = len(getattr(graph, "edges", []))

        # ==================================================
        # 5. FACTS
        # ==================================================
        symbol_ref_count = sum(
            len(a.symbol_references) for a in file_analyses
        )

        facts = {
            "file_count": processed_count,
            "symbol_ref_count": symbol_ref_count,
            "edge_count": edge_count,
        }

        # ==================================================
        # 6. INGESTION RESULT
        # ==================================================
        ingestion = {
            "file_analyses": file_analyses,
            "processed_count": processed_count,
            "total_symbol_refs": symbol_ref_count,
        }
        # ==================================================
        # 7. SNAPSHOT
        # ==================================================
        # ----------------------------
        # FANOUT STATE INITIALIZATION
        # ----------------------------
        all_reports = []
        drift_signals = []

        # ----------------------------
        # VALIDATION STAGE (ENGINE CONSOLIDATION)
        # ----------------------------
        if connection is not None:
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM symbol_references")
            db_total = cursor.fetchone()[0]
        else:
            db_total = 0

        db_snapshot = {
            "symbol_reference_count": db_total
        }

        validation_errors = []

        validator = SystemValidator(strict=False)

        for analysis in file_analyses:
            errors = validator.validate(
                analysis=analysis,
                graph=graph,
                contract_report=None,
                db_snapshot=db_snapshot,
            )

            if hasattr(errors, "errors"):
                validation_errors.extend(errors.errors)
            elif isinstance(errors, list):
                validation_errors.extend(errors)

        validation = type(
            "ValidationResult",
            (),
            {
                "ok": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": [],
            },
        )()

        system_shape = {"stub": True}
        structure_view = build_structure_view(graph)
        stability_view = build_stability_view(all_reports, drift_signals)
        integrity_view = build_integrity_view(validation, db_snapshot, graph)
        subsystem_view = {"stub": True}

        print("\n=== STRUCTURE VIEW CHECK ===")
        print(len(getattr(structure_view, "edges", structure_view)))
        print("\n=== STABILITY VIEW CHECK ===")
        print(stability_view)
        print("\n=== INTEGRITY VIEW CHECK ===")
        print(integrity_view)


        snapshot_builder = EngineEvaluationSnapshotBuilder()

        snapshot = snapshot_builder.build(
            file_analyses=file_analyses,
            graph=graph,
        )

        # ----------------------------
        # REDUCTION (FIRST FANOUT MODULE)
        # ----------------------------
        from tools.analysis.reducer.reduce import reduce

        reduced = reduce([snapshot])

        print("\n=== REDUCE CHECK ===")
        print(reduced)

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
    ENGINE_DB = "tools.analysis.data.analysis.db"
    LEGACY_DB = "_Users_bartl_dev_dj2_tools.old.db"

    print("RUNNING ENGINE TEST")

    # IMPORTANT: matches your real target root (tools.old)
    corpus = type("C", (), {"root_path": "tools.old"})()
    project_prefixes = []
    repo_root = "."

    runner = EngineRunner()

    result = runner.run(
        corpus=corpus,
        project_prefixes=project_prefixes,
        repo_root=repo_root,
        connection=None,
    )

    # -----------------------------------
    # ENGINE SNAPSHOT (derived from facts)
    # -----------------------------------
    engine_snapshot = {
        "file_count": result.facts["file_count"],
        "symbol_ref_count": result.facts["symbol_ref_count"],
        "edge_count": result.facts["edge_count"],
    }

    print("\n=== ENGINE SNAPSHOT ===")
    for k, v in engine_snapshot.items():
        print(f"{k}: {v}")

    # -----------------------------------
    # PARITY CHECK (DB vs ENGINE)
    # -----------------------------------
    parity = run_parity_check(
        db_path=LEGACY_DB,
        engine_result=result,
    )

    print_parity_report(parity)

    # -----------------------------------
    # STRUCTURAL DIFF (DB vs ENGINE GRAPH)
    # -----------------------------------
    diff = run_structural_diff(
        db_path=LEGACY_DB,
        file_analyses=result.ingestion["file_analyses"],
    )

    print_structural_diff(diff)

    # ===================================
    # PIPELINE REPRESENTATION LAYER
    # ===================================

    inventory = build_pipeline_inventory(
        result.ingestion["file_analyses"]
    )

    pipeline_snapshot = build_snapshot_stub(
        inventory=inventory,
        db_totals=engine_snapshot,
    )

    print_pipeline_inventory(inventory)