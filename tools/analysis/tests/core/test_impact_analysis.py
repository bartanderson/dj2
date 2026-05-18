# tools/analysis/tests/core/test_impact_analysis.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_impacted_modules_transitive():
    gb = GraphBuilder()

    gb.add_reference("a.x.f1", "b.y.f2", 1, "project")
    gb.add_reference("b.y.f2", "c.z.f3", 2, "project")
    gb.add_reference("d.q.f4", "a.x.f1", 3, "project")

    impacted = gb.impacted_modules("c.z")

    assert "b.y" in impacted
    assert "a.x" in impacted
    assert "d.q" in impacted