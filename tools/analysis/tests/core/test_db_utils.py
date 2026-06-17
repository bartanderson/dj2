# tools/analysis/tests/core/test_db_utils.py
#
# CLAUDE-EDIT 2026-06-17: was a hardcoded in-repo path
# ("tools/analysis/data/analysis.db") whose parent directory doesn't even
# exist in this checkout, and which nothing live references (confirmed via
# repo-wide grep before this change) - so it carried zero risk of colliding
# with a real product DB, but also could never have worked as-is (sqlite3
# can't create a file under a missing directory). Moved into the OS temp
# dir instead, both to fix that and to make it categorically impossible for
# this shared test-only DB to ever be confused with a real product DB path,
# even if "tools/analysis/data/" gets created later for an unrelated reason.
#
# This file populates SHARED_TEST_DB_PATH once via test_engine_smoke.py (a
# real engine run against the "tools" corpus); test_symbol_*.py then assert
# against that same data rather than each re-running the engine themselves.
# Relies on pytest's default alphabetical collection order within
# tests/core/ (test_engine_smoke.py sorts before test_symbol_*.py) - see the
# 2026-06-17 REFACTOR OPS BOARD.md entry for the full writeup of this
# ordering dependency and why it was left as-is rather than restructured
# into an explicit fixture.

import os
import tempfile

SHARED_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "dj2_analysis_engine_smoke_test.db")


def reset_analysis_db():
    if os.path.exists(SHARED_TEST_DB_PATH):
        os.remove(SHARED_TEST_DB_PATH)
