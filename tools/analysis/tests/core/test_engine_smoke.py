from tools.analysis.engine.run_engine import EngineRunner
from tools.analysis.tests.core.test_db_utils import reset_analysis_db
from tools.analysis.persistence.persist_file_analysis import (
    create_database,
    initialize_database,
)
from tools.analysis.graph.project_context import build_project_prefixes

DB_PATH = "tools/analysis/data/analysis.db"


def test_engine_runs_without_crashing():

    db = None

    try:

        reset_analysis_db()

        project_prefixes = build_project_prefixes("tools")

        db = create_database(DB_PATH)

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