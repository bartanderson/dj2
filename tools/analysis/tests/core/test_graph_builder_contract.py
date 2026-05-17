# tools/analysis/tests/core/test_graph_builder_contract.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_graph_builder_basic_edges():
    gb = GraphBuilder()

    gb.add_reference("a", "b", 1, "project")
    gb.add_reference("a", "c", 2, "project")
    gb.add_reference("b", "c", 3, "project")

    assert gb.callees_of("a") == {"b", "c"}
    assert gb.callers_of("c") == {"a", "b"}