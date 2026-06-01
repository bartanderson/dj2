# tools/analysis/ccss/snapshot_compare.py

import json
from pathlib import Path
from typing import Dict, Any


def load_snapshot(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_snapshots(prev_path: Path, curr_path: Path) -> Dict[str, Any]:
    """
    Deterministic deep comparison of two PASS3 snapshots.
    No heuristics. Pure structural diff.
    """

    prev = load_snapshot(prev_path)
    curr = load_snapshot(curr_path)

    def _safe_set(x):
        return set(x or [])

    prev_symbols = _safe_set(prev.get("symbols"))
    curr_symbols = _safe_set(curr.get("symbols"))

    prev_tests = _safe_set(prev.get("tests"))
    curr_tests = _safe_set(curr.get("tests"))

    return {
        "prev": str(prev_path),
        "curr": str(curr_path),

        "symbol_diff": {
            "added": sorted(curr_symbols - prev_symbols),
            "removed": sorted(prev_symbols - curr_symbols),
        },

        "test_diff": {
            "added": sorted(curr_tests - prev_tests),
            "removed": sorted(prev_tests - curr_tests),
        },

        "stable": prev == curr
    }