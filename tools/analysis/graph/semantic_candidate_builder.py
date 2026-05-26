# tools/analysis/graph/semantic_candidate_builder.py

from typing import Dict, List, Set
from tools.analysis.representation.semantic_identity import SemanticIdentity


class SemanticIdentityBuilder:
    """
    IR1 construction layer.

    PURPOSE:
    - unify runtime + alias + project signals
    - produce single coherent identity object per symbol

    NOT RESPONSIBLE FOR:
    - routing
    - classification
    - metrics
    """

    def build(
        self,
        name: str,
        alias_map: Dict[str, str],
        runtime_bindings: Dict[str, str],
        project_symbols: Set[str],
    ) -> SemanticIdentity:

        leaf = name.split(".")[-1]

        identity = SemanticIdentity(
            surface=name,
            leaf=leaf,
        )

        # ----------------------------
        # 1. Runtime binding (strongest signal)
        # ----------------------------
        if leaf in runtime_bindings:
            fqdn = runtime_bindings[leaf]

            identity.fqdn = fqdn
            identity.identity_type = "runtime"
            identity.confidence = max(identity.confidence, 0.85)

            identity.runtime_hints[leaf] = fqdn
            identity.provenance.append(f"runtime_binding:{leaf}->{fqdn}")

        # ----------------------------
        # 2. Alias resolution
        # ----------------------------
        if leaf in alias_map:
            fqdn = alias_map[leaf]

            identity.fqdn = identity.fqdn or fqdn
            identity.module = fqdn.split(".")[0] if "." in fqdn else None

            identity.identity_type = identity.identity_type if identity.identity_type != "unknown" else "alias"
            identity.confidence = max(identity.confidence, 0.9)

            identity.alias_hints[leaf] = fqdn
            identity.provenance.append(f"alias_map:{leaf}->{fqdn}")

        # ----------------------------
        # 3. Project symbol match
        # ----------------------------
        for sym in project_symbols:
            if sym == name or sym.endswith("." + leaf):
                identity.project_hits.append(sym)

                identity.fqdn = identity.fqdn or sym
                identity.module = identity.module or ".".join(sym.split(".")[:-1])

                identity.identity_type = identity.identity_type if identity.identity_type != "unknown" else "project"
                identity.confidence = max(identity.confidence, 0.7)

                identity.provenance.append(f"project_leaf_match:{sym}")

        # ----------------------------
        # 4. Fallback
        # ----------------------------
        if identity.identity_type == "unknown":
            identity.confidence = 0.05
            identity.provenance.append("no_resolution_signal")

        if identity.fqdn in project_symbols or identity.leaf in project_symbols:
            identity.identity_type = identity.identity_type if identity.identity_type != "unknown" else "project"
            identity.confidence = max(identity.confidence, 0.85)
            identity.provenance.append("project_symbol_hint")

        return identity