# tools/analysis/tests/core/test_critical_modules.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_critical_modules_returns_sorted_list():
    gb = GraphBuilder()

    gb.add_reference("a.x.f1", "b.y.f2", 1, "project")
    gb.add_reference("b.y.f2", "c.z.f3", 2, "project")
    gb.add_reference("c.z.f3", "a.x.f1", 3, "project")

    top = gb.critical_modules(2)

    assert len(top) == 2
    assert isinstance(top[0][0], str)
    assert isinstance(top[0][1], int)