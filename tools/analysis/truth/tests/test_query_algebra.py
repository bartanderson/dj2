# tools/analysis/truth/tests/test_query_algebra.py

import pytest

from tools.analysis.truth.query_ast import Select, Combine, Filter
from tools.analysis.truth.query_plan import QueryPlanner, QuerySemanticsRegistry


registry = QuerySemanticsRegistry()
planner = QueryPlanner(registry)


def plan(q):
    return planner.plan(q).root


# -------------------------
# VALID COMBINES
# -------------------------

def test_valid_structure_stability():
    q = Combine(
        Select("STRUCTURE"),
        Select("STABILITY"),
    )
    plan(q)


def test_valid_structure_integrity():
    q = Combine(
        Select("STRUCTURE"),
        Select("INTEGRITY"),
    )
    plan(q)


# -------------------------
# INVALID COMBINES
# -------------------------

def test_invalid_same_view():
    q = Combine(
        Select("STRUCTURE"),
        Select("STRUCTURE"),
    )

    with pytest.raises(ValueError):
        plan(q)


def test_invalid_unregistered_combine():
    q = Combine(
        Select("STABILITY"),
        Select("INTEGRITY"),
    )

    with pytest.raises(ValueError):
        plan(q)


# -------------------------
# STRUCTURAL RULES
# -------------------------

def test_nested_combine_rejected():
    q = Combine(
        Combine(
            Select("STRUCTURE"),
            Select("STABILITY"),
        ),
        Select("INTEGRITY"),
    )

    with pytest.raises(ValueError):
        plan(q)


# -------------------------
# FILTER BASIC SAFETY
# -------------------------

def test_filter_node_allowed():
    f = Filter(key="edges", op=">", value=10)
    assert isinstance(f, Filter)