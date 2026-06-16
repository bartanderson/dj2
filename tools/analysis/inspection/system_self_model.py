# tools/analysis/inspection/meta/system_self_model.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SystemSelfModel:
    capabilities: list
    limitations: list
    structural_biases: list
    failure_modes: list
    inference_gaps: list
    notes: list


class SystemSelfModelBuilder:
    def __init__(self, oracle):
        self.oracle = oracle

    def build(self) -> SystemSelfModel:
        graph = self.oracle.get_snapshot_graph()

        shape = self.oracle.system_shape() if hasattr(self.oracle, "system_shape") else None
        edges = graph.edges

        limitations = []
        failure_modes = []
        inference_gaps = []
        capabilities = []
        biases = []
        notes = []

        # -------------------------
        # Structural reality checks
        # -------------------------

        if len(edges) == 0:
            failure_modes.append("graph_empty_state")

        if len(edges) < 10:
            limitations.append("low_observability_graph")

        # -------------------------
        # Routing structure signals
        # -------------------------

        if hasattr(self.oracle, "router"):
            biases.append("router_is_primary_decision_layer")

        # -------------------------
        # DB vs inferred mismatch
        # -------------------------

        if shape:
            if "external_dependency_heavy" in shape.get("system_shape_tags", []):
                limitations.append("external_dependency_dominance")

            if "high_coupling_core" in shape.get("system_shape_tags", []):
                failure_modes.append("high_coupling_core_risk")

        # -------------------------
        # Oracle behavior assumptions
        # -------------------------

        capabilities.append("symbol_graph_traversal")
        capabilities.append("query_expansion_via_router")
        capabilities.append("contract_violation_detection")

        # -------------------------
        # Known inference gap class
        # -------------------------

        inference_gaps.append(
            "semantic_identity_is_heuristic_not_ground_truth"
        )

        inference_gaps.append(
            "edge_bucket_assignment_is_best_effort_classification"
        )

        notes.append(
            "system_self_model_is_derivative_not_authoritative"
        )

        return SystemSelfModel(
            capabilities=capabilities,
            limitations=limitations,
            structural_biases=biases,
            failure_modes=failure_modes,
            inference_gaps=inference_gaps,
            notes=notes,
        )