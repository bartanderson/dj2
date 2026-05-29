from tools.analysis.graph.symbol_classifier import classify_symbol
from tools.analysis.representation.symbol_environment import SymbolEnvironment
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder


PROJECT_PREFIXES = [
    "world.",
    "engine.",
    "core.",
]

PROJECT_SYMBOLS = {
    "world.game_state.GameState",
    "engine.controller.WorldController",
    "tools.analysis.graph.symbol_router.route_symbol",
    "DungeonSystem",
    "GameState",
}


def classify(name, runtime_bindings=None):
    runtime_bindings = runtime_bindings or {}

    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings=runtime_bindings,
        project_symbols=PROJECT_SYMBOLS,
    )

    builder = SemanticIdentityBuilder()

    identity = builder.build(name, env)

    return classify_symbol(identity, env)


def test_project_symbol_fully_qualified():
    result = classify("world.game_state.GameState")

    assert result == "project"


def test_project_symbol_leaf():
    result = classify("GameState")

    assert result == "project"


def test_builtin_symbol():
    result = classify("print")

    assert result == "builtin"


def test_stdlib_symbol():
    result = classify("pathlib.Path")

    assert result == "stdlib"


def test_unknown_symbol_not_project():
    result = classify("DefinitelyNotReal")

    assert result != "project"


def test_project_symbol_never_falls_through():
    result = classify("DungeonSystem")

    assert result == "project"


def test_external_symbol_never_project():
    result = classify("browser_use.Agent")

    assert result != "project"


def test_unknown_symbol_never_promoted_to_project():

    bad_inputs = [
        "DefinitelyNotReal",
        "AIBoundary",
        "RandomClass123",
        "FakeSystem",
    ]

    for name in bad_inputs:

        result = classify(name)

        assert result != "project"