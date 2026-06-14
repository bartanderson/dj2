# tools/analysis/tests/debug/oracle_compare_harness.py

from tools.analysis.api.oracle_router import route_query
from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.oracle.nl_agent import NaturalLanguageGraphAgent

print("HARNESS STARTED")


class OracleCompareHarness:
    def __init__(self, oracle: DBOracle, db_path: str, llm):
        self.oracle = oracle
        self.nl_agent = NaturalLanguageGraphAgent(db_path, llm)

    def run(self, question: str):
        print("\n==============================")
        print("QUESTION:", question)
        print("==============================\n")

        graph = self.oracle.get_snapshot_graph()

        # ------------------------------------------
        # ORACLE ROUTER (DETERMINISTIC)
        # ------------------------------------------
        oracle_result = route_query(
            question,
            graph,
            self.oracle.discover_seed_symbols,
        )

        print("\n--- ORACLE ROUTER ---")
        print("intent:", oracle_result.intent)
        print("seeds:", oracle_result.seed_symbols[:10])
        print("expanded:", oracle_result.expanded_symbols[:15])
        print("plan:", oracle_result.execution_plan)

        # ------------------------------------------
        # NL AGENT (LLM + DB)
        # ------------------------------------------
        nl = self.nl_agent.ask(question)

        print("\n--- NL AGENT ---")
        print("intent:", nl.get("intent"))
        print("target:", nl.get("target"))
        print("result:", nl)

        # ------------------------------------------
        # BASIC ALIGNMENT VIEW
        # ------------------------------------------
        print("\n--- ALIGNMENT CHECK ---")

        oracle_set = set(oracle_result.expanded_symbols)
        nl_target = nl.get("target")

        print("oracle node count:", len(oracle_set))
        print("nl target present in oracle:", nl_target in oracle_set if nl_target else False)

        return {
            "oracle": oracle_result,
            "nl": nl,
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python oracle_compare_harness.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    oracle = DBOracle(db_path)

    print("EDGE COUNT:", len(oracle.get_snapshot_graph().edges))

    nl_callable = lambda x: '{"intent":"surface","target":"test","depth":1}'

    harness = OracleCompareHarness(oracle=oracle, db_path=db_path, llm=nl_callable)

    queries = [
        "what depends on resolve_analysis_db_path",
        "show ingestion surface",
        "what affects engine snapshot",
    ]

    for q in queries:
        harness.run(q)