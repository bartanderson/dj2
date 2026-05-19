from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.symbol_classifier import classify_symbol
from tools.analysis.graph.symbol_router import route_symbol


def classify_symbol_with_context(
    name: str,
    ctx: ProjectGraphContext,
):

    route = route_symbol(
        name,
        ctx.runtime_bindings,      # ✅ MUST be dict
        ctx.project_prefixes,
    )

    return classify_symbol(
        name,
        route,
        ctx.project_prefixes,
        ctx.runtime_bindings,
        ctx.project_symbols,
    )