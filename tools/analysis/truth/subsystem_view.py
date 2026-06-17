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
#
# CLAUDE-EDIT 2026-06-17 (later): _module() now takes an optional
# module_map (DBOracle.symbol_module_map() - see oracle/db_oracle.py
# Phase 2 discovery API) and prefers it over the old dotted-name-split
# heuristic. Root cause being fixed (Truth.md Phase 3 Row 4 / REFACTOR
# OPS BOARD.md NEXT STEPS Track B item 2): this codebase's real symbols
# are mostly bare function names with no dots, so the old heuristic
# ("first two dotted segments, else the whole name") returned the bare
# name itself for almost everything, fragmenting SUBSYSTEM into ~355
# singleton groups instead of real architectural groupings. module_map
# is built from real `symbols` table declarations (true file_path, not
# guessed), so any symbol with a captured function/class declaration now
# groups by its actual file's directory. The dotted-name heuristic is
# kept as a fallback ONLY for symbols absent from module_map (builtins,
# external-library calls, accessor-chain noise) - it is no longer the
# only source of truth, just the honest answer when the DB has nothing
# better. Passing no module_map (default None) preserves the exact prior
# behavior, so existing callers/tests that seed only symbol_references/
# graph_edges (no `symbols` table rows) are unaffected - see
# tests/regression/test_run_algebra_end_to_end.py's seeded-DB test.

from __future__ import annotations

from collections import defaultdict

from tools.analysis.truth.views import SubsystemView


def build_subsystem_view(graph, module_map: dict | None = None) -> SubsystemView:
    """
    Deterministic subsystem extraction.

    Input:
        graph.edges
        module_map: optional symbol -> module map (DBOracle.
            symbol_module_map()), real DB-backed module resolution.
            Falls back to dotted-name splitting for any symbol not in
            the map (or when module_map is omitted entirely).

    Output:
        SubsystemView wrapping subsystem grouping based on module projection
    """

    subsystems = defaultdict(set)
    edge_counts = defaultdict(int)

    for e in graph.edges:
        caller = _module(e.caller, module_map)
        callee = _module(e.callee, module_map)

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


def _module(symbol: str, module_map: dict | None = None) -> str:
    if module_map:
        if symbol in module_map:
            return module_map[symbol]
        tail = symbol.split(".")[-1]
        if tail in module_map:
            return module_map[tail]

    # Fallback: original dotted-name heuristic, for symbols with no
    # DB-backed declaration (builtins, external libs, unresolved
    # accessor chains) or when no module_map was supplied at all.
    parts = symbol.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
