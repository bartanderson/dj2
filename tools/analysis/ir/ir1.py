# tools/analysis/ir/ir1.py

from dataclasses import dataclass
from typing import Optional, Literal, List


@dataclass(frozen=True)
class IR1Symbol:
    """
    Identity-first representation of any symbol in the system.
    This replaces string-only routing assumptions.
    """

    # THIS LAYER IS ADVISORY ONLY.
    # It represents reconstructed identity signals and must not be used for routing decisions.

    surface: str                  # raw AST surface ("field", "request.args")
    normalized: str              # canonicalized leaf or dotted form
    fqdn: Optional[str]           # fully resolved identity if known
    module: Optional[str]         # module anchor if known

    kind: Literal[
        "local",
        "imported",
        "attribute",
        "runtime",
        "builtin",
        "unknown"
    ]

    provenance: List[str]        # trace path (CP0–CP3.5 + resolver hints)

    confidence: float