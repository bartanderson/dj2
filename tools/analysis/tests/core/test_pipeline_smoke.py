from tools.analysis.run_analysis_pipeline import run_analysis_pipeline
from tools.analysis.persistence.persist_file_analysis import create_database


def test_full_pipeline_runs_without_crashing():
    db_path = "tools/analysis/data/analysis.db"

    run_analysis_pipeline("tools", db_path)

    db = create_database(db_path)
    c = db.cursor()

    c.execute("SELECT COUNT(*) FROM symbol_references")
    count = c.fetchone()[0]

    assert count > 0