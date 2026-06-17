#tools/analysis/tests/core/test_symbol_storage_format.py
#
# CLAUDE-EDIT 2026-06-17: same fix as test_symbol_classification_contract.py
# - stale import + create_database()'s unconditional wipe-on-open meant
# this was silently asserting against an empty DB. Now reads
# SHARED_TEST_DB_PATH without wiping it; skips with a clear reason if
# test_engine_smoke.py hasn't populated it yet.

import os
import sqlite3

import pytest

from tools.analysis.tests.core.test_db_utils import SHARED_TEST_DB_PATH


def test_symbols_are_stored_as_short_names():
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
        SELECT DISTINCT name
        FROM symbols
        """)

        names = [r[0] for r in c.fetchall()]

        fully_qualified = [
            n for n in names
            if "." in n
        ]

        assert fully_qualified == [], (
            "Symbols should currently be stored as short names only:\n"
            + "\n".join(fully_qualified)
        )
    finally:
        if db is not None:
            db.close()
