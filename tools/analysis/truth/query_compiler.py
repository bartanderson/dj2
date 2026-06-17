# tools/analysis/truth/query_compiler.py
# CLAUDE-EDIT 2026-06-16: full rewrite of Layer 4 compiler. Was a rule-based
# stub only. Now tries local Ollama (llama3.2:3b @ localhost:11434/api/generate)
# first, validates output through QueryPlanner, falls back to the original
# rule-based intent->AST table on any failure (connection error, timeout,
# bad JSON, invalid view/combine). Does NOT use Anthropic API - local only.
#
# LAYER 4 - QUERY COMPILER
#
# Translates natural language -> valid Query AST.
#
# Two modes (selected automatically):
#   1. Ollama mode  - calls llama3.2:3b via local Ollama API.
#                     The model is given the closed algebra spec and must
#                     emit only valid JSON. Output is validated through
#                     QueryPlanner before use. Falls back to rule-based
#                     on any failure (service down, invalid JSON, invalid AST).
#
#   2. Rule-based fallback - deterministic intent->AST table.
#                     Always available. Used when Ollama is unreachable or
#                     the model output fails validation.
#
# CONTRACT (from Truth Kernel spec):
#   INPUT:  natural language text + detected intent
#   OUTPUT: valid QueryPlan (Select / Combine only, from registry)
#   NEVER:  invents new views, emits invalid AST, raises to caller

import json
import logging

import requests

from tools.analysis.truth.query_ast import Select, Combine
from tools.analysis.truth.query_plan import QueryPlanner, QuerySemanticsRegistry

logger = logging.getLogger(__name__)

_registry = QuerySemanticsRegistry()
_planner = QueryPlanner(_registry)

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 10  # seconds - fail fast, don't block the pipeline

# =========================================================
# CLOSED-WORLD SPEC (fed verbatim to the model)
# =========================================================

_ALGEBRA_SPEC = """\
You are a query compiler for a closed-world code analysis system.
Your ONLY job is to translate a natural language question into a JSON query AST.
Output JSON only. No explanation. No markdown. No extra keys.

VALID VIEWS: STRUCTURE, STABILITY, INTEGRITY, SUMMARY, SUBSYSTEM, ROLE

VALID METRICS PER VIEW:
  STRUCTURE: edges, adjacency, hotspots
  STABILITY: stable_contracts, unstable_contracts, drift_signals
  INTEGRITY: errors, warnings, db_mismatches
  SUMMARY:   edge_count, file_count, metrics
  SUBSYSTEM: subsystems
  ROLE:      files, totals

VALID COMBINE PAIRS (unordered):
  (STRUCTURE, STABILITY)
  (STRUCTURE, INTEGRITY)
  (SUMMARY,   STABILITY)
  (SUBSYSTEM, STRUCTURE)
  (STABILITY, INTEGRITY)

QUERY TYPES:
  Select(view)           -> {"type": "select", "view": "VIEW"}
  Select(view, metric)   -> {"type": "select", "view": "VIEW", "metric": "METRIC"}
  Combine(left, right)   -> {"type": "combine", "left": <node>, "right": <node>}

MAPPING GUIDANCE:
  "what depends on X" / "who calls X" / "what breaks if X changes"
    -> {"type":"combine","left":{"type":"select","view":"STRUCTURE"},"right":{"type":"select","view":"INTEGRITY"}}

  "what does X call" / "show surface of X" / "forward dependencies"
    -> {"type":"combine","left":{"type":"select","view":"STRUCTURE"},"right":{"type":"select","view":"STABILITY"}}

  "show hotspots" / "most connected symbols"
    -> {"type":"select","view":"STRUCTURE","metric":"hotspots"}

  "system health" / "stability overview"
    -> {"type":"combine","left":{"type":"select","view":"STABILITY"},"right":{"type":"select","view":"INTEGRITY"}}

  "what is the purpose of X" / "why does X exist" / "what is the role of X"
    -> {"type":"select","view":"ROLE"}

  general / unclear
    -> {"type":"select","view":"STRUCTURE"}
"""

# =========================================================
# RULE-BASED FALLBACK (always deterministic)
# =========================================================

