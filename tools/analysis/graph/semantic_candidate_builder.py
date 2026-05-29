# tools\analysis\graph\semantic_candidate_builder.py

from tools.analysis.representation.semantic_identity import SemanticIdentity
from tools.analysis.representation.symbol_environment import SymbolEnvironment
from tools.analysis.graph.runtime_resolution import resolve_runtime_symbol


class SemanticIdentityBuilder:
    """
    IR1 construction layer.

    PURPOSE:
    - unify signals from routing stage
    - produce coherent semantic identity
    - DO NOT re-classify routing
    """

    def build(
        self,
        name: str,
        env: SymbolEnvironment,
        route_type: str,   # REQUIRED: authoritative CP3 output
    ) -> SemanticIdentity:

        leaf = name.split(".")[-1]

        identity = SemanticIdentity(
            surface=name,
            leaf=leaf,
            resolved_by=route_type,   # single source of truth
            confidence=1.0,           # fixed baseline (no inference here)
        )

        # -------------------------------------------------
        # 1. Runtime enrichment (signals only, no scoring)
        # -------------------------------------------------
        if route_type == "runtime":
            runtime_target = resolve_runtime_symbol(name, env.runtime_bindings)

            if runtime_target:
                identity.fqdn = runtime_target
                identity.runtime_hints[leaf] = runtime_target
                identity.provenance.append(
                    f"runtime:{leaf}->{runtime_target}"
                )

        # -------------------------------------------------
        # 2. Project enrichment (signals only, no scoring)
        # -------------------------------------------------
        elif route_type == "project":
            if name in env.project_symbols:
                identity.fqdn = name
                identity.project_hits.append(name)
                identity.provenance.append(f"project:{name}")

        # -------------------------------------------------
        # 3. External / unknown (pure labeling only)
        # -------------------------------------------------
        elif route_type in ("external", "unknown"):
            identity.provenance.append(f"unresolved:{route_type}")

        return identity