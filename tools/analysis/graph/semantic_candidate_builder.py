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
    
        # ----------------------------
        # 3. Project symbol match
        # ----------------------------
        for sym in env.project_symbols:
            if sym == name:
                identity.project_hits.append(sym)

                identity.fqdn = identity.fqdn or sym
                identity.module = identity.module or ".".join(sym.split(".")[:-1])

                identity.confidence = max(identity.confidence, 0.7)

                identity.provenance.append(f"project_leaf_match:{sym}")

        # ----------------------------
        # 4. Fallback (observation only)
        # ----------------------------

        if identity.fqdn is None:
            identity.confidence = 0.05
            identity.provenance.append("no_resolution_signal")

        # project detection is observational only
        if identity.fqdn in env.project_symbols or identity.leaf in env.project_symbols:
            identity.project_hits.append(identity.fqdn or identity.leaf)
            identity.confidence = max(identity.confidence, 0.85)
            identity.provenance.append("project_symbol_hint")
            
        return identity