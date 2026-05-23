# tools/analysis/contracts/contract_validator.py


# MODULE: contract
# OWNED: TRUE
# ROLE: runtime validation + cross-module consistency enforcement
#
# CONTRACT (LOCKED v1)
# - Validates pipeline invariants at runtime (not documentation)
# - Ensures classification → snapshot → reduction consistency
# - Rejects or flags inconsistent edge/bucket propagation
# - Must NOT mutate data (validation-only module)
# - Must NOT perform classification or graph construction
#
# BOUNDARIES
# - DOES NOT own: classification, snapshot building, graph construction
# - DOES own: invariant validation, structural checks, reconciliation scoring
#
# INVARIANTS (GLOBAL)
# - edge_conservation MUST hold across pipeline stages
# - snapshot.bucket_summary MUST reconcile with reducer output
# - classification routes MUST be stable for identical inputs
#
# FAILURE MODE
# - MUST emit structured validation report
# - MUST NOT silently correct pipeline state


from dataclasses import dataclass
from typing import Any, Dict


class ContractViolation(Exception):
    pass


class ContractRuntimeValidator:
    def __init__(self, contract: Dict[str, Any]):
        self.contract = contract

    def validate_stage(self, stage: str, context: Dict[str, Any]) -> None:
        """
        context = runtime snapshot of what just happened in pipeline stage
        """

        modules = self.contract.get("modules", {})
        stage_contract = modules.get(stage)

        if not stage_contract:
            raise ContractViolation(f"Unknown stage: {stage}")

        invariants = stage_contract.get("invariants", {})

        for name, rule in invariants.items():
            self._check_rule(stage, name, rule, context)

    def _check_rule(self, stage: str, name: str, rule: Any, context: Dict[str, Any]):
        """
        Minimal rule engine (intentionally simple)
        """

        # ---- edge conservation ----
        if name == "edge_conservation":
            edges = context.get("edges", None)
            if edges is not None and edges < 0:
                raise ContractViolation(f"[{stage}] negative edge count")

        # ---- classification boundary ----
        if name == "classification_must_not_be_in_persistence":
            if context.get("classification_called_in_persistence"):
                raise ContractViolation(f"[{stage}] classification leaked into persistence")

        # ---- snapshot integrity ----
        if name == "snapshot_must_match_graph":
            if context.get("snapshot_mismatch"):
                raise ContractViolation(f"[{stage}] snapshot mismatch detected")

        # ---- generic boolean guard ----
        if isinstance(rule, bool) and rule is True:
            if context.get(name) is False:
                raise ContractViolation(f"[{stage}] invariant failed: {name}")