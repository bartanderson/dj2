# tools/analysis/oracle/agent.py

import sqlite3
from tools.analysis.oracle.db_oracle import DBOracle


class GraphOracleAgent:
    def __init__(self, db_path: str):
        self.oracle = DBOracle(db_path)
        self.symbols = self._load_symbols()

    # -----------------------------
    # BOOTSTRAP SYMBOL SPACE
    # -----------------------------
    def _load_symbols(self):
        cur = self.oracle.conn.cursor()

        cur.execute("""
            SELECT caller FROM graph_edges
            UNION
            SELECT callee FROM graph_edges
        """)

        return sorted({r[0] for r in cur.fetchall()})

    # -----------------------------
    # SIMPLE SYMBOL FILTER (NO LLM YET)
    # -----------------------------
    def search_symbols(self, query: str, limit: int = 20):
        # intentionally minimal: substring match ONLY as fallback
        return [s for s in self.symbols if query.lower() in s.lower()][:limit]

    # -----------------------------
    # EXECUTION ENTRY
    # -----------------------------
    def run(self, llm_intent: dict):
        intent = llm_intent["intent"]
        target = llm_intent["target"]
        depth = llm_intent.get("depth", 1)

        if intent == "context":
            return self.oracle.neighbors(target)

        if intent == "surface":
            return self.oracle.surface(target, depth)

        if intent == "influence":
            return self.oracle.influence(target, depth)

        raise ValueError(intent)