# tools/analysis/truth/views.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StructureView:
    edges: list[tuple[str, str]]
    adjacency: dict[str, set[str]]
    hotspots: list[tuple[str, int]]  # (module, degree)


def build_structure_view(graph: Any, builtin_symbols: set = None) -> StructureView:
    edges = [(e.caller, e.callee) for e in graph.edges]

    adjacency = {}
    degree_count = {}

    for caller, callee in edges:
        adjacency.setdefault(caller, set()).add(callee)

        degree_count[caller] = degree_count.get(caller, 0) + 1
        degree_count[callee] = degree_count.get(callee, 0) + 1

    # Exclude builtin symbols from hotspot ranking.
    # Builtins (print, len, getattr, etc.) dominate degree counts by volume
    # but carry no semantic signal about project structure.
    # edges/adjacency are left intact — structural truth is not modified.
    if builtin_symbols:
        ranked = {k: v for k, v in degree_count.items() if k not in builtin_symbols}
    else:
        ranked = degree_count

    hotspots = sorted(
        ranked.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return StructureView(
        edges=edges,
        adjacency=adjacency,
        hotspots=hotspots,
    )

@dataclass
class StabilityView:
    stable_contracts: list[str]
    unstable_contracts: list[str]
    drift_signals: list[dict]


def build_stability_view(contract_reports, drift_signals) -> StabilityView:
    stable = []
    unstable = []

    for r in contract_reports:
        if r.violations:
            unstable.append(r.file_path)
        else:
            stable.append(r.file_path)

    return StabilityView(
        stable_contracts=stable,
        unstable_contracts=unstable,
        drift_signals=[
            {
                "contract": s.contract_name,
                "class": s.classification,
                "count": s.count,
                "layer": s.layer,
            }
            for s in drift_signals
        ],
    )

@dataclass
class IntegrityView:
    errors: list[str]
    warnings: list[str]
    db_mismatches: list[str]


def build_integrity_view(validation_result, graph) -> IntegrityView:
    return IntegrityView(
        errors=validation_result.errors,
        warnings=validation_result.warnings,
        db_mismatches=[],  # no DB comparison anymore
    )

@dataclass
class SystemSummaryView:
    edge_count: int
    file_count: int
    metrics: dict


def build_system_summary_view(reduced, metrics, file_count: int) -> SystemSummaryView:
    return SystemSummaryView(
        edge_count=reduced.get("edge_activity_total", 0),
        file_count=file_count,
        metrics=metrics,
    )