import ast

from tools.analysis.ingestion.parse_ast import (
    _extract_runtime_bindings,
    _extract_imports,
)

from tools.analysis.graph.semantic_candidate_builder import (
    SemanticIdentityBuilder,
)

from tools.analysis.graph.symbol_classifier import (
    classify_symbol,
)

from tools.analysis.representation.symbol_environment import (
    SymbolEnvironment,
)


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

ALLOWED_BUCKETS = {
    "runtime",
    "project",
    "builtin",
    "stdlib",
    "external_lib",
    "external_unknown",
    "classification_gap",
    "unresolved_qualified_reference",
    "unknown",
}


# ----------------------------
# STAGE 1
# AST → runtime bindings
# ----------------------------
def run_runtime_binding_stage():

    tree = ast.parse(SOURCE)

    # ----------------------------
    # import / alias extraction
    # ----------------------------
    imports, alias_map = _extract_imports(tree)

    print("\n================ IMPORT / ALIAS STAGE ================\n")

    for k, v in alias_map.items():
        print(k, "->", v)

    # ----------------------------
    # runtime binding extraction
    # ----------------------------
    bindings = _extract_runtime_bindings(
        tree,
        alias_map=alias_map,
    )

    print("\n================ STAGE 1: RUNTIME BINDINGS ================\n")

    for k, v in bindings.items():
        print(k, "->", v)

    # ----------------------------
    # canonical environment
    # ----------------------------
    env = SymbolEnvironment(
        alias_map=alias_map,
        runtime_bindings=bindings,
        project_symbols=PROJECT_SYMBOLS,
    )

    # ----------------------------
    # structural invariants
    # ----------------------------
    assert isinstance(bindings, dict)

    assert (
        len(bindings) >= 2
    ), "expected at least 2 runtime bindings"

    for k, v in bindings.items():

        assert isinstance(k, str)
        assert isinstance(v, str)

        assert k != ""
        assert v != ""

        assert "C:" not in v
        assert "\\" not in v

    # ----------------------------
    # semantic contract
    # ----------------------------
    for expected_key, expected_val in EXPECTED_RUNTIME_BINDINGS.items():

        assert (
            expected_key in bindings
        ), f"missing runtime binding: {expected_key}"

        assert (
            bindings[expected_key] == expected_val
        ), (
            f"runtime binding mismatch for {expected_key}: "
            f"{bindings[expected_key]} != {expected_val}"
        )

    return env


# ----------------------------
# STAGE 2
# runtime bindings → identities
# ----------------------------
def run_identity_stage(env):

    builder = SemanticIdentityBuilder()

    identities = []

    for var in env.runtime_bindings:

        identity = builder.build(
            name=var,
            env=env,
        )

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
    runtime_identified = any(
        i.identity_type == "runtime"
        for i in identities
    )

    assert (
        runtime_identified
    ), "expected at least one runtime-resolved identity"

    return identities


# ----------------------------
# STAGE 3
# identity → classification
# ----------------------------
def run_classification_stage(identities, env):

    results = []

    for i in identities:

        bucket = classify_symbol(
            identity=i,
            env=env,
        )

        results.append({
            "surface": i.surface,
            "bucket": bucket,
        })

    print("\n================ STAGE 3: CLASSIFICATION OUTPUT ================\n")

    for r in results:
        print(
            r["surface"],
            "->",
            r["bucket"],
        )

    # ----------------------------
    # runtime classification contract
    # ----------------------------
    assert any(
        r["surface"] == "p"
        and r["bucket"] == "runtime"
        for r in results
    ), "runtime binding 'p' not classified correctly"

    # ----------------------------
    # project classification contract
    # ----------------------------
    assert any(
        r["surface"] == "x"
        and r["bucket"] == "project"
        for r in results
    ), "project runtime binding 'x' not classified correctly"

    # ----------------------------
    # bucket validity contract
    # ----------------------------
    for r in results:

        assert (
            r["bucket"] in ALLOWED_BUCKETS
        ), f"invalid bucket emitted: {r['bucket']}"

    return results


# ----------------------------
# MAIN TRACE
# ----------------------------
def test_runtime_binding_trace():

    env = run_runtime_binding_stage()

    identities = run_identity_stage(env)

    results = run_classification_stage(
        identities,
        env,
    )

    print("\n================ PIPELINE COMPLETE ================\n")

    print("TOTAL RESULTS:", len(results))