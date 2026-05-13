# tools/analysis/graph/symbol_identity.py

def canonical_symbol(name: str) -> str:
    if not name:
        return name
    return name.strip().lstrip(".")