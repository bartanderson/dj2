# tools/analysis/engine/write_to_db.py

import sqlite3
from tools.analysis.persistence.persist_file_analysis import persist_file_analysis


def write_engine_to_db(connection: sqlite3.Connection, file_analyses, project_prefixes):
    if connection is None:
        raise RuntimeError("DB connection required for write_to_db stage")

    for analysis in file_analyses:
        persist_file_analysis(connection, analysis, project_prefixes)