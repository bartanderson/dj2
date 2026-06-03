# tools/analysis/run_analysis_pipeline.py
from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass
from tools.analysis.load_config_profiles import (load_analysis_profiles, build_profile_prefixes)
from tools.analysis.ingestion.scan_project_files import (scan_project_files)
from tools.analysis.persistence.persist_file_analysis import (create_database,persist_file_analysis)
from tools.analysis.graph.project_context import build_project_prefixes
from tools.analysis.core.pathing import (resolve_project_root)
from tools.analysis.graph.graph_builder import GraphBuilder
from tools.analysis.graph.evaluation_snapshot import build_evaluation_snapshot
from tools.analysis.query.query_file_analysis import fetch_complete_file_analysis
from tools.analysis.metrics.extract_metrics import extract_metrics
from tools.analysis.reducer.reduce import reduce
from tools.analysis.classification.classify_references import classify_references
from tools.analysis.contracts.load_contract import load_system_contract
from tools.analysis.contracts.contract_validator import ContractRuntimeValidator
from tools.analysis.contracts.contract_observer import (evaluate_file_contracts, summarize_reports)
from tools.analysis.inspection.system_shape import (
    generate_system_shape,
    format_system_shape,
)
from tools.analysis.validation.system_validator import SystemValidator
from tools.analysis.contracts.contract_drift_classifier import ContractDriftClassifier

from tools.analysis.truth.query_executor import QueryExecutor
from tools.analysis.truth.query_ast import Select
from tools.analysis.truth.views import (
    build_structure_view,
    build_stability_view,
    build_integrity_view,
    build_system_summary_view,
)
from tools.analysis.truth.subsystem_view import build_subsystem_view

@dataclass
class PipelineContext:
    project_root: Path
    db_path: Path
    project_prefixes: list[str]

def resolve_repo_root(path: str | Path) -> Path:
    p = Path(path).resolve()

    for parent in [p, *p.parents]:

        if (parent / ".git").exists():
            return parent

        if (parent / "pyproject.toml").exists():
            return parent

    return p

def get_config_path():
    # repo root = two levels up from this file
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "config" / "analysis_profiles.yaml"

def validate(stage: str, validator, context: dict):
    validator.validate_stage(stage, context)

def build_stage_context(stage: str, *, edges: int = 0, snapshot_mismatch: bool = False,
                        classification_called_in_persistence: bool = False,
                        no_cross_layer_logic: bool = True) -> dict:
    """
    Unified stage context builder for ContractRuntimeValidator.
    This eliminates duplication of inline dicts across the pipeline.
    """
    context = {
        "edges": edges,
        "snapshot_mismatch": snapshot_mismatch,
        "classification_called_in_persistence": classification_called_in_persistence,
        "no_cross_layer_logic": no_cross_layer_logic,
    }
    return context

# tools/analysis/run_analysis_pipeline.py

