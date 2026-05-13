#tools/analysis/tests/core/test_symbol_storage_format.py

from tools.analysis.persistence.persist_file_analysis import create_database


def test_symbols_are_stored_as_short_names():
    db = create_database("tools/analysis/data/analysis.db")
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