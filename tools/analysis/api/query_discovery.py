# tools/analysis/api/query_discovery.py

from __future__ import annotations

from typing import Any, List


# =========================================================
# SYMBOL LISTING (GLOBAL TRUTH SURFACE)
# =========================================================

def list_symbols(graph: Any) -> List[str]:
    """
    Returns raw symbol universe from graph edges.
    """

    edges = getattr(graph, "edges", [])

    symbols = set()

    for e in edges:
        if getattr(e, "caller", None):
            symbols.add(e.caller)
        if getattr(e, "callee", None):
            symbols.add(e.callee)

    return sorted(symbols)


# =========================================================
# SIMPLE SYMBOL SEARCH (TEXT MATCH ONLY)
# =========================================================

def find_symbols(graph, text: str, limit: int = 50):
    """
    Deterministic scoring-based symbol retrieval.
    No embeddings. No ML. Just structure + overlap.
    """

    text_tokens = set(
        text.lower()
        .replace("_", " ")
        .replace(".", " ")
        .split()
    )

    scored = []

    for sym in list_symbols(graph):

        sym_tokens = sym.lower().replace(".", " ").replace("_", " ").split()

        leaf = sym.split(".")[-1].lower()

        # -------------------------------------------------
        # SIGNAL 1: TOKEN OVERLAP
        # -------------------------------------------------
        overlap = len(text_tokens.intersection(sym_tokens))

        # -------------------------------------------------
        # SIGNAL 2: DIRECT SUBSTRING BOOST
        # -------------------------------------------------
        substring = 1 if text.lower() in sym.lower() else 0

        # -------------------------------------------------
        # FINAL SCORE
        # -------------------------------------------------
        exact_leaf = 5 if leaf in text.lower() else 0

        score = overlap + substring + exact_leaf

        if score > 0:
            scored.append((score, sym))

    # sort by strength of match
    scored.sort(reverse=True, key=lambda x: x[0])

    return [sym for _, sym in scored[:limit]]


# =========================================================
# FILE DISCOVERY (FROM GRAPH EDGES ONLY)
# =========================================================

def _extract_file(symbol: str):
    # take module path only (everything before last dot)
    if "." in symbol:
        return ".".join(symbol.split(".")[:-1])
    return symbol

def find_files(graph: Any, text: str, limit: int = 50) -> List[str]:
    """
    Extract file-level symbols if present in graph.
    """

    edges = getattr(graph, "edges", [])

    files = set()

    for e in edges:
        caller = getattr(e, "caller", "")
        callee = getattr(e, "callee", "")

        files.add(_extract_file(caller))
        files.add(_extract_file(callee))

    text = text.lower()

    results = [f for f in files if text in f.lower()]

    return results[:limit]