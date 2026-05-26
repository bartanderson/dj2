import ast
from tools.analysis.ingestion.parse_ast import _extract_symbol_references
from tools.analysis.graph.semantic_candidate_builder import SemanticIdentityBuilder
from tools.analysis.graph.symbol_classifier import classify_symbol


# ----------------------------
# FIXED TEST INPUT (controlled, minimal)
# ----------------------------
SOURCE = """
from tools.analysis.context.build_context_bundle import build_context_bundle

def get_llm_context_for_file():
    build_context_bundle()
    str()
"""


def run_ast_stage():
    """
    STAGE 1:
    AST → SymbolReference extraction only
    """
    tree = ast.parse(SOURCE)

    refs = _extract_symbol_references(
        tree=tree,
        known_symbols=set(),
        alias_map={
            "build_context_bundle": "tools.analysis.context.build_context_bundle.build_context_bundle"
        },
        module_name="tools.analysis.test",
        project_symbols={
            "tools.analysis.context.build_context_bundle.build_context_bundle"
        },
    )

    print("\n================ STAGE 1: AST OUTPUT ================\n")
    for r in refs:
        print(r.ir1.surface, "->", r.ir1.fqdn)

    assert len(refs) >= 2, "Expected at least 2 symbol references"

    return refs


def run_identity_stage(refs):
    """
    STAGE 2:
    Symbol → SemanticIdentity resolution
    """
    builder = SemanticIdentityBuilder()

    identities = []

    for r in refs:
        identity = builder.build(
            r.ir1.surface,
            alias_map={
                "build_context_bundle": "tools.analysis.context.build_context_bundle.build_context_bundle"
            },
            runtime_bindings={},
            project_symbols={
                "tools.analysis.context.build_context_bundle.build_context_bundle"
            },
        )
        identities.append(identity)

    print("\n================ STAGE 2: IDENTITY OUTPUT ================\n")
    for i in identities:
        print(
            i.surface,
            "| fqdn:", i.fqdn,
            "| type:", i.identity_type,
            "| conf:", round(i.confidence, 3)
        )

    # hard invariants (your real bug detectors)
    for i in identities:
        assert "C:" not in (i.fqdn or ""), "Filesystem leakage detected in fqdn"
        assert "\\" not in (i.fqdn or ""), "Backslash leakage detected in fqdn"

    return identities


def run_classification_stage(identities):
    """
    STAGE 3:
    Identity → classification bucket
    """
    results = []

    for i in identities:
        bucket = classify_symbol(
            identity=i,
            project_symbols={
                "tools.analysis.context.build_context_bundle.build_context_bundle"
            },
            runtime_bindings={}
        )
        results.append((i.surface, bucket))

    print("\n================ STAGE 3: CLASSIFICATION OUTPUT ================\n")
    for s, b in results:
        print(s, "->", b)

    # sanity assertions (tight signal checks)
    assert ("build_context_bundle", "project") in results, "project symbol missing"
    assert any("str" in r[0] for r in results), "builtin missing"

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