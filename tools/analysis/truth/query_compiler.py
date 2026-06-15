# tools/analysis/truth/query_compiler.py
#
# LAYER 4 — QUERY COMPILER (rule-based stub)
#
# This is the AI surface of the Truth Kernel. Currently implemented as
# a deterministic rule-based mapper from intent → AST. The AI version
# will replace _compile_from_intent() only — everything else stays.
#
# CONTRACT (from Truth Kernel spec):
#   INPUT:  natural language text + detected intent
#   OUTPUT: valid AST (Select / Combine only, from registry)
#   NEVER:  invents new views, expands beyond algebra, guesses metrics

from tools.analysis.truth.query_ast import Select, Combine
from tools.analysis.truth.query_plan import QueryPlanner, QuerySemanticsRegistry

_registry = QuerySemanticsRegistry()
_planner = QueryPlanner(_registry)


# =========================================================
# INTENT → AST MAPPING (rule-based — AI replacement target)
# =========================================================

_INTENT_TO_AST = {
    # "what depends on X" — who calls X (reverse traversal)
    # → structural graph + integrity check
    "impact_query": lambda: Combine(
        Select("STRUCTURE"),
        Select("INTEGRITY"),
    ),

    # "show surface of X" — what X calls (forward traversal)
    # → structural graph + stability check
    "surface_query": lambda: Combine(
        Select("STRUCTURE"),
        Select("STABILITY"),
    ),

    # "what affects X" — reverse deps
    "reverse_query": lambda: Combine(
        Select("STRUCTURE"),
        Select("INTEGRITY"),
    ),

    # general — full diagnostic view
    "general_query": lambda: Combine(
        Select("STABILITY"),
        Select("INTEGRITY"),
    ),
}

_INTENT_TO_AST_DEFAULT = lambda: Select("STRUCTURE")


def compile_query(intent: str):
    """
    Map a detected intent string to a valid AST node.
    Validates through the planner before returning — if the mapping
    produces an invalid AST the error surfaces here, not at execution.

    Returns: QueryPlan
    """
    factory = _INTENT_TO_AST.get(intent, _INTENT_TO_AST_DEFAULT)
    ast = factory()
    return _planner.plan(ast)


def compile_and_explain(intent: str) -> dict:
    """
    Returns the compiled plan plus a human-readable explanation
    of why this AST was selected for this intent.
    """
    plan = compile_query(intent)

    explanations = {
        "impact_query":  "Combined STRUCTURE+INTEGRITY: who depends on this symbol, and are those dependencies healthy?",
        "surface_query": "Combined STRUCTURE+STABILITY: what does this symbol call, and is that surface stable?",
        "reverse_query": "Combined STRUCTURE+INTEGRITY: reverse dependency view with integrity check.",
        "general_query": "Combined STABILITY+INTEGRITY: full diagnostic view of system health.",
    }

    return {
        "intent": intent,
        "ast": repr(plan.root),
        "explanation": explanations.get(intent, "Default structural projection."),
        "plan": plan,
    }