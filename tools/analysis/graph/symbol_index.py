# tools/analysis/graph/symbol_index.py

import sqlite3
from collections import defaultdict


def build_symbol_index(connection: sqlite3.Connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT file_path, name, symbol_type
        FROM symbols
    """)

    index = defaultdict(set)

    for file_path, name, symbol_type in cursor.fetchall():
        index[name].add(file_path)

    return index