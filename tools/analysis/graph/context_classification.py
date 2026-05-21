from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.symbol_classifier import classify_symbol
from tools.analysis.graph.symbol_router import route_symbol


def classify_symbol_with_context(
    name: str,
    ctx: ProjectGraphContext,
):
    assert not isinstance(
        ctx,
        dict,
    ), "ctx must be ProjectGraphContext, not dict"

    project_prefixes = ctx.project_prefixes
    runtime_bindings = ctx.runtime_bindings or {}
    project_symbols = ctx.project_symbols or set()

    route = route_symbol(
        name=name,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
    )

    return classify_symbol(
        name=name,
        route=route,
        project_prefixes=project_prefixes,
        runtime_bindings=runtime_bindings,
        project_symbols=project_symbols,
    )