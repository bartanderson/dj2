# tools/analysis/oracle/db_oracle.py

import sqlite3
import sys
from typing import Any, Dict, List, Tuple
from collections import defaultdict, deque
from tools.analysis.graph.graph_builder import GraphEdge, GraphBundle
from tools.analysis.oracle.edge_semantics import interpret_edge

# =========================================================
# DB ORACLE CORE
# =========================================================

class DBOracle:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.db_path = db_path

    # -----------------------------
    # SEMANTIC EDGES
    # -----------------------------

    def get_semantic_edges(self):
        cur = self.conn.cursor()

        rows = cur.execute("""
            SELECT caller, callee, line_number
            FROM graph_edges
            WHERE caller IS NOT NULL
              AND callee IS NOT NULL
        """).fetchall()

        return [
            interpret_edge(
                GraphEdge(
                    caller=r["caller"],
                    callee=r["callee"],
                    line_number=r["line_number"],
                )
            )
            for r in rows
        ]

    # -----------------------------
    # FILE COUNT (FIXED LOCATION)
    # -----------------------------

    def file_count(self) -> int:
        cur = self.conn.cursor()
        return cur.execute("""
            SELECT COUNT(DISTINCT file_path)
            FROM symbol_references
            WHERE file_path IS NOT NULL
        """).fetchone()[0]

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

    def get_snapshot_graph(self) -> GraphBundle:
        cur = self.conn.cursor()

        rows = cur.execute("""
            SELECT caller, callee, line_number
            FROM graph_edges
            WHERE caller IS NOT NULL
              AND callee IS NOT NULL
        """).fetchall()

        edges = [
            GraphEdge(
                caller=r["caller"],
                callee=r["callee"],
                line_number=r["line_number"],
            )
            for r in rows
        ]

        bucket_counts = {
            "total": len(edges)
        }

        return GraphBundle(
            edges=edges,
            bucket_counts=bucket_counts
        )

    def builtin_symbols(self) -> set:
        """
        Returns the set of all symbols that appear exclusively as builtins
        in symbol_references. A symbol is considered builtin if every
        reference to it (as caller or callee) is bucket='builtin'.
        Used by build_structure_view to exclude builtins from hotspot ranking.
        """
        cur = self.conn.cursor()

        rows = cur.execute("""
            SELECT symbol, MIN(bucket) as min_bucket, MAX(bucket) as max_bucket
            FROM (
                SELECT caller as symbol, bucket FROM symbol_references
                    WHERE caller IS NOT NULL
                UNION ALL
                SELECT callee as symbol, bucket FROM symbol_references
                    WHERE callee IS NOT NULL
            )
            GROUP BY symbol
        """).fetchall()

        builtins = set()

        for r in rows:
            if r["min_bucket"] == "builtin" and r["max_bucket"] == "builtin":
                builtins.add(r["symbol"])

        return builtins

    def snapshot(self):
        return self.get_snapshot_graph()

    # -----------------------------
    # BUCKET SUMMARY (symbol_references is the only table
    # that actually carries bucket info — graph_edges does not)
    # -----------------------------

    def bucket_summary(self) -> dict:
        cur = self.conn.cursor()

        rows = cur.execute("""
            SELECT bucket, COUNT(*) as cnt
            FROM symbol_references
            WHERE caller IS NOT NULL
              AND callee IS NOT NULL
            GROUP BY bucket
        """).fetchall()

        summary = {
            "project": 0,
            "builtin": 0,
            "classification_gap": 0,
        }

        for r in rows:
            bucket = r["bucket"]
            if bucket not in summary:
                bucket = "classification_gap"
            summary[bucket] += r["cnt"]

        return summary

    # -----------------------------
    # SYMBOL REFERENCE COUNT (DB total, mirrors ingestion fact)
    # -----------------------------

    def symbol_reference_count(self) -> int:
        cur = self.conn.cursor()
        return cur.execute("""
            SELECT COUNT(*) FROM symbol_references
        """).fetchone()[0]

    # -----------------------------
    # PER-FILE SYMBOL REFERENCES (DB analogue of file_analyses)
    # -----------------------------

    def file_reference_map(self) -> Dict[str, List[Dict[str, Any]]]:
        cur = self.conn.cursor()

        rows = cur.execute("""
            SELECT file_path, caller, callee, line_number, bucket
            FROM symbol_references
            WHERE file_path IS NOT NULL
            ORDER BY file_path
        """).fetchall()

        files: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for r in rows:
            files[r["file_path"]].append({
                "caller": r["caller"],
                "callee": r["callee"],
                "line_number": r["line_number"],
                "bucket": r["bucket"],
            })

        return dict(files)

    # =====================================================
    # SEED DISCOVERY (DB-OWNED, NO EXTERNAL MODULE)
    # =====================================================
    def discover_seed_symbols(self, text: str, limit: int = 50) -> list:
        """
        DB-backed seed discovery. Seeds are drawn from symbol_references
        (not graph_edges) so bucket filtering is available.

        Scoring:
          +2  exact symbol name match (case-insensitive)
          +2  substring match where query is contained in symbol
          +1  per overlapping token (tokenized on . _ and whitespace)

        Minimum score of 2 required — single loose token matches
        (e.g. 'show' matching matplotlib.pyplot.show) are excluded.

        Builtins are never seeds regardless of score.
        """
        cur = self.conn.cursor()

        rows = cur.execute("""
            SELECT DISTINCT caller as symbol, bucket FROM symbol_references
                WHERE caller IS NOT NULL
            UNION
            SELECT DISTINCT callee as symbol, bucket FROM symbol_references
                WHERE callee IS NOT NULL
        """).fetchall()

        text_lower = text.lower()
        text_tokens = set(
            text_lower
            .replace("_", " ")
            .replace(".", " ")
            .split()
        )

        # short/generic tokens that match too broadly as standalone signals
        # (these still count when combined with other matches)
        WEAK_TOKENS = {"on", "in", "at", "to", "of", "is", "a", "an",
                       "the", "for", "with", "from", "by", "or", "and"}

        signal_tokens = {t for t in text_tokens if t not in WEAK_TOKENS}

        scored = []
        seen_sym = set()

        for r in rows:
            sym = r["symbol"]
            bucket = r["bucket"]

            if bucket == "builtin":
                continue

            if sym in seen_sym:
                continue
            seen_sym.add(sym)

            sym_lower = sym.lower()
            sym_tokens = set(
                sym_lower
                .replace(".", " ")
                .replace("_", " ")
                .split()
            )

            score = 0

            # exact match — highest confidence
            if text_lower == sym_lower:
                score += 4

            # query text is a substring of the symbol
            if text_lower in sym_lower:
                score += 3
            # symbol tail (last segment) contains the full query
            sym_tail = sym_lower.split(".")[-1]
            if text_lower in sym_tail:
                score += 2

            # token overlap — weighted by token length (longer = more specific)
            for tok in signal_tokens & sym_tokens:
                score += 1 + (1 if len(tok) > 5 else 0)

            if score >= 2:
                scored.append((score, sym))

        scored.sort(reverse=True, key=lambda x: x[0])

        seen = set()
        out = []

        for _, s in scored:
            if s not in seen:
                seen.add(s)
                out.append(s)

            if len(out) >= limit:
                break

        return out

