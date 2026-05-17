from tools.analysis.graph.project_graph_context import (
    ProjectGraphContext,
)


def test_project_graph_context_defaults():

    ctx = ProjectGraphContext()

    assert ctx.project_prefixes == []
    assert ctx.project_symbols == set()
    assert ctx.runtime_bindings == {}