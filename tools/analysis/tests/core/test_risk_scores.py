# tools/analysis/tests/core/test_risk_scores.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_risk_scores_basic():
    gb = GraphBuilder()

    gb.add_reference("a.x.f1", "b.y.f2", 1, "project")
    gb.add_reference("b.y.f2", "c.z.f3", 2, "project")
    gb.add_reference("c.z.f3", "a.x.f1", 3, "project")

    scores = gb.risk_scores()

    assert "a.x" in scores

    data = scores["a.x"]

    assert "score" in data
    assert "fan_in" in data
    assert "fan_out" in data
    assert "impact_radius" in data
    assert isinstance(data["score"], int)