# tools/analysis/run_analysis_pipeline.py
from __future__ import annotations

import os
from pathlib import Path
from tools.analysis.load_config_profiles import load_analysis_profiles

from tools.analysis.ingestion.scan_project_files import (
    scan_project_files,
)
from tools.analysis.persistence.persist_file_analysis import (
    create_database,
    persist_file_analysis,
)
from tools.analysis.load_config_profiles import build_project_prefixes

def get_config_path():
    # repo root = two levels up from this file
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "config" / "analysis_profiles.yaml"

def resolve_project_root(cfg_root: str) -> Path:
    if cfg_root == ".":
        return Path.cwd()

    # allow env override for portability
    if cfg_root.startswith("${") and cfg_root.endswith("}"):
        env_key = cfg_root[2:-1]
        return Path(os.environ.get(env_key, Path.cwd()))

    return Path(cfg_root)

def run_analysis_pipeline(
    project_root: str | Path,
    database_path: str | Path,
    project_prefixes: list[str],
) -> None:
    """
    High-level deterministic analysis pipeline.

    Pipeline:
        filesystem
            ↓
        AST parsing
            ↓
        FileAnalysis generation
            ↓
        persistence

    This is intentionally minimal and boring.
    """

    connection = create_database(database_path)

    processed_count = 0

    file_analyses = []

    try:
        for analysis in scan_project_files(project_root, project_prefixes):
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

    parser.add_argument(
        "--database",
        default="tools/analysis/data/analysis.db",
        help="SQLite database path",
    )

    args = parser.parse_args()

    profiles, exclude = load_analysis_profiles(get_config_path())
    include = profiles["analysis_systems"]["include"]
    PROJECT_PREFIXES = build_project_prefixes(include)

    raw_root = profiles.get("project_root", ".")
    project_root = resolve_project_root(raw_root)

    run_analysis_pipeline(
        project_root=project_root,
        database_path=args.database,
        project_prefixes=PROJECT_PREFIXES,
    )