# tools/analysis/contracts/contract_drift_classifier.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
from collections import defaultdict


@dataclass
class ContractDriftSignal:
    contract_name: str
    severity: str
    layer: str
    classification: str  # transient | recurring | structural | obsolete
    count: int


class ContractDriftClassifier:
    """
    Converts raw contract violations into lifecycle signals.

    This is PURE ANALYSIS:
    - no mutation
    - no enforcement
    - no DB writes
    """

    def __init__(self):
        pass

    def classify(
        self,
        reports: List[Any],
    ) -> List[ContractDriftSignal]:

        counter = defaultdict(int)
        meta = {}

        # -----------------------------------------
        # FLATTEN ALL VIOLATIONS
        # -----------------------------------------
        for report in reports:
            for v in getattr(report, "violations", []):
                key = v.contract_name
                counter[key] += 1
                meta[key] = {
                    "severity": getattr(v, "severity", "unknown"),
                    "layer": getattr(v, "layer", "unknown"),
                }

        signals: List[ContractDriftSignal] = []

        # -----------------------------------------
        # CLASSIFICATION RULES (simple, deterministic)
        # -----------------------------------------
        for contract, count in counter.items():

            if count == 1:
                classification = "transient"

            elif 2 <= count <= 3:
                classification = "recurring"

            elif count > 3:
                classification = "structural"

            else:
                classification = "obsolete"

            signals.append(
                ContractDriftSignal(
                    contract_name=contract,
                    severity=meta[contract]["severity"],
                    layer=meta[contract]["layer"],
                    classification=classification,
                    count=count,
                )
            )

        return signals