# tools/analysis/tests/core/test_symbol_resolution.py
#
# CLAUDE-EDIT 2026-06-17: same fix as test_symbol_classification_contract.py
# - stale import + create_database()'s unconditional wipe-on-open meant
# this was silently asserting against an empty DB. Now reads
# SHARED_TEST_DB_PATH without wiping it; skips with a clear reason if
# test_engine_smoke.py hasn't populated it yet.
#
# CLAUDE-EDIT 2026-06-17 (later same day): once persistence_engine.py's
# dead bucket-gate was fixed and `symbols` started holding real
# function/class declarations, this test's "every callee must resolve"
# check needed the same fix as test_symbol_classification_contract.py's
# check #3 - restricted to bucket = 'project' callees, since stdlib/
# builtin/external references were never going to resolve against our
# own declarations table and that's expected, not a bug. Confirmed
# empirically: 0 unresolved once restricted to project-bucket callees.

import os
import sqlite3

import pytest

from tools.analysis.tests.core.test_db_utils import SHARED_TEST_DB_PATH


def test_all_symbol_references_resolve_to_known_symbols():
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

        # all declared symbols
        c.execute("""
        SELECT DISTINCT name
        FROM symbols
        """)

        known_symbols = {r[0] for r in c.fetchall()}

        # Only project-bucket callees are declarations we could possibly
        # have recorded in `symbols` ourselves. See CLAUDE-EDIT comment
        # at the top of this file.
        c.execute("""
        SELECT DISTINCT callee
        FROM symbol_references
        WHERE bucket = 'project'
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
    finally:
        if db is not None:
            db.close()
