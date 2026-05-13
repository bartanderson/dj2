# tools/analysis/tests/core/test_symbol_reconciliation.py

from tools.analysis.persistence.persist_file_analysis import create_database

DB_PATH = "tools/analysis/data/analysis.db"


def test_symbol_reconciliation_dump():
    db = create_database(DB_PATH)
    c = db.cursor()

    # -------------------------
    # 1. Ground truth symbols
    # -------------------------
    c.execute("SELECT DISTINCT name FROM symbols")
    symbols = {r[0] for r in c.fetchall()}

    # -------------------------
    # 2. All references
    # -------------------------
    c.execute("SELECT DISTINCT callee FROM symbol_references")
    refs = [r[0] for r in c.fetchall()]

    # -------------------------
    # 3. Normalize + compare
    # -------------------------
    unresolved = []

    for r in refs:
        leaf = r.split(".")[-1]
        if leaf not in symbols:
            unresolved.append(r)

    # -------------------------
    # 4. Debug output (only if failure)
    # -------------------------
    if unresolved:
        print("\n=== UNRESOLVED SYMBOLS ===")
        for u in unresolved[:100]:
            print(u)

    assert unresolved == []