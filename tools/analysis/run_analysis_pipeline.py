# tools/analysis/run_analysis_pipeline.py
from __future__ import annotations

from pathlib import Path

from tools.analysis.ingestion.scan_project_files import (
    scan_project_files,
)
from tools.analysis.persistence.persist_file_analysis import (
    create_database,
    persist_file_analysis,
)

def run_analysis_pipeline(
    project_root: str | Path,
    database_path: str | Path,
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
        for analysis in scan_project_files(project_root):
            persist_file_analysis(connection, analysis)
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
        "project_root",
        help="Root directory of project to analyze",
    )

    parser.add_argument(
        "--database",
        default="tools/analysis/data/analysis.db",
        help="SQLite database path",
    )

    args = parser.parse_args()

    run_analysis_pipeline(
        project_root=args.project_root,
        database_path=args.database,
    )