def run_analysis_pipeline(
    project_root: str | Path,
    database_path: str | Path,
    project_prefixes: list[str] | None = None,
) -> dict:

    project_root = Path(project_root).resolve()
    repo_root = resolve_repo_root(project_root)

    if not project_prefixes:
        project_prefixes = build_profile_prefixes(project_root)
    
    connection = None
    
    try:

        connection = create_database(database_path)

        # Load and enforce system contract
        contract = load_system_contract()
        validator = ContractRuntimeValidator(contract)

        # --------------------------
        # INGESTION
        # --------------------------
        file_analyses = list(scan_project_files(project_root, project_prefixes, repo_root))
        print("\n[POST INGESTION]")
        for a in file_analyses:
            print(
                a.file_path,
                "symbol_refs=",
                len(a.symbol_references),
            )
        print("FILE ANALYSIS COUNT:", len(file_analyses))
            
        if not file_analyses:
            raise RuntimeError("Pipeline produced no analyses")
        processed_count = len(file_analyses)

        # --------------------------
        # CLASSIFICATION
        # --------------------------
        file_analyses = [
            classify_references(a, project_prefixes) for a in file_analyses
        ]
        print("\n[POST CLASSIFICATION]")
        for a in file_analyses:
            print(
                a.file_path,
                "symbol_refs=",
                len(a.symbol_references),
            )
            
        # -------------------------
        # PERSISTENCE
        # -------------------------
        for analysis in file_analyses:

            # 🔧 DEBUG HOOK (temporary, remove after diagnosis)
            print(
                "SYMBOL REFS (pre-persist):",
                len(getattr(analysis, "symbol_references", []))
            )

            persist_file_analysis(connection, analysis, project_prefixes)

        all_reports = []
        
        # --------------------------
        # SNAPSHOTS + METRICS
        # --------------------------
        snapshots = []
        last_snapshot = None

        for analysis in file_analyses:
            builder = GraphBuilder()

            for ref in analysis.symbol_references:
                if not ref.bucket:
                    continue
                builder.add_reference(
                    caller=ref.caller,
                    callee=ref.callee,
                    line_number=ref.line_number,
                    bucket=ref.bucket or "unknown",
                )

            print(
                "[GRAPH BUILD]",
                analysis.file_path,
                "symbol_refs=",
                len(analysis.symbol_references),
                "graph_edges=",
                len(builder.edges),
            )

            if len(builder.edges) == 0:
                print(
                    "[GRAPH DEBUG]",
                    "refs_with_bucket=",
                    sum(
                        1
                        for r in analysis.symbol_references
                        if getattr(r, "bucket", None)
                    ),
                )

            graph = builder.build()

            if len(graph.edges) == 0:
                print(
                    "[ZERO EDGE FILE]",
                    analysis.file_path,
                    "symbol_refs=",
                    len(analysis.symbol_references),
                )

            # --------------------------
            # CONTRACT OBSERVATION (A)
            # --------------------------
            cursor = connection.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM symbol_references WHERE file_path = ?",
                (analysis.file_path,)
            )
            db_count = cursor.fetchone()[0]

            db_snapshot = {
                "symbol_reference_count": db_count
            }

            report = evaluate_file_contracts(
                file_path=analysis.file_path,
                file_analysis=analysis,
                graph=graph,
                db_snapshot=db_snapshot,
            )

            from tools.analysis.contracts.persist_contract_violations import (
                persist_contract_violations
            )

            persist_contract_violations(connection, report)

            # -------------------------------------------------
            # 🆕 CONTRACT DRIFT CLASSIFICATION PASS
            # -------------------------------------------------
            from tools.analysis.contracts.contract_drift_classifier import ContractDriftClassifier

            drift_classifier = ContractDriftClassifier()
            drift_input = all_reports + [report]
            drift_signals = drift_classifier.classify(drift_input)

            # -----------------------------------------
            # 🆕 DRIFT PERSISTENCE LAYER
            # -----------------------------------------
            cursor = connection.cursor()

            for s in drift_signals:

                cursor.execute("""
                    INSERT INTO contract_drift_history (
                        contract_name,
                        classification,
                        layer,
                        count
                    ) VALUES (?, ?, ?, ?)
                """, (
                    s.contract_name,
                    s.classification,
                    s.layer,
                    s.count,
                ))

            connection.commit()

            # -----------------------------------------
            # 🆕 CONTRACT HEALTH AGGREGATION PASS
            # -----------------------------------------
            from tools.analysis.contracts.contract_health_aggregator import ContractHealthAggregator

            cursor = connection.cursor()

            cursor.execute("""
                SELECT contract_name, classification, layer, count
                FROM contract_drift_history
            """)

            rows = [
                {
                    "contract_name": r[0],
                    "classification": r[1],
                    "layer": r[2],
                    "count": r[3],
                }
                for r in cursor.fetchall()
            ]

            health_agg = ContractHealthAggregator()
            health = health_agg.aggregate(rows)

            print("\n[CONTRACT HEALTH SUMMARY]")
            for h in health:
                print(
                    f"- {h.contract_name} | "
                    f"stability={h.stability_score} | "
                    f"trend={h.trend_direction} | "
                    f"obs={h.total_observations}"
                )


            # -----------------------------------------
            # 🆕 CONTRACT LIFECYCLE PASS
            # -----------------------------------------
            from tools.analysis.contracts.contract_lifecycle import ContractLifecycleController

            lifecycle_controller = ContractLifecycleController()

            lifecycle_states = lifecycle_controller.evaluate(health)

            print("\n[CONTRACT LIFECYCLE STATES]")
            for l in lifecycle_states:
                print(
                    f"- {l.contract_name} | "
                    f"{l.state} | "
                    f"{l.recommendation}"
                )


            print("[DRIFT INPUT SIZE]", len(drift_input))
            print("[CURRENT REPORT HAS VIOLATIONS]", len(report.violations))

            # -----------------------------------------
            # OBSERVABILITY OUTPUT
            # -----------------------------------------
            if drift_signals:
                print("\n[CONTRACT DRIFT SIGNALS]")
                for s in drift_signals:
                    print(
                        f"- {s.contract_name} | "
                        f"{s.classification} | "
                        f"count={s.count} | "
                        f"{s.layer}"
                    )

            all_reports.append(report)

            if report.violations:
                print("\n[CONTRACT VIOLATIONS]")
                for v in report.violations:
                    print(f"- {v.contract_name} | {v.layer} | {v.message}")

            # Snapshot stage
            validator.validate_stage(
                "snapshot",
                build_stage_context("snapshot", edges=len(graph.edges)),
            )

            snapshot = build_evaluation_snapshot(analysis=analysis, graph=graph)
            snapshots.append(snapshot)
            last_snapshot = snapshot

            # Metrics stage
            validator.validate_stage(
                "metrics",
                build_stage_context("metrics", edges=len(graph.edges)),
            )

            validator = SystemValidator(strict=False)

            validation = validator.validate(
                analysis=analysis,
                graph=graph,
                contract_report=report,
                db_snapshot=db_snapshot,
            )

            if not validation.ok:
                print("\n[VALIDATION ERRORS]")
                for e in validation.errors:
                    print(" -", e)

            if validation.warnings:
                print("\n[VALIDATION WARNINGS]")
                for w in validation.warnings:
                    print(" -", w)

        # --------------------------
        # REDUCER
        # --------------------------
        reduced = reduce(snapshots)

        validator.validate_stage(
            "reducer",
            build_stage_context("reducer", edges=reduced.get("edges", 0)),
        )

        assert reduced["edges"] > 0 or len(file_analyses) == 0, (
            "Pipeline produced no edges (graph construction failure or empty dataset)"
        )

        # --------------------------
        # SYSTEM UNDERSTANDING LAYER
        # --------------------------
        system_shape = generate_system_shape(connection)

        print("\n[SYSTEM SHAPE]")
        print(system_shape)
        print(format_system_shape(system_shape))

        # --------------------------
        # TRUTH VIEW BUILDING
        # --------------------------

        structure_view = build_structure_view(graph)
        stability_view = build_stability_view(all_reports, drift_signals if 'drift_signals' in locals() else [])
        integrity_view = build_integrity_view(validation, db_snapshot, graph)
        summary_view = build_system_summary_view(
            reduced,
            report,
            processed_count,
        )
        subsystem_view = build_subsystem_view(graph)

        print("\n[OBSERVABILITY - SUBSYSTEM VIEW]")
        for name, data in subsystem_view["subsystems"].items():
            print(f"- {name} | modules={len(data['modules'])} | edges={data['edge_count']}")

        views = {
            "STRUCTURE": structure_view,
            "STABILITY": stability_view,
            "INTEGRITY": integrity_view,
            "SUMMARY": summary_view,
            "SUBSYSTEM": subsystem_view,
        }
        
        executor = QueryExecutor(views=views)

        # --------------------------
        # GLOBAL INVARIANTS
        # --------------------------
        validator.validate_stage(
            "global",
            build_stage_context(
                "global",
                edges=reduced.get("edges", 0),
                classification_called_in_persistence=False,
                no_cross_layer_logic=True,
            ),
        )

        # --------------------------
        # FINAL METRICS REPORT
        # --------------------------
        report = extract_metrics([snapshot])

        print("Analysis complete. Processed", processed_count, "files.")

        for analysis in file_analyses:
            # (you already compute graph earlier — reuse same structure if refactored later)
            pass  # placeholder if we unify later

        print("\n[CONTRACT SUMMARY]")
        print(summarize_reports(all_reports))

        print("\n[SMOKE TEST - TRUTH QUERY LAYER]")

        test_queries = [
            Select("STRUCTURE"),
            Select("STABILITY"),
            Select("INTEGRITY"),
            Select("SUMMARY"),
        ]

        for q in test_queries:
            result = executor.execute(q)
            print("\n---", q.view, "---")
            print(result)

        return {
            "snapshots": snapshots,
            "snapshot": last_snapshot,
            "metrics": report,
            "reducer": reduced,
        }

    finally:
        if connection is None:
            print("[CLEANUP] connection was never created")
        else:
            connection.close()

def build_context(args):
    profiles, exclude = load_analysis_profiles(get_config_path())
    include = profiles["full_runtime"]["include"]
    PROJECT_PREFIXES = build_project_prefixes(include)

    raw_root = profiles.get("project_root", ".")

    analysis_root = resolve_project_root(args.path or raw_root)

    db_path = (
        Path(args.database)
        if args.database is not None
        else Path(
            str(analysis_root)
            .replace("/", "_")
            .replace("\\", "_")
            + ".db"
        )
    )

    if db_path.exists():
        print(f"[RESET DB] {db_path}")
        db_path.unlink()

    return PipelineContext(
        project_root=analysis_root,
        db_path=db_path,
        project_prefixes=PROJECT_PREFIXES,
    )


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Root path to analyze")
    parser.add_argument("--database", default="tools/analysis/data/analysis.db")

    args = parser.parse_args()

    ctx = build_context(args)

    run_analysis_pipeline(
        project_root=ctx.project_root,
        database_path=ctx.db_path,
        project_prefixes=ctx.project_prefixes,
    )