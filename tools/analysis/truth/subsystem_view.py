# tools/analysis/truth/subsystem_view.py
# CLAUDE-EDIT 2026-06-17: returns SubsystemView (views.py) instead of a
# bare dict. Before this, SUBSYSTEM was the only one of the 6 Truth Layer
# views where Select(view) with no metric returned a raw dict (bracket
# access) while every other view returned a dataclass instance (attribute
# access) - a real shape inconsistency in the algebra contract, found
# while root-causing the Windows-only ROLE-view AttributeError (see
# REFACTOR OPS BOARD.md 2026-06-17 "algebra shape contract" entry).
# Same data, same "subsystems" key - just exposed as .subsystems instead
# of ["subsystems"], for parity with STRUCTURE/STABILITY/INTEGRITY/
# SUMMARY/ROLE.

from __future__ import annotations

from collections import defaultdict

from tools.analysis.truth.views import SubsystemView


def build_subsystem_view(graph) -> SubsystemView:
    """
    Deterministic subsystem extraction.

    Input:
        graph.edges

    Output:
        SubsystemView wrapping subsystem grouping based on module projection
    """

    subsystems = defaultdict(set)
    edge_counts = defaultdict(int)

    for e in graph.edges:
        caller = _module(e.caller)
        callee = _module(e.callee)

        if caller == callee:
            continue

        subsystems[caller].add(callee)
        edge_counts[caller] += 1

    return SubsystemView(
        subsystems={
            k: {
                "modules": sorted(v),
                "edge_count": edge_counts[k],
            }
            for k, v in subsystems.items()
        }
    )


def _module(symbol: str) -> str:
    parts = symbol.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
