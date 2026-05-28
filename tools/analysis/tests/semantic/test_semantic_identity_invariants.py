# tools\analysis\tests\semantic\test_semantic_identity_invariants.py

from tools.analysis.representation.symbol_environment import SymbolEnvironment
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder


def test_builtin_fallback_behavior():
    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings={},
        project_symbols=set(),
    )

    builder = SemanticIdentityBuilder()

    identity = builder.build("print", env)

    assert identity.fqdn is None
    assert identity.confidence == 0.05
    assert "no_resolution_signal" in identity.provenance


def test_external_symbol_no_false_project():
    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings={},
        project_symbols={"SomeInternalThing"},
    )

    builder = SemanticIdentityBuilder()

    identity = builder.build("flask.jsonify", env)

    assert "project_symbol_hint" not in identity.provenance
    assert identity.leaf == "jsonify"


def test_project_does_not_override_runtime():
    env = SymbolEnvironment(
        alias_map={},
        runtime_bindings={"y": "flask.request.args"},
        project_symbols={"args"},
    )

    builder = SemanticIdentityBuilder()

    identity = builder.build("y", env)

    assert identity.resolved_by == "runtime"
    assert identity.fqdn.startswith("flask.request")