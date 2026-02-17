"""Extraction functions for scout data."""
import ast
from typing import List, Tuple

def extract_imports_from_ast(tree: ast.AST, file_path: str) -> List[Tuple[str, str, int]]:
    """Extract import information from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name.split('.')[0], 'import', node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_base = node.module.split('.')[0]
                imports.append((module_base, 'from', node.lineno))
    return imports

def extract_dict_key_accesses(node):
    """Extract dictionary key accesses from a function node."""
    accesses = []
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Subscript):
            if (isinstance(subnode.slice, ast.Constant) and 
                isinstance(subnode.slice.value, str) and
                isinstance(subnode.value, ast.Name)):
                accesses.append((subnode.value.id, subnode.slice.value))
    return accesses

def extract_method_params(func_node):
    """Extract parameters from a FunctionDef node."""
    params = []
    for i, arg in enumerate(func_node.args.args):
        if arg.arg not in ('self', 'cls'):
            params.append((arg.arg, i))
    return params

def extract_constructor_params(class_node):
    """Find __init__ in a class and extract its parameters."""
    for node in ast.walk(class_node):
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            return extract_method_params(node)
    return []