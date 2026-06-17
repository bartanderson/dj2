# tools/analysis/tests/core/test_symbol_uniqueness.py
#
# CLAUDE-EDIT 2026-06-17: same fix as test_symbol_classification_contract.py
# - stale import + create_database()'s unconditional wipe-on-open meant
# this was silently asserting against an empty DB. Now reads
# SHARED_TEST_DB_PATH without wiping it; skips with a clear reason if
# test_engine_smoke.py hasn't populated it yet.
#
# CLAUDE-EDIT 2026-06-17 (later same day): once persistence_engine.py's
# dead bucket-gate was fixed and `symbols` started holding real
# function/class declarations for the first time ever, this test's
# GROUP BY (file_path, name) started flagging real but legitimate cases:
# e.g. two different classes in the same file each defining their own
# __init__, or a module defining same-named methods on separate classes
# (confirmed via direct query: every flagged case was at a different
# line_number - e.g. db_oracle.py's two `surface` methods at lines 114
# and 779 belong to two different classes). FunctionRepresentation/
# ClassRepresentation don't track containing-class scope, so file+name
# alone can't distinguish "two methods that happen to share a name" from
# "the same declaration inserted twice". Added symbol_type and
# line_number to the GROUP BY so this checks true duplicates (the same
# declaration recorded more than once) - which the `symbols` table's
# UNIQUE canonical_id constraint already prevents at insert time, so
# this is now primarily a regression guard against that constraint ever
# being loosened or canonical_id's definition changing.

import os
import sqlite3

import pytest

from tools.analysis.tests.core.test_db_utils import SHARED_TEST_DB_PATH


def test_symbol_uniqueness():
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

        c.execute("""
            SELECT file_path, symbol_type, name, line_number, COUNT(*)
            FROM symbols
            GROUP BY file_path, symbol_type, name, line_number
            HAVING COUNT(*) > 1
        """)

        dupes = c.fetchall()

        assert dupes == [], f"Duplicate symbols found: {dupes}"
    finally:
        if db is not None:
            db.close()
