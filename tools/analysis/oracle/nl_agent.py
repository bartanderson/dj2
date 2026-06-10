# tools/analysis/oracle/nl_agent.py

import json
from tools.analysis.oracle.db_oracle import DBOracle


class NaturalLanguageGraphAgent:
    def __init__(self, db_path: str, llm_callable):
        self.oracle = DBOracle(db_path)
        self.llm = llm_callable
        self.symbols = self._load_symbols()

    def _load_symbols(self):
        cur = self.oracle.conn.cursor()
        cur.execute("""
            SELECT caller FROM graph_edges
            UNION
            SELECT callee FROM graph_edges
        """)
        return sorted({r[0] for r in cur.fetchall()})

    # ------------------------------------------
    # STEP 1: LLM INTENT EXTRACTION
    # ------------------------------------------
    def interpret(self, question: str):
        prompt = {
            "question": question,
            "symbols": self.symbols[:500],  # bounded context window
            "output_format": {
                "intent": "context|surface|influence",
                "target": "symbol_name",
                "depth": 1
            }
        }

        raw = self.llm(json.dumps(prompt))

        return json.loads(raw)

    # ------------------------------------------
    # STEP 2: EXECUTION
    # ------------------------------------------
    def ask(self, question: str):
        intent = self.interpret(question)

        intent_type = intent["intent"]
        target = intent["target"]
        depth = intent.get("depth", 1)

        if intent_type == "context":
            return self.oracle.neighbors(target)

        if intent_type == "surface":
            return self.oracle.surface(target, depth)

        if intent_type == "influence":
            return self.oracle.influence(target, depth)

        raise ValueError(f"Unknown intent: {intent_type}")