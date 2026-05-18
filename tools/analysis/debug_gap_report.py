# tools/analysis/debug_gap_report.py

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path


def normalize(name: str) -> str:
    if not name:
        return name
    return name.replace("<module>.", "").strip()


def project_key(name: str) -> str:
    return name.split(".")[-1]


def load_gap_rows(conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.execute("""
        SELECT caller, callee, line_number
        FROM symbol_references
        WHERE bucket = 'classification_gap'
    """)

    return cur.fetchall()


def load_global_symbols(conn: sqlite3.Connection):
    """
    Extract GLOBAL SYMBOLS indirectly from DB.
    We reconstruct from all project-classified symbols.
    """

    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM symbols
    """)

    return set(r[0] for r in cur.fetchall())


def classify_gap(caller, callee, global_symbols: set[str]):
    raw = callee
    norm = normalize(callee)

    leaf = project_key(norm)

    if raw in global_symbols or norm in global_symbols:
        return "MISSING_PROJECT_MATCH"

    if leaf in {project_key(s) for s in global_symbols}:
        return "NORMALIZATION_MISMATCH"

    if callee in {"print", "len", "sum", "exec"}:
        return "RUNTIME_OR_BUILTIN"

    return "TRULY_UNKNOWN"


def run(db_path: str):
    conn = sqlite3.connect(db_path)

    gaps = load_gap_rows(conn)
    globals_ = load_global_symbols(conn)

    breakdown = defaultdict(int)
    samples = defaultdict(list)

    for caller, callee, line in gaps:

        category = classify_gap(caller, callee, globals_)

        breakdown[category] += 1

        if len(samples[category]) < 10:
            samples[category].append({
                "caller": caller,
                "callee": callee,
                "line": line,
            })

    print("\n===== GAP ROOT CAUSE BREAKDOWN =====\n")

    for k, v in breakdown.items():
        print(f"{k}: {v}")

    print("\n===== SAMPLE CASES =====\n")

    for k, items in samples.items():
        print(f"\n--- {k} ---")
        for i in items:
            print(i)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python debug_gap_report.py <db_path>")
        raise SystemExit(1)

    run(sys.argv[1])