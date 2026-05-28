# tools/analysis/tests/integration/test_runtime_resolution_real.py

import ast

from tools.analysis.ingestion.parse_ast import (
    _extract_imports,
    _extract_runtime_bindings,
)

from tools.analysis.graph.semantic_candidate_builder import (
    SemanticIdentityBuilder,
)

from tools.analysis.representation.symbol_environment import (
    SymbolEnvironment,
)


def test_runtime_resolution_real():

    fixture = (
        "tools/analysis/tests/fixtures/"
        "sample_project/runtime_case.py"
    )

    with open(fixture, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    # -------------------------------------------------
    # REAL import extraction
    # -------------------------------------------------
    imports, alias_map = _extract_imports(tree)

    print("\nALIAS MAP:")
    print(alias_map)

    # -------------------------------------------------
    # REAL runtime binding extraction
    # -------------------------------------------------
    runtime_bindings = _extract_runtime_bindings(
        tree,
        alias_map=alias_map,
    )

    print("\nRUNTIME BINDINGS:")
    print(runtime_bindings)

    # -------------------------------------------------
    # REAL semantic environment
    # -------------------------------------------------
    env = SymbolEnvironment(
        alias_map=alias_map,
        runtime_bindings=runtime_bindings,
        project_symbols=set(),
    )

    builder = SemanticIdentityBuilder()

    # -------------------------------------------------
    # Build identities
    # -------------------------------------------------
    x_identity = builder.build("x", env)
    y_identity = builder.build("y", env)

    print("\nX IDENTITY:")
    print(x_identity)

    print("\nY IDENTITY:")
    print(y_identity)

    # -------------------------------------------------
    # HARD INVARIANTS
    # -------------------------------------------------

    # direct import binding
    assert x_identity.fqdn is not None

    # alias-based runtime binding
    assert y_identity.fqdn is not None

    # runtime signal must survive
    assert y_identity.resolved_by in (
        "runtime",
        "alias",
    )

    # provenance must exist
    assert len(y_identity.provenance) > 0

    # NEW INVARIANT
    assert x_identity.fqdn == y_identity.fqdn