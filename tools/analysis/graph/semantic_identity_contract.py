# tools/analysis/graph/semantic_identity_contract.py

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class SemanticIdentityContract:
    surface: str

    # CP1 / CP2 signals
    normalized: str
    leaf: str
    root: str
    depth: int

    # CP3 outcome (authoritative routing decision)
    routing_result: str  # project | runtime | builtin | stdlib | external | unknown

    # Shadow layer enrichment (non-authoritative)
    candidates: list[dict] = field(default_factory=list)

    # CP2.5 observation snapshot (frozen)
    observation: dict | None = None

    # reconstruction metadata (future migration layer)
    confidence: float = 1.0
    ambiguity_score: float = 0.0

    # provenance
    cp_version: str = "CP3+shadow_v1"