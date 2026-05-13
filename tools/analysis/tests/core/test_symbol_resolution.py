# tools/analysis/tests/core/test_symbol_resolution.py

from tools.analysis.persistence.persist_file_analysis import create_database


def test_all_symbol_references_resolve_to_known_symbols():
    db = create_database("tools/analysis/data/analysis.db")
    c = db.cursor()

    # all declared symbols
    c.execute("""
    SELECT DISTINCT name
    FROM symbols
    """)

    known_symbols = {r[0] for r in c.fetchall()}

    # all referenced callees
    c.execute("""
    SELECT DISTINCT callee
    FROM symbol_references
    """)

    callees = [r[0] for r in c.fetchall()]

    unresolved = []

    for callee in callees:
        short_name = callee.split(".")[-1]

        if short_name not in known_symbols:
            unresolved.append(callee)

    assert unresolved == [], (
        "Unresolved symbol references found:\n"
        + "\n".join(unresolved)
    )