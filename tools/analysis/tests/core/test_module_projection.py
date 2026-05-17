# tools/analysis/tests/core/test_module_projection.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_module_projection_basic():
    gb = GraphBuilder()

    gb.add_reference("a.x.foo", "b.y.bar", 1, "project")
    gb.add_reference("a.x.foo", "b.y.baz", 2, "project")
    gb.add_reference("b.y.bar", "c.z.qux", 3, "project")

    proj = gb.module_projection()

    assert ("a.x", "b.y") in proj
    assert ("b.y", "c.z") in proj

    # no self-dependencies
    for caller, callee in proj:
        assert caller != callee