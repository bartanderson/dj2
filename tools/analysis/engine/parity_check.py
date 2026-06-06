# tools/analysis/engine/parity_check.py

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class ParityResult:
    engine_total: int
    db_total: int
    match: bool
    engine_by_file: dict[str, int] | None = None
    db_by_file: dict[str, int] | None = None
    file_mismatches: int | None = None


def load_db_totals(db_path: str) -> int:
    conn = sqlite3.connect(db_path)

    total = conn.execute(
        "SELECT COUNT(*) FROM symbol_references"
    ).fetchone()[0]

    conn.close()
    return total


def load_db_by_file(db_path: str) -> dict[str, int]:
    conn = sqlite3.connect(db_path)

    rows = conn.execute("""
        SELECT file_path, COUNT(*)
        FROM symbol_references
        GROUP BY file_path
    """).fetchall()

    conn.close()

    return {file_path: count for file_path, count in rows}


def compute_engine_total(result: Any) -> int:
    return result.facts["symbol_ref_count"]


def run_parity_check(db_path: str, engine_result: Any) -> ParityResult:
    db_total = load_db_totals(db_path)
    engine_total = compute_engine_total(engine_result)

    db_by_file = load_db_by_file(db_path)

    engine_by_file = {
        f.file_path: len(getattr(f, "symbol_references", []))
        for f in engine_result.ingestion["file_analyses"]
    }

    all_files = set(db_by_file) | set(engine_by_file)

    mismatches = 0

    for f in all_files:
        if db_by_file.get(f, 0) != engine_by_file.get(f, 0):
            mismatches += 1

    return ParityResult(
        engine_total=engine_total,
        db_total=db_total,
        match=(engine_total == db_total and mismatches == 0),
        engine_by_file=engine_by_file,
        db_by_file=db_by_file,
        file_mismatches=mismatches,
    )


def print_parity_report(result: ParityResult) -> None:
    print("\n=== PARITY CHECK ===")
    print("engine_total:", result.engine_total)
    print("db_total:", result.db_total)
    print("match:", result.match)

    if result.file_mismatches is not None:
        print("file_mismatches:", result.file_mismatches)