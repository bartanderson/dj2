# simple health shell

from tools.analysis.tests.observability.system_health import compute_health, print_health

# TEMP SNAPSHOT BUILDER (from existing engine print structure)
def build_snapshot():
    return {
        # these are the only fields your health tool currently needs
        "file_count": 0,                   # optional if unknown
        "symbol_reference_count": 0,       # optional if unknown
        "edge_count": 0,                   # optional if unknown

        # optional richer field (for later drift analysis)
        "results": []
    }


snapshot = build_snapshot()

report = compute_health(snapshot)
print_health(report)