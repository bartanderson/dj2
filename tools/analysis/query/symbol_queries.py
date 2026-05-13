# tools/analysis/query/symbol_queries.py

import sqlite3


def get_all_symbols(db_path: str):
    db = sqlite3.connect(db_path)
    c = db.cursor()

    c.execute("SELECT DISTINCT name FROM symbols")
    return [r[0] for r in c.fetchall()]


def get_all_references(db_path: str):
    db = sqlite3.connect(db_path)
    c = db.cursor()

    c.execute("SELECT DISTINCT callee FROM symbol_references")
    return [r[0] for r in c.fetchall()]


def get_callers_of(db_path: str, symbol: str):
    db = sqlite3.connect(db_path)
    c = db.cursor()

    c.execute(
        "SELECT caller FROM symbol_references WHERE callee = ?",
        (symbol,),
    )
    return [r[0] for r in c.fetchall()]