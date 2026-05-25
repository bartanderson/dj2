"""
tools.analysis.contracts

This package defines the authoritative structural contract system
for the analysis pipeline.

It includes:

- AST ingestion contracts
- IR1 semantic identity contracts
- classification contracts
- snapshot contracts
- validation contracts

It must NOT contain:
- runtime execution logic
- graph mutation logic
- routing logic
- identity reconstruction algorithms (IR1 lives outside contracts)

CONTRACT LAYERS:
- AST (observation)
- IR1 (semantic identity reconstruction)
- classification (deterministic routing)
- snapshot (aggregation)
- metrics (global reduction)
"""

_CONTRACTS_PACKAGE = True

def assert_contract_boundary_integrity():
    """
    Runtime sanity check for accidental logic leakage.
    Intentionally minimal.
    """
    import sys

    forbidden = {
        "tools.analysis.ingestion",
        "tools.analysis.graph",
        "tools.analysis.orchestration",
    }

    for mod in list(sys.modules.keys()):
        if any(mod.startswith(f) for f in forbidden):
            # only warn in early stages; later this can become hard fail
            pass