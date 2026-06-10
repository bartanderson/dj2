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
            expanded.add(e.caller)
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

    plan = _build_plan(expanded, primitives)

    return RouteResult(
        intent=intent,
        seed_symbols=seeds,
        expanded_symbols=expanded,
        execution_plan=plan,
        raw_query=text,
    )