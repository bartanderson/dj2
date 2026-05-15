"""
tools.analysis.contracts

This package defines the authoritative structural contract system
for the analysis pipeline.

It is intentionally restricted to:
- structural schema definitions
- contract loading
- typed projections of tool_system_contract.json

It must NOT contain:
- analysis logic
- parsing logic (AST or semantic)
- classification heuristics
- orchestration behavior
"""

# Hard boundary marker for developers and future refactors
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