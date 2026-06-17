from tools.analysis.engine.run_engine import EngineRunner
from tools.analysis.tests.core.test_db_utils import reset_analysis_db, SHARED_TEST_DB_PATH
from tools.analysis.persistence.persistence_engine import (
    create_database,
    initialize_database,
)
from tools.analysis.graph.project_context import build_project_prefixes

# CLAUDE-EDIT 2026-06-17: import was from the now-deleted
# tools.analysis.persistence.persist_file_analysis - create_database/
# initialize_database live in persistence_engine.py now (same names, same
# behavior, just consolidated into one module). DB_PATH was a hardcoded
# in-repo path whose directory doesn't exist in this checkout and which
# nothing live references; moved to SHARED_TEST_DB_PATH (OS temp dir, see
# test_db_utils.py) so this can never collide with a real product DB. This
# test is the data producer for test_symbol_*.py, which assert against the
# same SHARED_TEST_DB_PATH without re-running the engine.


def test_engine_runs_without_crashing():

    db = None

    try:

        reset_analysis_db()

        project_prefixes = build_project_prefixes("tools")

        db = create_database(SHARED_TEST_DB_PATH)

        initialize_database(db)

        corpus = type(
            "Corpus",
            (),
            {"root_path": "tools"},
        )()

        runner = EngineRunner()

        runner.run(
            corpus=corpus,
            project_prefixes=project_prefixes,
            repo_root=".",
            connection=db,
        )

        c = db.cursor()

        c.execute(
            "SELECT COUNT(*) FROM symbol_references"
        )
        print("got here")
        count = c.fetchone()[0]

        assert isinstance(count, int)
        assert count > 0

    finally:

        if db:
            db.close()
        # CLAUDE-EDIT 2026-06-17: intentionally NOT deleting
        # SHARED_TEST_DB_PATH here - test_symbol_*.py read it after this
        # test runs (see test_db_utils.py docstring for the ordering
        # dependency this relies on).
