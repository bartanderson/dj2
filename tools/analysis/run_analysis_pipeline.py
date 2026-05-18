# tools/analysis/run_analysis_pipeline.py
from __future__ import annotations

import os
from pathlib import Path
from tools.analysis.load_config_profiles import (
    load_analysis_profiles,
    build_profile_prefixes,
)

from tools.analysis.ingestion.scan_project_files import (
    scan_project_files,
)
from tools.analysis.persistence.persist_file_analysis import (
    create_database,
    persist_file_analysis,
)

from tools.analysis.graph.project_context import build_project_prefixes
from tools.analysis.core.pathing import (
    resolve_project_root,
)

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
) -> None:

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
            repo_root=repo_root,   # 👈 ADD THIS
        ):
            persist_file_analysis(connection, analysis, project_prefixes)
            file_analyses.append(analysis)

            processed_count += 1

            if processed_count % 25 == 0:
                print(f"Processed {processed_count} files...")

    finally:
        connection.close()

    print(f"Analysis complete. Processed {processed_count} files.")


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