# tools/analysis/tests/core/test_symbol_graph_integrity.py

from tools.analysis.persistence.persist_file_analysis import create_database

DB_PATH = "tools/analysis/data/analysis.db"


def test_no_self_noise_and_valid_edges():
    db = create_database(DB_PATH)
    c = db.cursor()

    # 1. No empty callee
    c.execute("SELECT COUNT(*) FROM symbol_references WHERE callee = ''")
    assert c.fetchone()[0] == 0

    # 2. No module-like callee leakage
    c.execute("SELECT DISTINCT callee FROM symbol_references")
    bad = [r[0] for r in c.fetchall() if "." in r[0] and not r[0].startswith("tools.")]
    
    assert bad == [], f"Bad callee formats: {bad}"