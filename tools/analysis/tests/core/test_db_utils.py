# tools/analysis/tests/core/test_db_utils.py

import os

DB_PATH = "tools/analysis/data/analysis.db"


def reset_analysis_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)