# tools/analysis/representation/semantic_identity.py

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class SemanticIdentity:
    surface: str
    leaf: str

    fqdn: Optional[str] = None
    module: Optional[str] = None

    confidence: float = 0.0
    provenance: List[str] = field(default_factory=list)

    runtime_hints: Dict[str, str] = field(default_factory=dict)
    alias_hints: Dict[str, str] = field(default_factory=dict)
    project_hits: List[str] = field(default_factory=list)