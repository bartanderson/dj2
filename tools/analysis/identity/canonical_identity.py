# tools/analysis/identity/canonical_identity.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


from tools.analysis.graph.symbol_resolution import resolve_symbol_identity
from tools.analysis.graph.symbol_identity import normalize_symbol

# =========================================================
# FILE IDENTITY (single source of truth)
# =========================================================

def file_identity(path: str | Path) -> str:
    """
    Canonical file identity across all systems.
    """
    return normalize_file_identity(path)


# =========================================================
# SYMBOL IDENTITY (canonical semantic layer)
# =========================================================

def symbol_identity_from_string(
    name: str,
    alias_map: Optional[dict[str, str]] = None,
) -> str:
    """
    Canonical symbol identity from raw AST/string input.
    """
    if alias_map is None:
        alias_map = {}

    return resolve_symbol_identity(name, alias_map)


def symbol_identity_normalized(name: str) -> str:
    """
    Pure normalization layer (no resolution context).
    """
    return normalize_symbol(name)


# =========================================================
# IR / enriched identity (future graph-friendly layer)
# =========================================================

def symbol_identity_ir(ir: Any) -> str:
    """
    Preferred identity when IR layer is available.
    """
    # IR already carries canonicalization intent
    return getattr(ir, "normalized", None) or getattr(ir, "fqdn", None)


# =========================================================
# GRAPH EDGE IDENTITY (bridge layer)
# =========================================================

def edge_identity(source: Any, target: Any) -> tuple[str, str]:
    """
    Produces canonical graph edge identity pair.
    Accepts IR objects OR raw strings.
    """

    def resolve(x: Any) -> str:
        if hasattr(x, "normalized") or hasattr(x, "fqdn"):
            return symbol_identity_ir(x)
        if isinstance(x, str):
            return symbol_identity_normalized(x)
        return str(x)

    return resolve(source), resolve(target)


# =========================================================
# LEGACY COMPATIBILITY (DO NOT USE FOR GRAPH SEMANTICS)
# =========================================================

def legacy_canonical_id(file_path, symbol_type, name, line_number):
    """
    Existing storage identity (kept for backward compatibility only).
    """
    return f"{file_path}:{symbol_type}:{name}:{line_number}"