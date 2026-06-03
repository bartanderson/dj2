# tools/analysis/truth/subsystem_view.py

from __future__ import annotations

from collections import defaultdict


def build_subsystem_view(graph):
    """
    Deterministic subsystem extraction.

    Input:
        graph.edges

    Output:
        subsystem grouping based on module projection
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

    return {
        "subsystems": {
            k: {
                "modules": sorted(v),
                "edge_count": edge_counts[k],
            }
            for k, v in subsystems.items()
        }
    }


def _module(symbol: str) -> str:
    parts = symbol.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]