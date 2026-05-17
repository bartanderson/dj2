#tools/analysis/tests/core/test_symbol_storage_format.py

from tools.analysis.tests.core.test_db_utils import reset_analysis_db
from tools.analysis.persistence.persist_file_analysis import create_database

DB_PATH = "tools/analysis/data/analysis.db"

def test_symbols_are_stored_as_short_names():
    try:
        reset_analysis_db() # delete db for data isolation per run
        db = create_database(DB_PATH)
        c = db.cursor()

        c.execute("""
        SELECT DISTINCT name
        FROM symbols
        """)

        names = [r[0] for r in c.fetchall()]

        fully_qualified = [
            n for n in names
            if "." in n
        ]

        assert fully_qualified == [], (
            "Symbols should currently be stored as short names only:\n"
            + "\n".join(fully_qualified)
        )
    finally:
        db.close()