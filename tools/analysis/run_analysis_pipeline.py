# tools/analysis/run_analysis_pipeline.py
from __future__ import annotations

import os
from pathlib import Path
from tools.analysis.load_config_profiles import (load_analysis_profiles, build_profile_prefixes)
from tools.analysis.ingestion.scan_project_files import (scan_project_files)
from tools.analysis.persistence.persist_file_analysis import (create_database,persist_file_analysis)
from tools.analysis.graph.project_context import build_project_prefixes
from tools.analysis.core.pathing import (resolve_project_root)
from tools.analysis.metrics.extract_metrics import extract_metrics

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

def run_analysis_pipeline(
    project_root: str | Path,
    database_path: str | Path,
    project_prefixes: list[str],
) -> dict:

    graph_edge_count = 0

    project_root = Path(project_root).resolve()
    repo_root = resolve_repo_root(project_root)

    if not project_prefixes:
        from tools.analysis.graph.project_context import build_project_prefixes
        project_prefixes = build_profile_prefixes(project_root)

    connection = create_database(database_path)

    processed_count = 0

    file_analyses = []

    try:
        for analysis in scan_project_files(
            project_root,
            project_prefixes,
            repo_root=repo_root,
        ):
            # ============================
            # PERSIST + CAPTURE SNAPSHOT
            # ============================
            snapshot = persist_file_analysis(
                connection,
                analysis,
                project_prefixes,
            )

            # ============================
            # STORE SNAPSHOT (NOT RAW OBJECT)
            # ============================
            file_analyses.append(snapshot)
            assert isinstance(snapshot, dict)

            print("\n[ASSERT 4 - PIPELINE COLLECTION]")
            print("snapshot keys:", snapshot.keys())

            bs = snapshot.get("bucket_summary", None)
            assert bs is not None, "Missing bucket_summary in snapshot"

            print("bucket_summary:", bs)

            processed_count += 1


            # ============================
            # FILE CONTEXT (LAYER 1)
            # ============================
            print("\n" + "=" * 90)
            print("FILE:", getattr(analysis, "file_path", None))

            analysis_edges = getattr(analysis, "graph_edge_count", 0)

            print("RAW ANALYSIS (L1):")
            print("  functions:", len(getattr(analysis, "functions", [])))
            print("  imports:", len(getattr(analysis, "imports", [])))
            print("  symbol_refs:", len(getattr(analysis, "symbol_references", [])))
            print("  graph_edge_count:", analysis_edges)

            # ============================
            # SNAPSHOT OUTPUT (LAYER 2)
            # ============================
            snapshot_edges = snapshot.get("edge_count", 0)
            snapshot_bucket = snapshot.get("bucket_summary", {})

            print("\nSNAPSHOT (L2):")
            print("  edge_count:", snapshot_edges)
            print("  bucket_summary:", snapshot_bucket)

            # ============================
            # CONSISTENCY CHECK (THIS IS WHAT YOU WERE MISSING)
            # ============================
            print("\nCONSISTENCY CHECK:")
            print("  analysis vs snapshot edges:", analysis_edges, "->", snapshot_edges)

            if analysis_edges != snapshot_edges:
                print("⚠ CRITICAL INVARIANT FAILURE")
                print("analysis:", analysis_edges)
                print("snapshot:", snapshot_edges)

            print("=" * 90)


    finally:
        connection.close()

    snapshot  = {
        "file_count": processed_count,
        "file_analyses": file_analyses,
        "edge_count": graph_edge_count,  # temporary placeholder until we fix graph accumulation
    }

    print("\n" + "=" * 90)
    print("PIPELINE SEMANTIC SUMMARY")

    print("files:", len(file_analyses))
    print("edges:", graph_edge_count)

    print("\n" + "=" * 80)
    print("PIPELINE → METRICS BOUNDARY")
    print("files:", len(file_analyses))

    total_edges = 0
    total_classification_gap = 0
    total_builtin = 0

    print("\n" + "=" * 80)
    print("STEP 5: REDUCER TRACE START")

    reduced_edges = 0
    reduced_gap = 0
    reduced_builtin = 0

    for i, snap in enumerate(file_analyses):

        print("\n[REDUCE STEP]", i)

        print("snapshot id:", snap.get("file_path", f"file_{i}"))

        edge = snap.get("edge_count", 0)
        bs = snap.get("bucket_summary", {})

        gap = bs.get("classification_gap", 0)
        builtin = bs.get("builtin", 0)
        project = bs.get("project", 0)

        print("incoming values:")
        print("  edge:", edge)
        print("  gap:", gap)
        print("  builtin:", builtin)
        print("  project:", project)

        # ---- FOLD STEP ----
        before = (reduced_edges, reduced_gap, reduced_builtin)

        reduced_edges += edge
        reduced_gap += gap
        reduced_builtin += builtin

        after = (reduced_edges, reduced_gap, reduced_builtin)

        print("fold:")
        print("  before:", before)
        print("  after:", after)

    print("\nFINAL REDUCED STATE")
    print("edges:", reduced_edges)
    print("gap:", reduced_gap)
    print("builtin:", reduced_builtin)
    print("=" * 80)

    print("\n[STEP 6 - FINAL INVARIANT CHECK]")

    assert reduced_edges >= 0, "edges negative?"
    assert reduced_gap >= 0, "gap negative?"
    assert reduced_builtin >= 0, "builtin negative?"

    # structural sanity
    assert reduced_edges > 0 or len(file_analyses) == 0, (
        "No edges found despite snapshots existing"
    )

    print("✔ reducer invariants passed")

    print("\nAGGREGATED PREVIEW (first 3 files only)")
    print("edges:", total_edges)
    print("classification_gap:", total_classification_gap)
    print("builtin:", total_builtin)

    print("=" * 80 + "\n")

    report = extract_metrics(file_analyses)

    print("Analysis complete. Processed", processed_count, "files.")

    return report

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Root path to analyze")
    parser.add_argument(
        "--database",
        default="tools/analysis/data/analysis.db",
    )

    args = parser.parse_args()

    profiles, exclude = load_analysis_profiles(get_config_path())
    include = profiles["full_runtime"]["include"]
    PROJECT_PREFIXES = build_project_prefixes(include)

    raw_root = profiles.get("project_root", ".")

    root_input = args.path if args.path else raw_root
    analysis_root = resolve_project_root(
        args.path if args.path else profiles.get("project_root", ".")
    )

    Path(args.database).unlink(missing_ok=True)

    run_analysis_pipeline(
        project_root=analysis_root,
        database_path=args.database,
        project_prefixes=PROJECT_PREFIXES,
    )