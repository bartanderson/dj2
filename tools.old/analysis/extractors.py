import ast
from typing import List, Tuple

def _module_name_from_path(file_path: str) -> str:
    """
    Convert a relative file path (e.g., 'world/character_builder.py') to a dotted module name.
    """
    # Normalize path separators
    file_path = file_path.replace('\\', '/')
    # Remove .py extension
    if file_path.endswith('.py'):
        file_path = file_path[:-3]
    # Replace slashes with dots
    return file_path.replace('/', '.')

def extract_imports_from_ast(tree: ast.AST, file_path: str) -> List[Tuple[str, str, int]]:
    """
    Extract full module paths for imports.
    Returns list of (full_module, import_type, line_number).
    """
    imports = []
    # Determine the package of the source file for relative imports
    source_module = _module_name_from_path(file_path)
    source_parts = source_module.split('.')
    source_package = '.'.join(source_parts[:-1]) if len(source_parts) > 1 else ''

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                full_module = alias.name
                imports.append((full_module, 'import', node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                # Relative import without module name: from . import x
                level = node.level
                # Compute the base package after going up 'level' levels
                if level <= len(source_parts):
                    base_parts = source_parts[:-level]
                    base = '.'.join(base_parts)
                else:
                    base = ''
                # For each alias, we need the module? Actually the module is the current package.
                # But to resolve the file, we need the package path. We'll store the base as the module.
                # If there are aliases, the actual file is the __init__.py of that package.
                for alias in node.names:
                    # The full module for the file that defines the imported object is the package itself
                    # (e.g., for `from . import tool`, the file is `__init__.py` in the package)
                    imports.append((base, 'from', node.lineno))
            else:
                # Absolute or relative import with module name
                module = node.module
                level = node.level
                if level == 0:
                    # Absolute import
                    full_module = module
                else:
                    # Relative import: from .submodule import x
                    # Go up 'level' levels from source_package, then append module
                    if level <= len(source_parts):
                        base_parts = source_parts[:-level]
                        base = '.'.join(base_parts)
                    else:
                        base = ''
                    if base:
                        full_module = f"{base}.{module}"
                    else:
                        full_module = module
                imports.append((full_module, 'from', node.lineno))
    return imports

# Keep the other extraction functions unchanged
def extract_dict_key_accesses(node):
    accesses = []
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Subscript):
            if (isinstance(subnode.slice, ast.Constant) and 
                isinstance(subnode.slice.value, str) and
                isinstance(subnode.value, ast.Name)):
                accesses.append((subnode.value.id, subnode.slice.value))
    return accesses

def extract_method_params(func_node):
    params = []
    for i, arg in enumerate(func_node.args.args):
        if arg.arg not in ('self', 'cls'):
            params.append((arg.arg, i))
    return params

def extract_constructor_params(class_node):
    for node in ast.walk(class_node):
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            return extract_method_params(node)
    return []