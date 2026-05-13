# tools/analysis/tests/core/test_graph_integrity.py

from tools.analysis.persistence.persist_file_analysis import create_database


def test_symbol_references_have_no_duplicates():
    db = create_database("tools/analysis/data/analysis.db")
    c = db.cursor()

    c.execute("""
    SELECT
        caller,
        callee,
        line_number,
        COUNT(*)
    FROM symbol_references
    GROUP BY caller, callee, line_number
    HAVING COUNT(*) > 1
    """)

    duplicates = c.fetchall()

    assert duplicates == [], f"Duplicate symbol references found: {duplicates}"


def test_symbol_references_are_project_scoped():
    db = create_database("tools/analysis/data/analysis.db")
    c = db.cursor()

    c.execute("""
    SELECT DISTINCT callee
    FROM symbol_references
    """)

    rows = [r[0] for r in c.fetchall()]

    invalid = []

    for name in rows:
        if not name.startswith("tools."):
            invalid.append(name)

    assert invalid == [], f"Non-project symbols found: {invalid}"