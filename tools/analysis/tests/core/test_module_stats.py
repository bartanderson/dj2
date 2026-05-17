# tools/analysis/tests/core/test_module_stats.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_module_stats_basic():
    gb = GraphBuilder()

    gb.add_reference("a.x.foo", "b.y.bar", 1, "project")
    gb.add_reference("a.x.foo", "b.y.baz", 2, "project")
    gb.add_reference("b.y.bar", "c.z.qux", 3, "project")

    stats = gb.module_stats()

    assert stats["a.x"]["fan_out"] == 1
    assert stats["b.y"]["fan_in"] >= 1
    assert stats["b.y"]["fan_out"] >= 1
    assert stats["c.z"]["fan_in"] >= 1