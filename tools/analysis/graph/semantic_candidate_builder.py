# tools/analysis/graph/semantic_candidate_builder.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ResolvedCandidate:
    surface: str
    fqdn: Optional[str]
    module: Optional[str]
    confidence: float
    source: str
    evidence: List[str] = field(default_factory=list)


class SemanticCandidateBuilder:
    """
    Phase 1 semantic reconstruction layer.

    PURELY OBSERVATIONAL:
    - does not affect routing
    - does not modify graph
    - does not replace identity
    """

    def __init__(self):
        self.candidates: list[ResolvedCandidate] = []

    def from_trace(
        self,
        name: str,
        alias_map: Dict[str, str],
        runtime_bindings: Dict[str, str],
        project_symbols: set[str],
    ) -> list[ResolvedCandidate]:

        leaf = name.split(".")[-1]

        evidence = []

        # 1. runtime binding hint
        if leaf in runtime_bindings:
            fqdn = runtime_bindings[leaf]
            evidence.append(f"runtime_binding:{leaf}->{fqdn}")

            self.candidates.append(
                ResolvedCandidate(
                    surface=leaf,
                    fqdn=fqdn,
                    module=None,
                    confidence=0.8,
                    source="runtime_binding",
                    evidence=evidence,
                )
            )

        # 2. alias map hint
        if leaf in alias_map:
            fqdn = alias_map[leaf]
            evidence.append(f"alias_map:{leaf}->{fqdn}")

            self.candidates.append(
                ResolvedCandidate(
                    surface=leaf,
                    fqdn=fqdn,
                    module=fqdn.split(".")[0] if "." in fqdn else None,
                    confidence=0.9,
                    source="import_alias",
                    evidence=evidence,
                )
            )

        # 3. project symbol hint (leaf-level match)
        for sym in project_symbols:
            if sym.split(".")[-1] == leaf:
                evidence.append(f"project_leaf_match:{sym}")

                self.candidates.append(
                    ResolvedCandidate(
                        surface=leaf,
                        fqdn=sym,
                        module=".".join(sym.split(".")[:-1]),
                        confidence=0.7,
                        source="project_leaf",
                        evidence=evidence,
                    )
                )

        # 4. fallback unresolved semantic stub
        if not self.candidates:
            self.candidates.append(
                ResolvedCandidate(
                    surface=leaf,
                    fqdn=None,
                    module=None,
                    confidence=0.0,
                    source="unresolved",
                    evidence=["no_resolution_signal"],
                )
            )

        return self.candidates