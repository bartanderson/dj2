# tools/analysis/graph/symbol_identity.py

def project_key(name: str) -> str:
    if not name:
        return name
    return name.split(".")[-1]


def module_key(name: str) -> str:
    if not name:
        return ""
    return ".".join(name.split(".")[:-1]) if "." in name else ""