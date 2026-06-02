# tools/analysis/db_toolsold_audit.py

import sqlite3
import json
from pathlib import Path


def run_query(conn, label, sql):
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    return label, rows


def as_dict(label, rows):
    return {
        "query": label,
        "row_count": len(rows),
        "rows": rows
    }


def main(db_path: str):
    db_path = Path(db_path)

    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))

    results = {}

    # ---------------------------
    # 1. FILE COUNT
    # ---------------------------
    label, rows = run_query(conn, "total_files",
        "SELECT COUNT(*) FROM files;")
    results[label] = rows[0][0]

    # ---------------------------
    # 2. EDGE COUNT
    # ---------------------------
    label, rows = run_query(conn, "total_edges",
        "SELECT COUNT(*) FROM symbol_references;")
    results[label] = rows[0][0]

    # ---------------------------
    # 3. BUCKET DISTRIBUTION
    # ---------------------------
    label, rows = run_query(conn, "bucket_distribution",
        """
        SELECT bucket, COUNT(*)
        FROM symbol_references
        GROUP BY bucket
        ORDER BY COUNT(*) DESC;
        """)
    results[label] = rows

    # ---------------------------
    # 4. CLASSIFICATION GAPS
    # ---------------------------
    label, rows = run_query(conn, "classification_gaps",
        """
        SELECT COUNT(*)
        FROM symbol_references
        WHERE bucket = 'classification_gap'
           OR bucket IS NULL;
        """)
    results[label] = rows[0][0]

    # ---------------------------
    # 5. CALLER HOTSPOTS
    # ---------------------------
    label, rows = run_query(conn, "caller_hotspots",
        """
        SELECT caller, COUNT(*) as outgoing
        FROM symbol_references
        GROUP BY caller
        ORDER BY outgoing DESC
        LIMIT 20;
        """)
    results[label] = rows

    # ---------------------------
    # 6. CALLEE HOTSPOTS
    # ---------------------------
    label, rows = run_query(conn, "callee_hotspots",
        """
        SELECT callee, COUNT(*) as incoming
        FROM symbol_references
        GROUP BY callee
        ORDER BY incoming DESC
        LIMIT 20;
        """)
    results[label] = rows

    # ---------------------------
    # 7. BUCKET HEALTH CHECK
    # ---------------------------
    label, rows = run_query(conn, "bucket_health",
        """
        SELECT bucket, COUNT(*)
        FROM symbol_references
        WHERE bucket IN (
            'project',
            'builtin',
            'classification_gap',
            'external_lib',
            'runtime',
            'unresolved_qualified_reference'
        )
        GROUP BY bucket;
        """)
    results[label] = rows

    # ---------------------------
    # 8. FILE DENSITY
    # ---------------------------
    label, rows = run_query(conn, "file_density",
        """
        SELECT file_path, COUNT(*) as edges
        FROM symbol_references
        GROUP BY file_path
        ORDER BY edges DESC
        LIMIT 30;
        """)
    results[label] = rows

    # ---------------------------
    # 9. CONTRACT COVERAGE
    # ---------------------------
    label, rows = run_query(conn, "contract_coverage",
        """
        SELECT file_path, COUNT(*) as contracts
        FROM behavioral_contracts
        GROUP BY file_path
        ORDER BY contracts DESC;
        """)
    results[label] = rows

    # ---------------------------
    # OUTPUT
    # ---------------------------
    print("\n============================")
    print("TOOLS.OLD AUDIT REPORT")
    print("============================\n")

    print(json.dumps(results, indent=2))

    conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python db_toolsold_audit.py <db_path>")
        raise SystemExit(1)

    main(sys.argv[1])