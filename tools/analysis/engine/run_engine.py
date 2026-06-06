# tools/analysis/engine/run_engine.py

from dataclasses import dataclass
from typing import Any, Dict

from tools.analysis.ingestion.scan_project_files import scan_project_files
from tools.analysis.classification.classify_references import classify_references
from tools.analysis.persistence.persist_file_analysis import persist_file_analysis
from tools.analysis.graph.graph_builder import GraphBuilder
from tools.analysis.engine.parity_check import run_parity_check, print_parity_report

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
        # 6. SNAPSHOT (minimal parity view)
        # ==================================================
        snapshot = {
            "file_count": processed_count,
            "symbol_ref_count": symbol_ref_count,
            "edge_count": edge_count,
        }

        # ==================================================
        # 7. INGESTION RESULT (PARITY LAYER)
        # ==================================================
        ingestion = {
            "file_analyses": file_analyses,
            "processed_count": processed_count,
            "total_symbol_refs": symbol_ref_count,
        }

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

    print("RUNNING ENGINE TEST")

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
    # save db
    parity = run_parity_check(
        db_path="tools/analysis/data/analysis.db",
        engine_result=result,
    )

    print("\n=== DONE ===")
    print("Files:", result.facts["file_count"])
    print("Symbols:", result.facts["symbol_ref_count"])
    print("Edges:", result.facts["edge_count"])