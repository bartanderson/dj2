# tools/analysis/oracle/db_oracle.py

import sqlite3
import sys
from typing import List, Tuple

from tools.analysis.oracle.semantic_graph import SemanticGraphView

# =========================================================
# DB ORACLE CORE
# =========================================================

class DBOracle:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.sg = SemanticGraphView(self.conn)


    def edges(self):
        return self.sg.edges

    # -----------------------------
    # GRAPH EDGE QUERIES
    # -----------------------------

    def neighbors(self, symbol: str) -> dict:
        cur = self.conn.cursor()

        cur.execute("""
            SELECT callee
            FROM graph_edges
            WHERE caller = ?
        """, (symbol,))
        calls = sorted({r["callee"] for r in cur.fetchall()})

        cur.execute("""
            SELECT caller
            FROM graph_edges
            WHERE callee = ?
        """, (symbol,))
        called_by = sorted({r["caller"] for r in cur.fetchall()})

        return {
            "symbol": symbol,
            "calls": calls,
            "called_by": called_by,
        }

    # -----------------------------
    # FORWARD WALK (surface)
    # -----------------------------

    def surface(self, symbol: str, depth: int = 1) -> List[str]:
        visited = set()
        frontier = {symbol}
        result = set()

        for _ in range(depth):
            next_frontier = set()

            for node in frontier:
                cur = self.conn.cursor()
                cur.execute("""
                    SELECT callee FROM graph_edges WHERE caller = ?
                """, (node,))

                for row in cur.fetchall():
                    tgt = row["callee"]
                    if tgt not in visited:
                        result.add(tgt)
                        next_frontier.add(tgt)

            visited.update(frontier)
            frontier = next_frontier

        return sorted(result)

    # -----------------------------
    # REVERSE WALK (influence)
    # -----------------------------

    def influence(self, symbol: str, depth: int = 1) -> List[str]:
        visited = set()
        frontier = {symbol}
        result = set()

        for _ in range(depth):
            next_frontier = set()

            for node in frontier:
                cur = self.conn.cursor()
                cur.execute("""
                    SELECT caller FROM graph_edges WHERE callee = ?
                """, (node,))

                for row in cur.fetchall():
                    src = row["caller"]
                    if src not in visited:
                        result.add(src)
                        next_frontier.add(src)

            visited.update(frontier)
            frontier = next_frontier

        return sorted(result)


# =========================================================
# CLI INTERFACE
# =========================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python db_oracle.py <db_path>")
        sys.exit(1)

    oracle = DBOracle(sys.argv[1])

    print("\nDB ORACLE READY")
    print("Commands:")
    print("  neighbors <symbol>")
    print("  surface <symbol> [depth]")
    print("  influence <symbol> [depth]")
    print("  exit\n")

    while True:
        cmd = input("oracle> ").strip().split()

        if not cmd:
            continue

        if cmd[0] == "exit":
            break

        if cmd[0] == "neighbors":
            res = oracle.neighbors(cmd[1])
            print(res)

        elif cmd[0] == "surface":
            depth = int(cmd[2]) if len(cmd) > 2 else 1
            res = oracle.surface(cmd[1], depth)
            print(res)

        elif cmd[0] == "influence":
            depth = int(cmd[2]) if len(cmd) > 2 else 1
            res = oracle.influence(cmd[1], depth)
            print(res)

        else:
            print("unknown command")


if __name__ == "__main__":
    main()