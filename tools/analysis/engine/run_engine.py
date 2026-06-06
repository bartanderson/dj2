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
        # 7. INGESTION RESULT
        # ==================================================
        ingestion = {
            "file_analyses": file_analyses,
            "processed_count": processed_count,
            "total_symbol_refs": symbol_ref_count,
        }
        # ==================================================
        # 7. SNAPSHOT
        # ==================================================
        system_shape = {"stub": True}
        structure_view = {"stub": True}
        stability_view = {"stub": True}
        integrity_view = {"stub": True}
        subsystem_view = {"stub": True}

        snapshot_builder = EngineEvaluationSnapshotBuilder()

        snapshot = snapshot_builder.build(
            file_analyses=file_analyses,
            graph=graph,
        )

        return EngineResult(
            ingestion=ingestion,
            graph={
                "graph": graph,
                "edge_count": edge_count,
            },
            facts=facts,
            snapshot=snapshot,
        )


if __name__ == "__main__":

    # ----------------------------
    # DB TARGETS (explicit roles)
    # ----------------------------
    ENGINE_DB = "tools.analysis.data.analysis.db"
    LEGACY_DB = "_Users_bartl_dev_dj2_tools.old.db"

    print("RUNNING ENGINE TEST")

    # IMPORTANT: matches your real target root (tools.old)
    corpus = type("C", (), {"root_path": "tools"})()
    project_prefixes = []
    repo_root = "."

    runner = EngineRunner()

    result = runner.run(
        corpus=corpus,
        project_prefixes=project_prefixes,
        repo_root=repo_root,
        connection=None,
    )

    # ----------------------------
    # PARITY CHECK
    # ----------------------------
    parity = run_parity_check(
        db_path=LEGACY_DB,
        engine_result=result,
    )

    print("\n=== DONE ===")
    print("Files:", result.facts["file_count"])
    print("Symbols:", result.facts["symbol_ref_count"])
    print("Edges:", result.facts["edge_count"])

    print_parity_report(parity)

    # ----------------------------
    # STRUCTURAL DIFF
    # ----------------------------
    diff = run_structural_diff(
        db_path=LEGACY_DB,
        file_analyses=result.ingestion["file_analyses"],
    )

    print_structural_diff(diff)

    pipeline_snapshot = None  # TEMP placeholder for now

    diff = diff_snapshots(
        engine_snapshot=result.snapshot,
        pipeline_snapshot=pipeline_snapshot,
    )

    print_snapshot_diff(diff)

    from tools.analysis.engine.pipeline_inventory import (
        build_pipeline_inventory,
        print_pipeline_inventory,
    )
    inventory = build_pipeline_inventory(
        result.ingestion["file_analyses"]
    )

    print_pipeline_inventory(inventory)

    from tools.analysis.engine.pipeline_dependency_tracer import (
        trace_pipeline_dependencies,
        print_pipeline_report,
    )

    index = {
        a.file_path: {
            "imports": getattr(a, "imports", []),
            "calls": getattr(a, "calls", []),
        }
        for a in result.ingestion["file_analyses"]
    }

    report = trace_pipeline_dependencies(index)
    print_pipeline_report(report)  