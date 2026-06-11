# tools/analysis/api/oracle_router.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# =========================================================
# ROUTE RESULT CONTRACT (STABLE OUTPUT SHAPE)
# =========================================================

@dataclass
class RouteResult:
    intent: str
    seed_symbols: List[str]
    expanded_symbols: List[str]
    execution_plan: Dict[str, Any]
    raw_query: str


def _is_valid_symbol(sym: str) -> bool:
    # rejects runtime / python noise / structural artifacts
    if not sym:
        return False

    if sym.startswith("<"):
        return False

    noise = {
        "run", "len", "print", "getattr", "set", "int", "str",
        "any", "all", "dict", "list"
    }

    if sym in noise:
        return False

    return True


# =========================================================
# INTENT DETECTION (LIGHTWEIGHT, NOT "AI")
# =========================================================

def _detect_intent(text: str) -> str:
    t = text.lower()

    if "what depends" in t or "impact" in t:
        return "impact_query"

    if "what uses" in t or "used by" in t:
        return "reverse_query"

    if "what does" in t or "surface" in t:
        return "surface_query"

    return "general_query"


# =========================================================
# SEED SYMBOL DISCOVERY
# =========================================================

def _seed_symbols(text: str, graph, find_symbols_fn) -> List[str]:
    """
    Step 1: map query → candidate symbols
    """

    candidates = find_symbols_fn(graph, text, limit=20)

    return candidates


# =========================================================
# GRAPH EXPANSION STRATEGY (BASIC V1)
# =========================================================

def _expand(graph, symbols: List[str]) -> List[str]:
    """
    Step 2: expand symbol set using local edges
    """

    expanded = set(symbols)

    edges = getattr(graph, "edges", [])

    for e in edges:
        if e.caller in symbols or e.callee in symbols:

            if _is_valid_symbol(e.caller):
                expanded.add(e.caller)

            if _is_valid_symbol(e.callee):
                expanded.add(e.callee)

    return sorted(expanded)


# =========================================================
# PRIMITIVE SELECTION
# =========================================================

def _select_primitives(intent: str) -> List[str]:
    """
    Maps intent → graph primitives
    """

    if intent == "impact_query":
        return ["impact", "context"]

    if intent == "reverse_query":
        return ["impact"]

    if intent == "surface_query":
        return ["surface", "context"]

    return ["context", "surface", "impact"]


# =========================================================
# EXECUTION PLAN BUILDER
# =========================================================

def _build_plan(symbols: List[str], primitives: List[str]) -> Dict[str, Any]:
    """
    Produces deterministic execution structure
    """

    return {
        "symbols": symbols,
        "primitives": primitives,
    }


# =========================================================
# MAIN ROUTER ENTRYPOINT
# =========================================================

def route_query(text: str, graph, find_symbols_fn) -> RouteResult:

    intent = _detect_intent(text)

    seeds = _seed_symbols(text, graph, find_symbols_fn)

    expanded = _expand(graph, seeds)

    primitives = _select_primitives(intent)

    filtered = _prune(graph, expanded, seeds)

    plan = _build_plan(filtered, primitives)

    print("\n=== SYMBOL QUALITY CHECK ===")
    print("raw expanded:", len(expanded))
    print("final pruned:", len(_prune(graph, expanded, seeds)))

    return RouteResult(
        intent=intent,
        seed_symbols=seeds,
        expanded_symbols=expanded,
        execution_plan=plan,
        raw_query=text,
    )

def _score_symbol(symbol: str, seeds: List[str], graph) -> float:
    """
    Deterministic relevance score.
    """

    score = 0.0

    # -------------------------------------------------
    # 1. DIRECT SEED MATCH BOOST
    # -------------------------------------------------
    if symbol in seeds:
        score += 5.0

    # -------------------------------------------------
    # 2. NAME OVERLAP WITH SEEDS
    # -------------------------------------------------
    for s in seeds:
        if s.split(".")[-1] in symbol:
            score += 2.0

    # -------------------------------------------------
    # 3. GRAPH CONNECTIVITY SIGNAL
    # -------------------------------------------------
    edges = getattr(graph, "edges", [])

    degree = 0
    for e in edges:
        if e.caller == symbol or e.callee == symbol:
            degree += 1

    score += min(degree * 0.1, 3.0)

    return score

def _prune(graph, symbols: List[str], seeds: List[str], limit: int = 40) -> List[str]:
    """
    Keeps only the most relevant execution nodes.
    """

    scored = []

    for sym in symbols:
        score = _score_symbol(sym, seeds, graph)
        scored.append((score, sym))

    scored.sort(reverse=True, key=lambda x: x[0])

    return [s for _, s in scored[:limit]]

