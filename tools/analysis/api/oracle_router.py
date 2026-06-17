# tools/analysis/api/oracle_router.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from tools.analysis.oracle.symbol_noise import is_noise_symbol

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


def _is_valid_symbol(sym: str, builtin_symbols=frozenset()) -> bool:
    """
    Rejects runtime / python noise / structural artifacts.

    builtin_symbols is the DB-authoritative set from
    DBOracle.builtin_symbols() (bucket == "builtin" in symbol_references).
    This is the SAME classification seed discovery uses to exclude
    builtins - there is no separate hardcoded noise list anymore, so
    expansion-time and discovery-time filtering cannot drift apart.
    """
    return not is_noise_symbol(sym, builtin_symbols)


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

    # CLAUDE-EDIT 2026-06-16: per Truth.md Phase 3 Row 1 - "purpose of
    # this file" / "why does X exist" / "role of X" style questions
    # previously fell through to general_query and got a content-blind
    # STABILITY+INTEGRITY answer regardless of which file was asked
    # about. Routes to the new ROLE view instead (see role_view() /
    # Assessor.responsibility_map()).
    if "purpose" in t or "why does" in t or "why is" in t or "role of" in t or "what role" in t or "what kind of" in t:
        return "role_query"

    return "general_query"


# =========================================================
# SEED SYMBOL DISCOVERY
# =========================================================

def _seed_symbols(text: str, graph, find_symbols_fn) -> List[str]:
    """
    Step 1: map query -> candidate symbols
    """

    candidates = find_symbols_fn(text, limit=20)

    return candidates


# =========================================================
# GRAPH EXPANSION STRATEGY
# NOTE: _expand() removed - route_query uses _route_expand() directly
# =========================================================


# =========================================================
# PRIMITIVE SELECTION
# =========================================================

def _select_primitives(intent: str) -> List[str]:
    """
    Maps intent -> graph primitives
    """

    if intent == "impact_query":
        return ["impact", "context"]

    if intent == "reverse_query":
        return ["impact"]

    if intent == "surface_query":
        return ["surface", "context"]

    if intent == "role_query":
        return ["role"]

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
def route_query(text: str, graph, find_symbols_fn, logger=None, builtin_symbols=None) -> RouteResult:
    """
    Seed authority contract:
    find_symbols_fn MUST be DBOracle.discover_seed_symbols, seeds must come from DB truth only.

    logger: optional callable(str) for observability output.
    Pass None (default) for silent operation.

    builtin_symbols: DB-authoritative builtin set (DBOracle.builtin_symbols()).
    Callers should always pass this; expansion-time noise filtering relies
    on it instead of a hardcoded word list. Defaults to empty set if omitted
    (expansion still filters accessor-chain noise, just not builtins).
    """

    intent = _detect_intent(text)

    #seeds = _seed_symbols(text, graph, find_symbols_fn)
    seeds = find_symbols_fn(text, limit=20)

    expand_result = _route_expand(graph, seeds, intent, builtin_symbols=builtin_symbols or frozenset())

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
        # promote key reasoning surfaces to top level for QuerySessionResult
        "seed_paths": expansion_trace.get("seed_paths", {}),
        "node_reasons": expansion_trace.get("node_reasons", {}),
        "edges": expansion_trace.get("edges", {}),
    }

    filtered = _prune(graph, expanded, seeds)

    primitives = _select_primitives(intent)
    plan = _build_plan(filtered, primitives, trace)

    # -------------------------------------------------
    # OBSERVABILITY (logger-gated - silent by default)
    # -------------------------------------------------
    if logger:
        logger(f"\n=== ROUTE METRICS ===")
        logger(f"intent: {intent}")
        logger(f"seed_count: {len(seeds)}")
        logger(f"expanded_count: {len(expanded)}")
        logger(f"filtered_count: {len(filtered)}")
        logger(f"removed_count: {len(expanded) - len(filtered)}")

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


def _route_expand(graph, seeds, intent, builtin_symbols=frozenset()):
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
            if not _is_valid_symbol(n, builtin_symbols):
                continue
            add(n, f"forward:{node}", source=node)
            expand_forward(n, depth - 1)

    def expand_reverse(node, depth=1):
        if depth <= 0:
            return

        for n in reverse.get(node, []):
            if not _is_valid_symbol(n, builtin_symbols):
                continue
            add(n, f"reverse:{node}", source=node)
            expand_reverse(n, depth - 1)

    intent_budget = {
        "surface_query": {
            "forward_depth": 1,
            "reverse": False,
            "reverse_depth": 0,
            "two_hop": False,
        },
        "impact_query": {
            "forward_depth": 0,
            "reverse": True,
            "reverse_depth": 2,
            "two_hop": False,
        },
        "reverse_query": {
            "forward_depth": 0,
            "reverse": True,
            "reverse_depth": 2,
            "two_hop": False,
        },
        "general_query": {
            "forward_depth": 1,
            "reverse": True,
            "reverse_depth": 1,
            "two_hop": False,
        },
        "role_query": {
            # ROLE is a global, file-level classification - it doesn't
            # depend on which symbol was mentioned in the question, so
            # there's nothing for graph traversal to add. Zero budget
            # is the honest answer, not a placeholder.
            "forward_depth": 0,
            "reverse": False,
            "reverse_depth": 0,
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
            expand_reverse(s, depth=budget["reverse_depth"])

    # -------------------------
    # NODE REASONS
    # Derive human-readable per-node explanation from seed_paths.
    # seed_paths[node] = list of raw reasons e.g. ["seed"], ["forward:X", "reverse:Y"]
    # node_reasons[node] = single readable string summarising inclusion reason
    # -------------------------
    node_reasons = {}

    for node, reasons in trace["seed_paths"].items():
        if "seed" in reasons:
            node_reasons[node] = "direct seed match"
        else:
            forward_sources = [r.split(":", 1)[1] for r in reasons if r.startswith("forward:")]
            reverse_sources = [r.split(":", 1)[1] for r in reasons if r.startswith("reverse:")]

            parts = []
            if forward_sources:
                parts.append(f"reachable from {', '.join(forward_sources[:2])}")
            if reverse_sources:
                parts.append(f"depends on {', '.join(reverse_sources[:2])}")

            node_reasons[node] = "; ".join(parts) if parts else "included via traversal"

    trace["node_reasons"] = node_reasons

    return {
        "nodes": list(expanded),
        "trace": trace
    }
