# tools/analysis/validation/system_validator.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


class SystemValidator:
    """
    Pure validation layer.

    Rules:
    - NO DB access
    - NO ingestion logic
    - ONLY observes analysis + graph + contracts
    """

    def __init__(self, contract=None, strict: bool = False):
        self.contract = contract
        self.strict = strict

    # --------------------------
    # PUBLIC ENTRY POINT
    # --------------------------
    def validate(
        self,
        analysis,
        graph,
        contract_report: Any,
        db_snapshot: dict,
    ) -> ValidationResult:

        errors = []
        warnings = []

        errors += self._validate_symbol_integrity(analysis)
        errors += self._validate_graph_integrity(graph)
        errors += self._validate_contracts(contract_report)
        warnings += self._validate_shape_signals(graph, db_snapshot)

        ok = len(errors) == 0

        return ValidationResult(
            ok=ok,
            errors=errors,
            warnings=warnings,
        )

    # --------------------------
    # SYMBOL VALIDATION
    # --------------------------
    def _validate_symbol_integrity(self, analysis) -> list[str]:
        errors = []

        if analysis.symbol_references is None:
            errors.append("symbol_references is None")
            return errors

        # structural sanity
        for ref in analysis.symbol_references:
            if not ref.caller or not ref.callee:
                errors.append(
                    f"Invalid symbol reference at line {ref.line_number}"
                )

        return errors

    # --------------------------
    # GRAPH VALIDATION
    # --------------------------
    def _validate_graph_integrity(self, graph) -> list[str]:
        errors = []

        if not hasattr(graph, "edges"):
            errors.append("Graph missing edges attribute")
            return errors

        if len(graph.edges) == 0:
            errors.append("Graph has zero edges (possible ingestion failure)")

        return errors

    # --------------------------
    # CONTRACT VALIDATION
    # --------------------------
    def _validate_contracts(self, report) -> list[str]:
        errors = []

        if not report:
            errors.append("Missing contract report")
            return errors

        if getattr(report, "violations", None) is None:
            errors.append("Contract report missing violations")

        # escalate errors only
        for v in getattr(report, "violations", []):
            if getattr(v, "severity", None) == "error":
                errors.append(f"{v.contract_name}: {v.message}")

        return errors

    # --------------------------
    # SHAPE SIGNALS (soft checks)
    # --------------------------
    def _validate_shape_signals(self, graph, db_snapshot) -> list[str]:
        warnings = []

        edge_count = len(getattr(graph, "edges", []))

        if edge_count < 10:
            warnings.append("Low edge count detected (possible under-analysis)")

        db_edges = db_snapshot.get("symbol_reference_count", 0)

        if db_edges != edge_count:
            warnings.append(
                f"DB/graph mismatch: db={db_edges}, graph={edge_count}"
            )

        return warnings

    def validate_stage(self, stage: str, context: dict) -> None:
        """
        Stage-level validation hook for pipeline enforcement.

        This is intentionally lightweight so we can:
        - observe behavior first
        - tighten constraints later
        """

        # 1. fetch stage rules (if any exist in contract)
        stage_rules = getattr(self.contract, "stages", {}).get(stage, {})

        # 2. if no rules defined → allow pass-through (observational mode)
        if not stage_rules:
            return

        # 3. enforce only declared invariants
        for rule in stage_rules.get("rules", []):
            rule.validate(context)