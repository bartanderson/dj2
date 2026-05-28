# tools/analysis/tests/regression/test_runtime_resolution_lock.py

import ast

from tools.analysis.representation.symbol_environment import SymbolEnvironment
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder
from tools.analysis.ingestion.parse_ast import (
    _extract_imports,
    _extract_runtime_bindings,
)


def test_runtime_resolution_real_lock():

    fixture = "tools/analysis/tests/fixtures/sample_project/runtime_case.py"

    with open(fixture, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    # ----------------------------
    # build real environment
    # ----------------------------
    imports, alias_map = _extract_imports(tree)

    runtime_bindings = _extract_runtime_bindings(
        tree,
        alias_map=alias_map,
    )

    env = SymbolEnvironment(
        alias_map=alias_map,
        runtime_bindings=runtime_bindings,
        project_symbols=set(),
    )

    builder = SemanticIdentityBuilder()

    # ----------------------------
    # identities
    # ----------------------------
    x_identity = builder.build("x", env)
    y_identity = builder.build("y", env)

    # ----------------------------
    # LOCKED ASSERTIONS
    # ----------------------------

    # runtime resolution must exist somewhere in graph
    assert y_identity.fqdn is not None, "runtime resolution failed for y_identity"

    # resolved runtime target must propagate consistently
    if x_identity.fqdn is not None:
	    assert x_identity.fqdn == y_identity.fqdn, (
	        f"fqdn mismatch: x={x_identity.fqdn}, y={y_identity.fqdn}"
	    )

    # runtime binding must win over unresolved state
    assert y_identity.resolved_by == "runtime"

    # confidence must reflect resolution success
    assert y_identity.confidence >= 0.85