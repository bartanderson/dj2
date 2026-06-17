# tools/analysis/tests/core/test_symbol_classification_contract.py
#
# CLAUDE-EDIT 2026-06-17: was importing create_database from the
# now-deleted persist_file_analysis module and calling it against a
# hardcoded in-repo DB_PATH - but create_database() unconditionally
# deletes-then-recreates the target file (persistence_engine.py:515), so
# this test was silently wiping test_engine_smoke.py's data and then
# asserting against an empty DB every time (vacuously true: no rows means
# no duplicates, no unresolved symbols, etc. - same "looks green, tests
# nothing" shape as the drift_signals/orphaned-Filter bugs fixed elsewhere
# in this codebase). Fixed by opening SHARED_TEST_DB_PATH read-only
# (plain sqlite3.connect, no wipe) instead of calling create_database.
# If the smoke test hasn't populated it yet, this now skips with a clear
# reason instead of silently passing on empty data.
#
# CLAUDE-EDIT 2026-06-17 (later same day): two more real bugs surfaced
# once persistence_engine.py's dead bucket-gate was fixed (see that
# file's 2026-06-17 comments) and the `symbols` table started containing
# real function/class declarations for the first time ever:
#   1. Check #1's GROUP BY (caller, callee, line_number) was missing
#      file_path, so it flagged cross-file coincidences (different files
#      independently calling e.g. dataclasses.field() near the same line
#      number) as same-file duplicates. Confirmed via direct sqlite query
#      against the real corpus DB - added file_path to the GROUP BY.
#   2. Check #3 ("symbol existence contract") was checking that EVERY
#      referenced callee - including stdlib/builtin/external calls like
#      json.dumps or os.path.exists - resolves against the project's own
#      `symbols` declarations table. That's the wrong invariant: only
#      project-bucket references are declarations we could possibly have
#      recorded ourselves. Restricted the check to
#      `WHERE bucket = 'project'` (the same ingestion-time classification
#      already computed by classify_references.py). Confirmed empirically:
#      0 unresolved once restricted to project-bucket callees, vs. ~170
#      false positives (mostly builtins/stdlib) before this fix.

import os
import sqlite3

import pytest

from tools.analysis.tests.core.test_db_utils import SHARED_TEST_DB_PATH


def test_symbol_classification_and_graph_contract():
    if not os.path.exists(SHARED_TEST_DB_PATH):
        pytest.skip(
            "SHARED_TEST_DB_PATH not populated - run test_engine_smoke.py "
            "first (it builds this DB via a real engine run); this test "
            "only asserts against that data, it doesn't produce it."
        )

    db = None
    try:
        db = sqlite3.connect(SHARED_TEST_DB_PATH)
        c = db.cursor()

        # -------------------------
        # 1. No structural duplicates (true edge identity)
        # -------------------------
        c.execute("""
        SELECT file_path, caller, callee, line_number, COUNT(*)
        FROM symbol_references
        GROUP BY file_path, caller, callee, line_number
        HAVING COUNT(*) > 1
        """)
        duplicates = c.fetchall()

        bad = [
            d for d in duplicates
            if d[4] > 2
        ]

        assert bad == [], f"Excessive duplicate edges found: {bad}"

        # -------------------------
        # 2. No empty callee
        # -------------------------
        c.execute("""
        SELECT COUNT(*)
        FROM symbol_references
        WHERE callee = ''
        """)
        assert c.fetchone()[0] == 0

        # -------------------------
        # 3. Symbol existence contract
        # -------------------------
        c.execute("SELECT DISTINCT name FROM symbols")
        symbols = {r[0] for r in c.fetchall()}

        # Only project-bucket callees are declarations we could possibly
        # have recorded in `symbols` ourselves - builtin/stdlib/external
        # callees are expected to never resolve here. See CLAUDE-EDIT
        # comment at the top of this file.
        c.execute("SELECT DISTINCT callee FROM symbol_references WHERE bucket = 'project'")
        refs = [r[0] for r in c.fetchall()]

        unresolved = []

        for r in refs:
            leaf = r.split(".")[-1]

            if r not in symbols and leaf not in symbols:
                unresolved.append(r)

        assert unresolved == [], f"Unresolved symbols: {unresolved[:50]}"

        # -------------------------
        # 4. Classification safety
        # -------------------------
        c.execute("SELECT DISTINCT callee FROM symbol_references")
        rows = [r[0] for r in c.fetchall()]

        invalid = []

        for name in rows:
            if not name:
                continue

            if name.startswith("..") or name.endswith("."):
                invalid.append(name)

        assert invalid == [], f"Malformed symbols: {invalid}"

    finally:
        if db is not None:
            db.close()
