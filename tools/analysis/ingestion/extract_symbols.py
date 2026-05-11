# tools/analysis/ingestion/extract_symbols.py

import ast

def extract_symbols(tree):
    functions = set()
    classes = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.add(node.name)

        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)

    return functions | classes