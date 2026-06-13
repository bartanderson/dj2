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

    candidates = find_symbols_fn(text, limit=20)

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

def _build_plan(symbols: List[str], primitives: List[str], trace: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Deterministic execution structure + explainability trace
    """

    return {
        "symbols": symbols,
        "primitives": primitives,
        "trace": trace or {}
    }


# =========================================================
# MAIN ROUTER ENTRYPOINT
# =========================================================
def _apply_intent_weights(symbols, intent, graph, seeds):
    # phase 1: score, don’t branch
    # phase 2: filter, don’t expand

    weights = {
        "surface_query": {"reverse": 0.2},
        "impact_query": {"forward": 0.3},
        "reverse_query": {"forward": 0.2},
        "general_query": {"all": 0.7},
    }

    # placeholder scoring pass (keep simple for now)
    return symbols

def route_query(text: str, graph, find_symbols_fn) -> RouteResult:

    intent = _detect_intent(text)

    #seeds = _seed_symbols(text, graph, find_symbols_fn)
    seeds = find_symbols_fn(text, limit=20)

    expand_result = _route_expand(graph, seeds, intent)

    expanded = expand_result["nodes"]
    expansion_trace = expand_result["trace"]

    # -------------------------------------------------
    # TRACE (canonical, single source of truth)
    # -------------------------------------------------
    trace = {
        "seeds": seeds,
        "intent": intent,
        "expanded": expanded,
        "expansion_trace": expansion_trace,
    }

    filtered = _prune(graph, expanded, seeds)

    primitives = _select_primitives(intent)
    plan = _build_plan(filtered, primitives, trace)

    # -------------------------------------------------
    # DEBUG / OBSERVABILITY (safe, non-invasive)
    # -------------------------------------------------
    print("\n=== ROUTE METRICS ===")
    print("intent:", intent)
    print("seed_count:", len(seeds))
    print("expanded_count:", len(expanded))
    print("filtered_count:", len(filtered))
    print("removed_count:", len(expanded) - len(filtered))

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


def _route_expand(graph, seeds, intent):
    edges = getattr(graph, "edges", [])

    forward = {}
    reverse = {}

    for e in edges:
        forward.setdefault(e.caller, set()).add(e.callee)
        reverse.setdefault(e.callee, set()).add(e.caller)

    visited = set()
    expanded = set()

    trace = {
        "seed_paths": {},   # node -> reasons
        "edges": {}         # parent -> children
    }

    def add(node, reason, source=None):
        if not node:
            return

        if node not in visited:
            visited.add(node)
            expanded.add(node)

        trace["seed_paths"].setdefault(node, []).append(reason)

        if source:
            trace["edges"].setdefault(source, []).append(node)

    def expand_forward(node, depth=1):
        if depth <= 0:
            return

        for n in forward.get(node, []):
            add(n, f"forward:{node}", source=node)
            expand_forward(n, depth - 1)

    def expand_reverse(node):
        for n in reverse.get(node, []):
            add(n, f"reverse:{node}", source=node)

    intent_budget = {
        "surface_query": {
            "forward_depth": 1,
            "reverse": False,
            "two_hop": False,
        },
        "impact_query": {
            "forward_depth": 0,
            "reverse": True,
            "two_hop": False,
        },
        "reverse_query": {
            "forward_depth": 0,
            "reverse": True,
            "two_hop": False,
        },
        "general_query": {
            "forward_depth": 1,
            "reverse": True,
            "two_hop": False,
        },
    }

    budget = intent_budget.get(intent, intent_budget["general_query"])

    for s in seeds:
        add(s, "seed")

        # -------------------------
        # FORWARD EXPANSION
        # -------------------------
        if budget["forward_depth"] >= 1:
            expand_forward(s, depth=budget["forward_depth"])

        # -------------------------
        # REVERSE EXPANSION
        # -------------------------
        if budget["reverse"]:
            expand_reverse(s)

        # -------------------------
        # 2-HOP (DISABLED FOR NOW)
        # -------------------------
        if budget["two_hop"]:
            for n in forward.get(s, []):
                for n2 in forward.get(n, []):
                    add(n2, f"forward_2hop:{n}", source=n)

    return {
        "nodes": list(expanded),
        "trace": trace
    }