# tools/analysis/tests/core/test_symbol_uniqueness.py

from tools.analysis.persistence.persist_file_analysis import create_database

DB_PATH = "tools/analysis/data/analysis.db"


def test_symbol_uniqueness():
    db = create_database(DB_PATH)
    c = db.cursor()

    c.execute("""
        SELECT file_path, name, COUNT(*)
        FROM symbols
        GROUP BY file_path, name
        HAVING COUNT(*) > 1
    """)

    dupes = c.fetchall()

    assert dupes == [], f"Duplicate symbols found: {dupes}"