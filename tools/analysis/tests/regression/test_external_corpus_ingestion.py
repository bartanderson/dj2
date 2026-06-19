# tools/analysis/tests/regression/test_external_corpus_ingestion.py
#
# Closes TRACKER.md section 3 item 1's verification bar for "widening the
# ingestion test corpus": tools.old/, external_corpora/flask/src, and
# external_corpora/sqlalchemy/lib have now all been ingested at least once
# (2026-06-19 session) - this is the permanent regression proof for the
# first corpus ingested (tools.old/), the one TRACKER's "if multiple
# candidates, verify whichever lands first" bar applies to.
#
# Runs a real EngineRunner over the real, in-repo tools.old/ directory (73
# .py files) into a temp sqlite DB (same OS-temp-dir convention as
# test_engine_smoke.py's SHARED_TEST_DB_PATH, for the same reason: never
# collide with a real product DB, and avoid this sandbox's mount-specific
# sqlite write issues entirely rather than work around them - see
# TRACKER.md section 2 for that standing defect, which is sandbox-local,
# not a project bug, so it is not worked around inside product code).
#
# Verifies a known, hand-checked real call site survives the full
# ingestion pipeline (scan -> classify -> graph build -> persist) and
# lands correctly in BOTH symbol_references and graph_edges:
# tools.old/agent.py's run_orchestrated_agent() calls setup_logging() at
# line 258 (and again at line 288, after the complex-path branch) -
# confirmed by direct inspection of the source file before writing this
# assertion.

import os
import sqlite3
import tempfile

from tools.analysis.engine.run_engine import EngineRunner
from tools.analysis.persistence.persistence_engine import create_database


def _ingest_tools_old():
    db_path = tempfile.mktemp(suffix=".db")
    db = create_database(db_path)

    corpus = type("Corpus", (), {"root_path": "tools.old"})()
    EngineRunner().run(
        corpus=corpus,
        project_prefixes=[],
        repo_root=".",
        connection=db,
    )
    db.close()
    return db_path


def test_tools_old_ingestion_produces_edges():
    db_path = _ingest_tools_old()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM files")
        assert cur.fetchone()[0] == 73

        cur.execute("SELECT COUNT(*) FROM symbol_references")
        assert cur.fetchone()[0] > 0

        cur.execute("SELECT COUNT(*) FROM graph_edges")
        assert cur.fetchone()[0] > 0

        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_known_real_symbol_appears_in_graph_edges():
    # run_orchestrated_agent() -> setup_logging() at tools.old/agent.py
    # line 258 (and line 288) - both call sites must survive ingestion.
    db_path = _ingest_tools_old()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute(
            "SELECT line_number FROM graph_edges "
            "WHERE caller = ? AND callee = ? ORDER BY line_number",
            ("run_orchestrated_agent", "setup_logging"),
        )
        lines = [r[0] for r in cur.fetchall()]
        assert lines == [258, 288]

        # same call sites must also be classified in symbol_references
        # (graph_edges and symbol_references are two persisted views of
        # the same ingestion run; both must agree)
        cur.execute(
            "SELECT line_number FROM symbol_references "
            "WHERE caller = ? AND callee = ? ORDER BY line_number",
            ("run_orchestrated_agent", "setup_logging"),
        )
        lines2 = [r[0] for r in cur.fetchall()]
        assert lines2 == [258, 288]

        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    test_tools_old_ingestion_produces_edges()
    test_known_real_symbol_appears_in_graph_edges()
    print("OK")
