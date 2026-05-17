# tools/analysis/tests/core/test_context_classification.py

from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.context_classification import (
    classify_symbol_with_context,
)


def test_context_classification_project():

    ctx = ProjectGraphContext(
        project_prefixes=["tools."],
        project_symbols={
            "tools.analysis.example.main"
        }
    )

    result = classify_symbol_with_context(
        "tools.analysis.example.main",
        ctx,
    )

    assert result == "project"


def test_context_classification_builtin():

    ctx = ProjectGraphContext()

    result = classify_symbol_with_context(
        "print",
        ctx,
    )

    assert result == "builtin"