# tools/analysis/tests/core/test_reference_extraction_integrity.py

from collections import Counter

from tools.analysis.run_analysis_pipeline import run_analysis_pipeline
from tools.analysis.tests.core.test_db_utils import reset_analysis_db
from tools.analysis.persistence.persist_file_analysis import create_database
from tools.analysis.graph.project_context import build_project_prefixes


DB_PATH = "tools/analysis/data/analysis.db"


def test_reference_extraction_has_no_excessive_duplicates():

    db = None

    try:
        reset_analysis_db()

        project_prefixes = build_project_prefixes("tools")

        run_analysis_pipeline(
            "tools",
            DB_PATH,
            project_prefixes,
        )

        db = create_database(DB_PATH)
        c = db.cursor()

        c.execute("""
        SELECT caller, callee, line_number
        FROM symbol_references
        """)

        rows = c.fetchall()

        counts = Counter(rows)

        excessive = [
            (k, v)
            for k, v in counts.items()
            if v > 1
        ]

        assert excessive == [], f"Duplicate semantic edges: {excessive[:25]}"

    finally:
        if db:
            db.close()