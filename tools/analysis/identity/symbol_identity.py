# tools/analysis/identity/symbol_identity.py

def normalize_symbol(name: str) -> str:
    if not name:
        return name
    return name.strip()

def resolve_symbol_identity(name: str, alias_map: dict[str, str]) -> str:
    # keep minimal behavior for now
    return alias_map.get(name, name)

def project_key(name: str):
    return "default"