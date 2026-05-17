from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.symbol_classifier import classify_symbol
from tools.analysis.graph.symbol_router import route_symbol


def classify_symbol_with_context(
    name: str,
    ctx: ProjectGraphContext,
):

    route = route_symbol(
        name,
        runtime_bindings=ctx.runtime_bindings,
        project_symbols=ctx.project_symbols,
    )

    return classify_symbol(
        name,
        route,
        ctx.project_prefixes,
        ctx.runtime_bindings,
        ctx.project_symbols,
    )