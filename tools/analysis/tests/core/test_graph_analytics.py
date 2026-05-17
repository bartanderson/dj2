# tools/analysis/tests/core/test_graph_analytics.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_graph_top_callees_and_callers():
    gb = GraphBuilder()

    gb.add_reference("a", "b", 1, "project")
    gb.add_reference("a", "c", 2, "project")
    gb.add_reference("b", "c", 3, "project")
    gb.add_reference("a", "c", 4, "project")

    top_callees = gb.top_callees()

    assert top_callees[0][0] == "c"
    assert top_callees[0][1] == 2  # c is called twice

    top_callers = gb.top_callers()

    assert top_callers[0][0] == "a"