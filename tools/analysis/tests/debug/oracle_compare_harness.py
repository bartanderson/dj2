# tools/analysis/tests/debug/oracle_compare_harness.py

from tools.analysis.api.oracle_router import route_query
from tools.analysis.oracle.nl_agent import NaturalLanguageGraphAgent

print("HARNESS STARTED")
class OracleCompareHarness:
    def __init__(self, graph, find_symbols_fn, db_path, llm):
        self.graph = graph
        self.find_symbols_fn = find_symbols_fn
        self.nl_agent = NaturalLanguageGraphAgent(db_path, llm)

    def run(self, question: str):
        print("\n==============================")
        print("QUESTION:", question)
        print("==============================\n")

        # ------------------------------------------
        # ORACLE ROUTER (DETERMINISTIC)
        # ------------------------------------------
        oracle = route_query(
            question,
            self.graph,
            self.find_symbols_fn
        )

        print("\n--- ORACLE ROUTER ---")
        print("intent:", oracle.intent)
        print("seeds:", oracle.seed_symbols[:10])
        print("expanded:", oracle.expanded_symbols[:15])
        print("plan:", oracle.execution_plan)

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

        oracle_set = set(oracle.expanded_symbols)
        nl_target = nl.get("target")

        print("oracle node count:", len(oracle_set))
        print("nl target present in oracle:", nl_target in oracle_set if nl_target else False)

        return {
            "oracle": oracle,
            "nl": nl
        }

if __name__ == "__main__":
    from tools.analysis.api.oracle_router import route_query
    from tools.analysis.oracle.nl_agent import NaturalLanguageGraphAgent
    from tools.analysis.graph.graph_builder import GraphBuilder
    from tools.analysis.engine.db_resolver import resolve_analysis_db_path
    from tools.analysis.api.query_discovery import find_symbols as real_find_symbols
    import sys

    db_path = sys.argv[1]

    graph = GraphBuilder().build()
    print("EDGE COUNT:", len(graph.edges))
    find_symbols_fn = real_find_symbols

    nl_agent = NaturalLanguageGraphAgent(db_path, llm_callable=lambda x: '{"intent":"surface","target":"test","depth":1}')

    queries = [
        "what depends on resolve_analysis_db_path",
        "show ingestion surface",
        "what affects engine snapshot"
    ]

    for q in queries:
        print("\n\n==============================")
        print("QUERY:", q)

        print("\n--- ROUTER ---")
        r1 = route_query(q, graph, find_symbols_fn)
        print(r1.execution_plan)

        print("\n--- NL AGENT ---")
        r2 = nl_agent.ask(q)
        print(r2)
    print("SYMBOL SAMPLE:", list(getattr(graph, "symbols", []))[:20])