# tools/analysis/tests/core/test_symbol_classification_runtime_contract.py

import ast

from tools.analysis.graph.symbol_router import route_symbol
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder
from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.ingestion.parse_ast import (
    _extract_imports,
    _extract_runtime_bindings,
)


def _ctx(source: str):
    tree = ast.parse(source, mode="exec")

    _, alias_map = _extract_imports(tree)

    runtime_bindings = _extract_runtime_bindings(
        tree,
        alias_map=alias_map
    )
    assert runtime_bindings is not None, "runtime_bindings missing from extractor"

    return ProjectGraphContext(
        project_prefixes=["tools.", "engine.", "world."],
        runtime_bindings=runtime_bindings,
        project_symbols={
            "tools.analysis.example.main",
            "world.game_state.GameState",
            "engine.controller.WorldController",
        },
    )


def test_runtime_binding_contract():
    ctx = _ctx("request = request.args")

    print("CTX BUILD runtime_bindings =", ctx.runtime_bindings)

    route = route_symbol(
        "request.args",
        ctx.runtime_bindings,
        ctx.project_symbols,
    )

    identity = SemanticIdentityBuilder().build("request.args", ctx, route)

    assert route == "runtime"
    assert identity.resolved_by == "runtime"
    assert identity.fqdn is not None


def test_project_symbol_contract():
    ctx = _ctx("tools.analysis.example.main")

    route = route_symbol(
        "tools.analysis.example.main",
        ctx.runtime_bindings,
        ctx.project_symbols,
    )

    identity = SemanticIdentityBuilder().build("tools.analysis.example.main", ctx, route)

    assert route == "project"
    assert identity.fqdn is not None


def test_external_symbol_contract():
    ctx = _ctx("flask.jsonify")

    route = route_symbol(
        "flask.jsonify",
        ctx.runtime_bindings,
        ctx.project_symbols,
    )

    identity = SemanticIdentityBuilder().build("flask.jsonify", ctx, route)

    assert route in ("external", "unknown")