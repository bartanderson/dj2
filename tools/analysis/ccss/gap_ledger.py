# tools/analysis/ccss/gap_ledger.py

from typing import Dict, Any, List, Set


def _to_set(items) -> Set[str]:
    return set(items or [])


def build_gap_ledger(prev: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:

    prev_axes = prev["pass_3"]["coverage"]["axes"]
    curr_axes = current["pass_3"]["coverage"]["axes"]

    prev_redundancy = {
        (r["symbol"], r["test_id"]): r["occurrences"]
        for r in prev["pass_3"]["coverage"]["redundancy"]
    }

    curr_redundancy = {
        (r["symbol"], r["test_id"]): r["occurrences"]
        for r in current["pass_3"]["coverage"]["redundancy"]
    }

    # -------------------------
    # STRUCTURAL DIFF
    # -------------------------
    prev_struct = _to_set(prev_axes["structural"]["covered"])
    curr_struct = _to_set(curr_axes["structural"]["covered"])

    structural_diff = {
        "added_tests": sorted(list(curr_struct - prev_struct)),
        "removed_tests": sorted(list(prev_struct - curr_struct))
    }

    # -------------------------
    # SEMANTIC DIFF
    # -------------------------
    prev_sem = _to_set(prev_axes["semantic"]["covered"])
    curr_sem = _to_set(curr_axes["semantic"]["covered"])

    semantic_diff = {
        "added_symbols": sorted(list(curr_sem - prev_sem)),
        "removed_symbols": sorted(list(prev_sem - curr_sem))
    }

    # -------------------------
    # RUNTIME DIFF
    # -------------------------
    prev_rt = _to_set(prev_axes["runtime"]["covered"])
    curr_rt = _to_set(curr_axes["runtime"]["covered"])

    runtime_diff = {
        "added_traces": sorted(list(curr_rt - prev_rt)),
        "removed_traces": sorted(list(prev_rt - curr_rt))
    }

    # -------------------------
    # REDUNDANCY DIFF
    # -------------------------
    all_keys = set(prev_redundancy.keys()) | set(curr_redundancy.keys())

    increased = []
    decreased = []

    for k in all_keys:
        prev_v = prev_redundancy.get(k, 0)
        curr_v = curr_redundancy.get(k, 0)

        if curr_v > prev_v:
            increased.append({
                "symbol": k[0],
                "test_id": k[1],
                "delta": curr_v - prev_v
            })

        elif curr_v < prev_v:
            decreased.append({
                "symbol": k[0],
                "test_id": k[1],
                "delta": prev_v - curr_v
            })

    return {
        "file_id": current["file_id"],
        "structural_diff": structural_diff,
        "semantic_diff": semantic_diff,
        "runtime_diff": runtime_diff,
        "redundancy_diff": {
            "increased": increased,
            "decreased": decreased
        }
    }