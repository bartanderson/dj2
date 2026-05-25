from tools.analysis.run_analysis_pipeline import run_analysis_pipeline
from tools.analysis.tests.core.test_db_utils import reset_analysis_db
from tools.analysis.persistence.persist_file_analysis import create_database
from tools.analysis.graph.project_context import build_project_prefixes

DB_PATH = "tools/analysis/data/analysis.db"


def test_full_pipeline_runs_without_crashing():
    db = None
    try:
        reset_analysis_db()

        # minimal valid project context (NO external dependency)
        project_prefixes = {"tools"}

        project_prefixes = build_project_prefixes("tools")

        run_analysis_pipeline(
            "tools",
            DB_PATH,
            project_prefixes,
        )

        db = create_database(DB_PATH)
        c = db.cursor()

        c.execute("SELECT COUNT(*) FROM symbol_references")
        count = c.fetchone()[0]

        assert isinstance(count, int)
        assert count is not None
    finally:
        if db:
            db.close()