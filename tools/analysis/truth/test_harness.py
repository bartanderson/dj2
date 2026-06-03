# tools/analysis/truth/test_harness.py

from tools.analysis.truth.query_executor import QueryExecutor
from tools.analysis.truth.query_plan import QueryPlanner
from tools.analysis.truth.query_executor import QuerySemanticsRegistry
from tools.analysis.truth.query_ast import Select, Combine


class TruthTestHarness:

    def __init__(self, views):
        self.executor = QueryExecutor(views=views)
        self.planner = QueryPlanner(QuerySemanticsRegistry())

    def run(self, queries):

        results = []

        for q in queries:
            try:
                plan = self.planner.plan(q)
                result = self.executor.execute(plan.root)

                results.append({
                    "query": repr(q),
                    "ok": True,
                    "result": result,
                    "error": None,
                })

            except Exception as e:
                results.append({
                    "query": repr(q),
                    "ok": False,
                    "result": None,
                    "error": str(e),
                })

        return results

    def print_report(self, results):

        print("\n=== TRUTH LAYER TEST REPORT ===")

        passed = 0
        failed = 0

        for r in results:

            if r["ok"]:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            print(f"\n[{status}] {r['query']}")

            if r["ok"]:
                print(r["result"])
            else:
                print("ERROR:", r["error"])

        print("\n--- SUMMARY ---")
        print("passed:", passed)
        print("failed:", failed)

        return passed, failed