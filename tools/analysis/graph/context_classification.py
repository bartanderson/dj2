from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.symbol_classifier import classify_symbol
from tools.analysis.graph.symbol_router import route_symbol
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder

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

    builder = SemanticIdentityBuilder()
    identity = builder.build(name, env)
    return classify_symbol(identity, env)