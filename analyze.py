import os
import ast
import json
import argparse
from typing import List, Dict, Any, Optional

def extract_function_info(node: ast.FunctionDef) -> Dict[str, Any]:
    """Extract function/method details from AST node"""
    return {
        'name': node.name,
        'args': [arg.arg for arg in node.args.args],
        'decorators': [ast.unparse(d) for d in node.decorator_list],
        'lineno': node.lineno
    }

def extract_class_info(node: ast.ClassDef) -> Dict[str, Any]:
    """Extract class details from AST node including methods"""
    class_info = {
        'name': node.name,
        'bases': [ast.unparse(b) for b in node.bases],
        'decorators': [ast.unparse(d) for d in node.decorator_list],
        'methods': [],
        'lineno': node.lineno
    }
    
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            class_info['methods'].append(extract_function_info(item))
            
    return class_info

def extract_import_info(node) -> Dict[str, Any]:
    """Extract import statement details"""
    if isinstance(node, ast.Import):
        return {
            'type': 'import',
            'names': [alias.name for alias in node.names]
        }
    elif isinstance(node, ast.ImportFrom):
        return {
            'type': 'from',
            'module': node.module,
            'names': [alias.name for alias in node.names],
            'level': node.level
        }

def parse_python_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Parse a Python file and extract its structure"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error parsing {filepath}: {e}")
        return None

    file_info = {
        'path': filepath,
        'imports': [],
        'classes': [],
        'functions': []
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            file_info['imports'].append(extract_import_info(node))
        elif isinstance(node, ast.ClassDef):
            file_info['classes'].append(extract_class_info(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            file_info['functions'].append(extract_function_info(node))
            
    return file_info

def scan_project(base_path: str, ignore_dirs: List[str]) -> List[Dict[str, Any]]:
    """Scan a project directory and parse all Python files"""
    project_data = []
    
    for root, dirs, files in os.walk(base_path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                file_data = parse_python_file(full_path)
                if file_data:
                    project_data.append(file_data)
                    
    return project_data

def main():
    parser = argparse.ArgumentParser(description='Extract project structure from Python files')
    parser.add_argument('base_dir', help='Base directory to scan')
    parser.add_argument('-i', '--ignore', nargs='+', default=['__pycache__', 'venv', '.git'],
                        help='Directories to ignore')
    parser.add_argument('-o', '--output', default='project_ast.json',
                        help='Output JSON file name')
    
    args = parser.parse_args()
    
    print(f"Scanning project in: {args.base_dir}")
    print(f"Ignoring directories: {', '.join(args.ignore)}")
    
    project_data = scan_project(args.base_dir, args.ignore)
    
    with open(args.output, 'w') as f:
        json.dump(project_data, f, indent=2)
        
    print(f"Project structure saved to {args.output}")
    print(f"Processed {len(project_data)} Python files")

if __name__ == '__main__':
    main()