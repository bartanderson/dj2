# tools\analysis\tests\semantic\test_semantic_identity_project.py

from tools.analysis.representation.symbol_environment import SymbolEnvironment
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder


def test_project_fqdn_match():
    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings={},
        project_symbols={"world.game_state.GameState"},
    )

    print("\n[DEBUG A - ENV CHECK]")
    print("project_symbols:", env.project_symbols)
    print("type:", type(env.project_symbols))

    builder = SemanticIdentityBuilder()

    print("\n[DEBUG B - INPUT CHECK]")
    print("input name:", "world.game_state.GameState")
    print("leaf:", "GameState")

    identity = builder.build("world.game_state.GameState", env)

    print("\n[DEBUG C - IDENTITY OUTPUT]")
    print("fqdn:", identity.fqdn)
    print("leaf:", identity.leaf)
    print("project_hits:", identity.project_hits)
    print("provenance:", identity.provenance)
    print("resolved_by:", identity.resolved_by)

    print("\n[DEBUG D - FINAL STATE]")
    print(identity)

    assert identity.fqdn == "world.game_state.GameState"
    assert identity.project_hits
    assert identity.confidence >= 0.85


def test_project_leaf_match():
    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings={},
        project_symbols={"GameState"},
    )

    builder = SemanticIdentityBuilder()

    identity = builder.build("GameState", env)

    assert identity.leaf == "GameState"
    assert "GameState" in identity.project_hits