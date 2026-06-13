# tools/analysis/api/seed_discovery.py

from typing import Any, List


def list_symbols(graph: Any, query: str, limit: int = 20) -> List[str]:
    """
    DB-backed symbol retrieval ONLY.

    This is NOT semantic.
    This is NOT interpretation.
    This is string match / index lookup only.
    """

    cur = graph.conn.cursor()

    rows = cur.execute("""
        SELECT DISTINCT caller
        FROM graph_edges
        WHERE caller LIKE ?
        LIMIT ?
    """, (f"%{query}%", limit)).fetchall()

    return [r["caller"] for r in rows if r["caller"]]


def find_symbols(graph: Any, query: str, limit: int = 20) -> List[str]:
    """
    Broader match version (caller + callee space)
    """

    cur = graph.conn.cursor()

    rows = cur.execute("""
        SELECT DISTINCT caller
        FROM graph_edges
        WHERE caller LIKE ?
           OR callee LIKE ?
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit)).fetchall()

    return [r["caller"] for r in rows if r["caller"]]