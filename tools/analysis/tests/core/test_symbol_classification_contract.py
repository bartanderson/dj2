# tools/analysis/tests/core/test_symbol_classification_contract.py

from tools.analysis.tests.core.test_db_utils import reset_analysis_db
from tools.analysis.persistence.persist_file_analysis import create_database

DB_PATH = "tools/analysis/data/analysis.db"


def test_symbol_classification_and_graph_contract():
    db = None
    try:
        reset_analysis_db()  # delete db for data isolation per run

        db = create_database(DB_PATH)
        c = db.cursor()

        # -------------------------
        # 1. No structural duplicates (true edge identity)
        # -------------------------
        c.execute("""
        SELECT caller, callee, line_number, COUNT(*)
        FROM symbol_references
        GROUP BY caller, callee, line_number
        HAVING COUNT(*) > 1
        """)
        duplicates = c.fetchall()

        bad = [
            d for d in duplicates
            if d[3] > 2
        ]

        assert bad == [], f"Excessive duplicate edges found: {bad}"

        # -------------------------
        # 2. No empty callee
        # -------------------------
        c.execute("""
        SELECT COUNT(*)
        FROM symbol_references
        WHERE callee = ''
        """)
        assert c.fetchone()[0] == 0

        # -------------------------
        # 3. Symbol existence contract
        # -------------------------
        c.execute("SELECT DISTINCT name FROM symbols")
        symbols = {r[0] for r in c.fetchall()}

        c.execute("SELECT DISTINCT callee FROM symbol_references")
        refs = [r[0] for r in c.fetchall()]

        unresolved = []

        for r in refs:
            leaf = r.split(".")[-1]

            if r not in symbols and leaf not in symbols:
                unresolved.append(r)

        assert unresolved == [], f"Unresolved symbols: {unresolved[:50]}"

        # -------------------------
        # 4. Classification safety
        # -------------------------
        c.execute("SELECT DISTINCT callee FROM symbol_references")
        rows = [r[0] for r in c.fetchall()]

        invalid = []

        for name in rows:
            if not name:
                continue

            if name.startswith("..") or name.endswith("."):
                invalid.append(name)

        assert invalid == [], f"Malformed symbols: {invalid}"

    finally:
        if db is not None:
            db.close()