_INTENT_TO_AST = {
    "impact_query":  lambda: Combine(Select("STRUCTURE"), Select("INTEGRITY")),
    "surface_query": lambda: Combine(Select("STRUCTURE"), Select("STABILITY")),
    "reverse_query": lambda: Combine(Select("STRUCTURE"), Select("INTEGRITY")),
    "general_query": lambda: Combine(Select("STABILITY"), Select("INTEGRITY")),
    # CLAUDE-EDIT 2026-06-16: per Truth.md Phase 3 Row 1 / Row 2 - routes
    # "purpose of file" style questions to the new ROLE view instead of
    # falling through to general_query's content-blind STABILITY+INTEGRITY
    # default. Select-only (not Combine): ROLE isn't in VALID_COMBINES yet,
    # since no question asked so far has needed it joined with anything.
    "role_query":    lambda: Select("ROLE"),
}

_INTENT_EXPLANATIONS = {
    "impact_query":  "STRUCTURE+INTEGRITY: who depends on this symbol, and are those callers healthy?",
    "surface_query": "STRUCTURE+STABILITY: what does this symbol call, and is that surface stable?",
    "reverse_query": "STRUCTURE+INTEGRITY: reverse dependency view with integrity check.",
    "general_query": "STABILITY+INTEGRITY: full diagnostic view of system health.",
    "role_query":    "ROLE: what kind of work does this file do, per the DB-backed responsibility classification.",
}

_DEFAULT_AST = lambda: Select("STRUCTURE")


def _rule_based_ast(intent: str):
    return _INTENT_TO_AST.get(intent, _DEFAULT_AST)()


# =========================================================
# JSON -> AST PARSER
# =========================================================

def _parse_ast_node(node: dict):
    """
    Recursively parse a JSON dict into a Select or Combine AST node.
    Raises ValueError on any structural problem.
    """
    t = node.get("type")
    if t == "select":
        view = node.get("view", "").upper()
        metric = node.get("metric")
        return Select(view, metric)
    elif t == "combine":
        left  = _parse_ast_node(node["left"])
        right = _parse_ast_node(node["right"])
        return Combine(left, right)
    else:
        raise ValueError(f"Unknown node type: {t!r}")


# =========================================================
# OLLAMA COMPILER CORE
# =========================================================

def _compile_via_ollama(text: str, intent: str):
    """
    Call llama3.2:3b via local Ollama to produce a Query AST.
    Returns a validated QueryPlan, or None on any failure.
    """
    prompt = (
        f"Natural language query: {text!r}\n"
        f"Detected intent: {intent!r}\n\n"
        "Output the query AST as JSON only."
    )

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": _ALGEBRA_SPEC,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 128},
            },
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()

        # strip markdown fences if the model added them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        node_dict = json.loads(raw)
        ast_node  = _parse_ast_node(node_dict)
        plan      = _planner.plan(ast_node)   # validates against registry
        return plan

    except requests.exceptions.ConnectionError:
        logger.debug("Ollama not reachable - using rule-based compiler")
        return None
    except requests.exceptions.Timeout:
        logger.debug("Ollama timeout - using rule-based compiler")
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("Ollama compiler output invalid: %s", e)
        return None
    except Exception as e:
        logger.warning("Ollama compiler unexpected failure: %s", e)
        return None


# =========================================================
# PUBLIC API
# =========================================================

def compile_query(intent: str, text: str = ""):
    """
    Translate intent (and optionally the raw NL text) into a QueryPlan.
    Tries Ollama first; falls back to rule-based table on any failure.
    Returns: QueryPlan (always valid, never raises)
    """
    if text:
        plan = _compile_via_ollama(text, intent)
        if plan is not None:
            return plan

    ast_node = _rule_based_ast(intent)
    return _planner.plan(ast_node)


def compile_and_explain(intent: str, text: str = "") -> dict:
    """
    Returns the compiled plan plus a human-readable explanation.
    """
    plan = None
    ai_used = False

    if text:
        plan = _compile_via_ollama(text, intent)
        if plan is not None:
            ai_used = True

    if plan is None:
        ast_node = _rule_based_ast(intent)
        plan = _planner.plan(ast_node)

    explanation = _INTENT_EXPLANATIONS.get(intent, "Default structural projection.")
    if ai_used:
        explanation = f"[llama] {explanation}"

    return {
        "intent":      intent,
        "ast":         repr(plan.root),
        "explanation": explanation,
        "compiler":    "llama" if ai_used else "rule-based",
        "plan":        plan,
    }
