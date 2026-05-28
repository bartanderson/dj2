# tools/analysis/graph/semantic_candidate_builder.py

from typing import Dict, List, Set
from tools.analysis.representation.semantic_identity import SemanticIdentity
from tools.analysis.representation.symbol_environment import SymbolEnvironment


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
        env: SymbolEnvironment
    ) -> SemanticIdentity:

        leaf = name.split(".")[-1]

        identity = SemanticIdentity(
            surface=name,
            leaf=leaf,
        )

        # ----------------------------
        # 1. Runtime binding (strongest signal)
        # ----------------------------
        runtime_target = env.resolve_runtime(leaf)

        if runtime_target:
            fqdn = runtime_target

            identity.fqdn = fqdn
            identity.confidence = max(identity.confidence, 0.85)

            identity.runtime_hints[leaf] = fqdn
            identity.provenance.append(f"runtime_binding:{leaf}->{fqdn}")
            identity.resolved_by = "runtime"

        # ----------------------------
        # 2. Alias resolution
        # ----------------------------
        # alias resolution (parallel signal to runtime)
        alias_target = env.resolve_alias(leaf)

        if alias_target:
            fqdn = alias_target

            # only set if runtime did not already define fqdn
            identity.fqdn = identity.fqdn or fqdn
            identity.module = fqdn.split(".")[0] if "." in fqdn else None

            identity.confidence = max(identity.confidence, 0.9)

            identity.alias_hints[leaf] = fqdn
            identity.provenance.append(f"alias_map:{leaf}->{fqdn}")

            if identity.resolved_by is None:
                identity.resolved_by = "alias"

        # ----------------------------
        # 3. Fallback (observation only)
        # ----------------------------

        if identity.fqdn is None:
            identity.confidence = 0.05
            identity.provenance.append("no_resolution_signal")

        # ----------------------------
        # 4. Project symbol match (corrected)
        # ----------------------------

        for sym in env.project_symbols:
            # match against full canonical name OR resolved fqdn
            if sym == identity.surface or sym == identity.fqdn:
                identity.project_hits.append(sym)

                # ensure fqdn is always populated for project symbols
                identity.fqdn = identity.fqdn or sym

                identity.confidence = max(identity.confidence, 0.85)
                identity.provenance.append(f"project_match:{sym}")
                break

        return identity