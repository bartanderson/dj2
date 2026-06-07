# tools/analysis/engine/snapshot_stub.py

from typing import Dict, Any


def build_snapshot_stub(
    inventory: Dict[str, Any],
    db_totals: Dict[str, int],
) -> Dict[str, Any]:
    """
    Pipeline-side projection of engine snapshot.

    IMPORTANT RULE:
    - This does NOT compute anything new.
    - It only reduces already-known data into SnapshotV1 shape.
    """

    buckets = inventory.get("buckets", {}) or {}

    return {
        "file_count": int(db_totals.get("file_count", 0)),
        "symbol_reference_count": int(db_totals.get("symbol_reference_count", 0)),
        "edge_count": int(db_totals.get("edge_count", 0)),

        "buckets": {
            "project": int(buckets.get("project", 0)),
            "runtime": int(buckets.get("runtime", 0)),
            "builtin": int(buckets.get("builtin", 0)),
            "stdlib": int(buckets.get("stdlib", 0)),
            "external": int(buckets.get("external", 0)),
            "unresolved": int(buckets.get("unresolved", 0)),
        }
    }