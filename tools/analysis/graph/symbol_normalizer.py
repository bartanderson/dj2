# tools/analysis/graph/symbol_normalizer.py

from __future__ import annotations

import re


def normalize_symbol(name: str) -> str:
    if not name:
        return name

    # -------------------------------------------------
    # Collapse repeated module repetition (SAFE)
    # world.world_controller.WorldController.create_party
    # → world.world_controller.create_party
    # -------------------------------------------------
    parts = name.split(".")

    if len(parts) >= 3:
        # remove repeated class name if pattern matches
        if parts[-2].lower() == parts[-3].lower():
            parts.pop(-2)

    return ".".join(parts)