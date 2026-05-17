import builtins

from tools.analysis.graph.symbol_classifier import classify_symbol
from tools.analysis.graph.symbol_router import route_symbol


PROJECT_PREFIXES = [
    "world.",
    "engine.",
    "core.",
    "dungeon_neo.",
    "tools.analysis.",
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

    route = route_symbol(
        name,
        runtime_bindings,
        PROJECT_SYMBOLS,
    )

    return classify_symbol(
        name,
        route,
        PROJECT_PREFIXES,
        runtime_bindings,
        PROJECT_SYMBOLS,
    )


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


def test_external_symbol():
    result = classify("flask.jsonify")
    assert result == "external_lib.flask"


def test_runtime_symbol():
    runtime_bindings = {
        "request": "flask.request"
    }

    result = classify(
        "request.args",
        runtime_bindings=runtime_bindings,
    )

    assert result == "runtime"


def test_unknown_symbol_not_project():
    result = classify("DefinitelyNotReal")
    assert result != "project"


def test_project_symbol_never_falls_through():
    result = classify("DungeonSystem")
    assert result == "project"


def test_external_symbol_never_project():
    result = classify("browser_use.Agent")
    assert result != "project"

from tools.analysis.graph.symbol_classifier import classify_symbol


def test_unknown_symbol_never_promoted_to_project():
    project_prefixes = [
        "world.",
        "engine.",
        "core.",
    ]

    runtime_bindings = {}
    project_symbols = {
        "world.game_state.GameState",
        "engine.controller.WorldController",
    }

    bad_inputs = [
        "DefinitelyNotReal",
        "AIBoundary",
        "RandomClass123",
        "FakeSystem",
    ]

    for name in bad_inputs:
        result = classify_symbol(
            name,
            route="external",
            project_prefixes=project_prefixes,
            runtime_bindings=runtime_bindings,
            project_symbols=project_symbols,
        )

        assert result != "project", f"False project promotion: {name} -> {result}"