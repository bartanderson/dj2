import ast

from tools.analysis.ingestion.parse_ast import _extract_symbol_references
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder
from tools.analysis.identity.symbol_identity import classify_symbol
from tools.analysis.representation.symbol_environment import SymbolEnvironment
from tools.analysis.contracts.semantic_pipeline_contract import SemanticPipelineContract as Contract
from tools.analysis.graph.symbol_resolution_engine import resolve_symbol_type

def validate_classification_results(results):
    for r in results:
        Contract.validate_bucket(r["bucket"])

# ----------------------------
# FIXED TEST INPUT (controlled, minimal)
# ----------------------------
SOURCE = """
from tools.analysis.context.build_context_bundle import build_context_bundle

def get_llm_context_for_file():
    build_context_bundle()
    str()
"""


# ----------------------------
# CANONICAL TEST FIXTURES
# ----------------------------
PROJECT_SYMBOLS = {
    "tools.analysis.context.build_context_bundle.build_context_bundle"
}

ALIAS_MAP = {
    "build_context_bundle":
        "tools.analysis.context.build_context_bundle.build_context_bundle"
}

ENV = SymbolEnvironment(
    alias_map=ALIAS_MAP,
    runtime_bindings={},
    project_symbols=PROJECT_SYMBOLS,
)

ALLOWED_BUCKETS = {
    "project",
    "builtin",
    "stdlib",
    "runtime",
    "external_lib",
    "external_unknown",
    "classification_gap",
    "unresolved_qualified_reference",
    "unknown",
}


# ----------------------------
# STAGE 1
# AST → SymbolReference
# ----------------------------
def run_ast_stage():

    tree = ast.parse(SOURCE)

    refs = _extract_symbol_references(
        tree=tree,
        known_symbols=set(),
        alias_map=ALIAS_MAP,
        module_name="tools.analysis.test",
        project_symbols=PROJECT_SYMBOLS,
    )

    print("\n================ STAGE 1: AST OUTPUT ================\n")

    for r in refs:
        print(r.ir1.surface, "->", r.ir1.fqdn)

    # ----------------------------
    # structural invariants
    # ----------------------------
    assert (
        len(refs) == 2
    ), "unexpected symbol extraction cardinality"

    for r in refs:

        assert r.ir1.surface is not None
        assert isinstance(r.ir1.surface, str)

        assert r.ir1.normalized is not None
        assert isinstance(r.ir1.normalized, str)

        assert r.ir1.provenance is not None
        assert isinstance(r.ir1.provenance, list)

    return refs


# ----------------------------
# STAGE 2
# SymbolReference → SemanticIdentity
# ----------------------------
def run_identity_stage(refs):

    builder = SemanticIdentityBuilder()

    identities = []

    for r in refs:
        route_type = resolve_symbol_type(
            name=r.ir1.surface,
            runtime_bindings=ENV.runtime_bindings,
            project_symbols=ENV.project_symbols,
        )

        identity = builder.build(
            name=r.ir1.surface,
            env=ENV,
            route_type=route_type,
        )
        identities.append(identity)

    print("\n================ STAGE 2: IDENTITY OUTPUT ================\n")

    for i in identities:
        print(
            i.surface,
            "| fqdn:", i.fqdn,
            "| conf:", round(i.confidence, 3),
        )

    # ----------------------------
    # semantic invariants
    # ----------------------------
    for i in identities:

        assert i.surface is not None
        assert isinstance(i.surface, str)

        assert i.leaf == i.surface.split(".")[-1]

        assert i.fqdn is None or isinstance(i.fqdn, str)

        assert 0.0 <= i.confidence <= 1.0

        # fqdn normalization contract
        if i.fqdn:

            assert "\\" not in i.fqdn
            assert ":" not in i.fqdn

    # ----------------------------
    # cross-stage integrity
    # ----------------------------
    ref_surfaces = {
        r.ir1.surface
        for r in refs
    }

    identity_surfaces = {
        i.surface
        for i in identities
    }

    assert (
        ref_surfaces == identity_surfaces
    ), "AST → identity surface divergence detected"

    return identities


# ----------------------------
# STAGE 3
# SemanticIdentity → classification
# ----------------------------
def run_classification_stage(identities):

    results = []

    for i in identities:

        bucket = classify_symbol(
            identity=i,
            env=ENV,
        )

        results.append({
            "surface": i.surface,
            "fqdn": i.fqdn,
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
    # project classification contract
    # ----------------------------
    assert any(
        r["surface"] == "build_context_bundle"
        and r["bucket"] == "project"
        for r in results
    ), "project classification contract violation"

    # ----------------------------
    # builtin classification contract
    # ----------------------------
    assert any(
        r["surface"] == "str"
        and r["bucket"] == "builtin"
        for r in results
    ), "builtin classification contract violation"

    # ----------------------------
    # bucket validity contract
    # ----------------------------
    for r in results:

        assert (
            r["bucket"] in ALLOWED_BUCKETS
        ), f"invalid bucket emitted: {r['bucket']}"

    validate_classification_results(results)
    return results


# ----------------------------
# MAIN TRACE RUNNER
# ----------------------------
def test_symbol_pipeline_trace():

    refs = run_ast_stage()

    identities = run_identity_stage(refs)

    results = run_classification_stage(identities)

    print("\n================ PIPELINE COMPLETE ================\n")

    print("TOTAL RESULTS:", len(results))