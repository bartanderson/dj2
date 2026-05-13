# tools/analysis/ingestion/extract_symbols.py

import ast

def extract_symbols(tree, module_prefix: str = ""):
    functions = set()
    classes = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.add(f"{module_prefix}.{node.name}" if module_prefix else node.name)

        elif isinstance(node, ast.ClassDef):
            classes.add(f"{module_prefix}.{node.name}" if module_prefix else node.name)

    return functions | classes