# not class functions here...


# =========================================================
# INTERNAL INDEX BUILDER (STRUCTURAL ONLY)
# =========================================================

def _edges(graph):
    return getattr(graph, "edges", [])


def _build_index(graph):
    forward = defaultdict(set)
    reverse = defaultdict(set)

    for e in _edges(graph):
        forward[e.caller].add(e.callee)
        reverse[e.callee].add(e.caller)

    return forward, reverse


# =========================================================
# CONTEXT (was neighbors)
# =========================================================

def context(graph: Any, symbol: str) -> Dict[str, Any]:
    forward, reverse = _build_index(graph)

    return {
        "symbol": symbol,
        "calls": sorted(forward.get(symbol, [])),
        "called_by": sorted(reverse.get(symbol, [])),
    }


# =========================================================
# SURFACE (forward dependency)
# =========================================================

def surface(graph: Any, symbol: str, depth: int = 1) -> List[str]:
    forward, _ = _build_index(graph)

    visited = set()
    queue = deque([(symbol, 0)])
    result = set()

    while queue:
        node, d = queue.popleft()

        if node in visited:
            continue
        visited.add(node)

        if d > 0:
            result.add(node)

        if d < depth:
            for nxt in forward.get(node, []):
                queue.append((nxt, d + 1))

    return sorted(result)


# =========================================================
# INFLUENCE (reverse dependency)
# =========================================================

def influence(graph: Any, symbol: str, depth: int = 1) -> List[str]:
    _, reverse = _build_index(graph)

    visited = set()
    queue = deque([(symbol, 0)])
    result = set()

    while queue:
        node, d = queue.popleft()

        if node in visited:
            continue
        visited.add(node)

        if d > 0:
            result.add(node)

        if d < depth:
            for nxt in reverse.get(node, []):
                queue.append((nxt, d + 1))

    return sorted(result)


def engine_query(graph, symbol: str, depth: int = 1):
    """
    Single deterministic reasoning surface over the graph.

    This is the ONLY supported external query abstraction.
    """

    return {
        "symbol": symbol,
        "context": context(graph, symbol),
        "surface": surface(graph, symbol, depth=depth),
        "influence": influence(graph, symbol, depth=depth),
    }

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