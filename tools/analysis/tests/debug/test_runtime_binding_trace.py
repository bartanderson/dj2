import ast

from tools.analysis.ingestion.parse_ast import (
    _extract_runtime_bindings,
    _extract_symbol_references,
    _extract_imports
)

from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder
from tools.analysis.graph.symbol_classifier import classify_symbol


# ----------------------------
# FIXED INPUT (runtime binding focused)
# ----------------------------
SOURCE = """
from pathlib import Path

import tools.analysis.context.build_context_bundle as ctx

def handler():
    p = Path("x")
    x = ctx.build_context_bundle
    return p, x
"""


# ----------------------------
# CANONICAL EXPECTATIONS
# ----------------------------
EXPECTED_RUNTIME_BINDINGS = {
    "p": "Path",
    "x": (
        "tools.analysis.context."
        "build_context_bundle."
        "build_context_bundle"
    ),
}

PROJECT_SYMBOLS = {
    "tools.analysis.context.build_context_bundle.build_context_bundle",
}

ALLOWED_LEAF_TYPES = {
    "runtime",
    "alias",
    "builtin",
    "unknown",
}


# ----------------------------
# STAGE 1
# AST → runtime bindings only
# ----------------------------
def run_runtime_binding_stage():

    tree = ast.parse(SOURCE)

    # --------------------------------
    # canonical alias extraction stage
    # --------------------------------
    imports, alias_map = _extract_imports(tree)

    print("\n================ IMPORT / ALIAS STAGE ================\n")

    for k, v in alias_map.items():
        print(k, "->", v)

    # --------------------------------
    # runtime binding extraction stage
    # --------------------------------
    bindings = _extract_runtime_bindings(
        tree,
        alias_map=alias_map,
    )

    print("\n================ STAGE 1: RUNTIME BINDINGS ================\n")

    for k, v in bindings.items():
        print(k, "->", v)

    # ----------------------------
    # structural invariants
    # ----------------------------
    assert isinstance(bindings, dict)
    assert len(bindings) >= 2, "expected at least 2 runtime bindings"

    for k, v in bindings.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        assert k != ""
        assert v != ""

        # no filesystem leakage
        assert "C:" not in v
        assert "\\" not in v

    # ----------------------------
    # semantic contract
    # ----------------------------
    for expected_key, expected_val in EXPECTED_RUNTIME_BINDINGS.items():
        assert expected_key in bindings, f"missing runtime binding: {expected_key}"
        assert bindings[expected_key] == expected_val, (
            f"runtime binding mismatch for {expected_key}: "
            f"{bindings[expected_key]} != {expected_val}"
        )

    return bindings


# ----------------------------
# STAGE 2
# runtime bindings → identity enrichment
# ----------------------------
def run_identity_stage(bindings):

    builder = SemanticIdentityBuilder()

    identities = []

    runtime_bindings = bindings

    for var, target in runtime_bindings.items():

        identity = builder.build(
            name=var,                      # variable name is the identity surface
            alias_map={},
            runtime_bindings={
                var: target               # preserve correct mapping
            },
            project_symbols=set(),
        )

        identity.surface = var

        identities.append(identity)

    print("\n================ STAGE 2: IDENTITY OUTPUT ================\n")

    for i in identities:
        print(
            i.surface,
            "| fqdn:", i.fqdn,
            "| type:", i.identity_type,
            "| conf:", round(i.confidence, 3),
        )

    # ----------------------------
    # structural invariants
    # ----------------------------
    for i in identities:

        assert isinstance(i.surface, str)
        assert isinstance(i.identity_type, str)

        assert 0.0 <= i.confidence <= 1.0

        if i.fqdn:
            assert "C:" not in i.fqdn
            assert "\\" not in i.fqdn

    # ----------------------------
    # semantic contract
    # ----------------------------
    runtime_identified = any(i.identity_type == "runtime" for i in identities)
    assert runtime_identified, "expected at least one runtime-resolved identity"

    return identities


# ----------------------------
# STAGE 3
# identity → classification verification
# ----------------------------
def run_classification_stage(identities,bindings):

    results = []

    for i in identities:

        bucket = classify_symbol(
            identity=i,
            project_symbols=PROJECT_SYMBOLS,
            runtime_bindings=bindings,
        )

        results.append((i.surface, bucket))

    print("\n================ STAGE 3: CLASSIFICATION OUTPUT ================\n")

    for s, b in results:
        print(s, "->", b)

    # ----------------------------
    # runtime classification contract
    # ----------------------------
    assert any(
        s == "p" and b == "runtime"
        for s, b in results
    ), "runtime binding 'p' not classified correctly"

    assert any(
        s == "x"
        for s, _ in results
    ), "alias-derived runtime binding missing"

    return results


# ----------------------------
# MAIN TRACE
# ----------------------------
def test_runtime_binding_trace():

    bindings = run_runtime_binding_stage()

    identities = run_identity_stage(bindings)

    results = run_classification_stage(identities, bindings)

    print("\n================ PIPELINE COMPLETE ================\n")
    print("TOTAL RESULTS:", len(results))