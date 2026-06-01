# tools/analysis/ccss/pass1.py

from typing import Dict, Any, List


# -----------------------------
# PASS2 — SEMANTIC ENRICHMENT
# -----------------------------
# Contract:
# - NEVER mutate PASS1 structure
# - NEVER reorder symbols
# - NEVER delete symbols
# - ONLY annotate symbols deterministically


def classify_context(context: str) -> str:
    """
    Deterministic context passthrough.
    PASS2 does NOT infer meaning beyond PASS1 tags.
    """
    # PASS1 already defines:
    # import | call | attribute | assignment | builtin | unknown
    return context


def enrich_symbol(symbol: Dict[str, Any]) -> Dict[str, Any]:
    """
    PASS2 enrichment step for a single symbol.

    No heuristics, only structural pass-through + normalized annotations.
    """

    return {
        "symbol_index": symbol["symbol_index"],
        "symbol_uid": symbol["symbol_uid"],
        "surface": symbol["surface"],
        "context": classify_context(symbol.get("context", "unknown")),
        "line": symbol.get("line"),
    }


def run_pass2(pass1: Dict[str, Any]) -> Dict[str, Any]:
    """
    PASS2 input: PASS1 output
    PASS2 output: enriched PASS1 (same structure, enriched symbols)
    """

    out = {
        "file_id": pass1["file_id"],
        "tests": []
    }

    for test in pass1.get("tests", []):
        enriched_test = {
            "test_name": test["test_name"],
            "test_id": test["test_id"],
            "start_line": test["start_line"],
            "end_line": test["end_line"],
            "symbols": []
        }

        for sym in test.get("symbols", []):
            enriched_test["symbols"].append(enrich_symbol(sym))

        out["tests"].append(enriched_test)

    return out