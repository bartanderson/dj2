# tools/analysis/tests/core/test_project_graph_context_routing.py

from tools.analysis.graph.symbol_router import (
    route_symbol_with_context,
)

from tools.analysis.graph.project_graph_context import (
    ProjectGraphContext,
)


def test_route_symbol_with_context_project():

    ctx = ProjectGraphContext(
        project_symbols={
            "tools.analysis.example.main"
        }
    )

    result = route_symbol_with_context(
        "main",
        ctx,
    )

    assert result == "project"


def test_route_symbol_with_context_runtime():

    ctx = ProjectGraphContext(
        runtime_bindings={
            "request": "flask.request"
        }
    )

    result = route_symbol_with_context(
        "request.args",
        ctx,
    )

    assert result == "runtime"