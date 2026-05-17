# tools/analysis/tests/core/test_module_ranking.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_module_ranking_basic():
    gb = GraphBuilder()

    gb.add_reference("a.x.f1", "b.y.f2", 1, "project")
    gb.add_reference("b.y.f2", "c.z.f3", 2, "project")
    gb.add_reference("c.z.f3", "a.x.f1", 3, "project")  # cycle

    ranked = gb.rank_modules()

    assert len(ranked) >= 3

    top_module = ranked[0][0]
    top_score = ranked[0][1]

    assert isinstance(top_module, str)
    assert top_score > 0