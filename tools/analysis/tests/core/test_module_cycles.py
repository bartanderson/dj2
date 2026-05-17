# tools/analysis/tests/core/test_module_cycles.py

from tools.analysis.graph.graph_builder import GraphBuilder


def test_cycle_detection():
    gb = GraphBuilder()

    gb.add_reference("a.x.f1", "b.y.f2", 1, "project")
    gb.add_reference("b.y.f2", "c.z.f3", 2, "project")
    gb.add_reference("c.z.f3", "a.x.f1", 3, "project")  # cycle

    cycles = gb.find_module_cycles()

    assert len(cycles) > 0

    flat = [n for cycle in cycles for n in cycle]
    assert "a.x" in flat
    assert "b.y" in flat
    assert "c.z" in flat