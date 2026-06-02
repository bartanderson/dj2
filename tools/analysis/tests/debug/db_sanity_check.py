# tools/analysis/db_sanity_check.py

import sys
import sqlite3
from pathlib import Path


TABLES = [
    "files",
    "functions",
    "classes",
    "imports",
    "file_edges",
    "behavioral_contracts",
    "mutations",
    "symbols",
    "symbol_references",
]


def count(cursor, table: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]


def main(db_path: str):
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    print("\n================ DB SANITY CHECK ================\n")

    totals = {}

    # ----------------------------
    # TABLE POPULATION CHECK
    # ----------------------------
    for t in TABLES:
        try:
            c = count(cur, t)
        except Exception as e:
            print(f"❌ {t}: ERROR ({e})")
            continue

        totals[t] = c

        status = "✔" if c > 0 else "⚠"
        print(f"{status} {t:25} {c}")

    print("\n---------------- EDGE VALIDATION ----------------")

    edges = totals.get("file_edges", 0)
    symrefs = totals.get("symbol_references", 0)

    print(f"file_edges           : {edges}")
    print(f"symbol_references    : {symrefs}")

    if symrefs == 0:
        print("\n❌ CRITICAL: symbol_references is EMPTY")
    else:
        ratio = edges / symrefs if symrefs else 0
        print(f"edge/ref ratio       : {ratio:.2f}")

        if ratio < 1:
            print("⚠ WARNING: more symbol refs than edges (unexpected)")
        elif ratio > 20:
            print("⚠ WARNING: very sparse symbol coverage")

    print("\n---------------- SYMBOL COVERAGE ----------------")

    symbols = totals.get("symbols", 0)

    if symbols == 0:
        print("⚠ symbols table empty or filtered")
    else:
        print(f"symbols: {symbols}")

    print("\n---------------- FINAL HEALTH ----------------")

    critical_missing = symrefs == 0 or totals.get("files", 0) == 0

    if critical_missing:
        print("❌ PIPELINE STATE: DEGRADED")
    else:
        print("✔ PIPELINE STATE: OK")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python db_sanity_check.py <db_path>")
        sys.exit(1)

    main(sys.argv[1])