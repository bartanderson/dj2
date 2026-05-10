#!/usr/bin/env python3
"""
Clean and repopulate dependent tables after a scout scan.
Run this after arch_recon.py --scout to fix duplicates and ensure data consistency.
"""
import numpy as np
import sqlite3
import ast
import sys
from pathlib import Path

# Add paths to import our modules
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from extractors import (
    extract_imports_from_ast,
    extract_dict_key_accesses,
    extract_method_params,
    extract_constructor_params,
)
from db_operations import (
    clear_all_dependent_tables,
    insert_import,
    insert_dict_key,
    insert_method_param,
    insert_class_constructor,
    insert_behavioral_contract,
    insert_embedding,
)
from embedding_model import embed_text

def process_file(conn, file_path, project_root):
    """Extract all data from a file and insert into DB."""
    full_path = project_root / file_path
    if not full_path.exists():
        print(f"  File not found: {file_path}, skipping.")
        return

    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception as e:
        print(f"  Error parsing {file_path}: {e}")
        return

    # Insert imports
    imports = extract_imports_from_ast(tree, file_path)
    for imp_mod, imp_type, lineno in imports:
        insert_import(conn, file_path, imp_mod, imp_type, lineno)

    # Insert dict key accesses and method parameters (we need to walk functions)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Determine if it's a method (enclosed in class)
            in_class = False
            for parent in ast.walk(tree):
                if parent != node and isinstance(parent, ast.ClassDef):
                    for child in ast.walk(parent):
                        if child is node:
                            in_class = True
                            break
                    if in_class:
                        break
            # Dict keys
            for dict_var, key in extract_dict_key_accesses(node):
                insert_dict_key(conn, file_path, node.name, dict_var, key)
            # Parameters (top-level only)
            if not in_class:
                for param_name, pos in extract_method_params(node):
                    insert_method_param(conn, file_path, None, node.name, param_name, pos)

    # Classes: constructor params and method params
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            # Constructor
            for param_name, pos in extract_constructor_params(node):
                insert_class_constructor(conn, file_path, class_name, param_name, pos)
            # Methods
            for method_node in node.body:
                if isinstance(method_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_name = method_node.name
                    for param_name, pos in extract_method_params(method_node):
                        insert_method_param(conn, file_path, class_name, method_name, param_name, pos)

    # Generate embedding
    summary_parts = []
    module_doc = ast.get_docstring(tree)
    if module_doc:
        summary_parts.append(module_doc)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node)
            if doc:
                summary_parts.append(doc)
    identifiers = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifiers.append(node.id)
    if identifiers:
        summary_parts.append(" ".join(identifiers))
    summary = "\n".join(summary_parts)
    if summary.strip():
        emb = embed_text(summary)
        emb_bytes = emb.astype(np.float32).tobytes()
        insert_embedding(conn, file_path, emb_bytes)

    # Note: behavioral contracts are not handled here because they are already in the files table data.
    # If you want to repopulate them, you'd need to extract them as well, but they are not in separate tables.
    # The current behavioral_contracts table is populated by arch_recon.py during the second loop.
    # To keep it simple, we'll skip behavioral contracts here; they are already correct from the scout scan.

def main():
    db_path = Path("ai_context/scout.db")
    if not db_path.exists():
        print("❌ Scout DB not found. Run arch_recon.py --scout first.")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Get list of all files
    cur.execute("SELECT path FROM files")
    files = cur.fetchall()
    print(f"Found {len(files)} files in database.")

    # Clear dependent tables
    clear_all_dependent_tables(conn)
    print("Cleared dependent tables.")

    # Process each file
    for (file_path,) in files:
        print(f"Processing {file_path}...")
        process_file(conn, file_path, Path("."))

    conn.commit()
    conn.close()
    print("✅ Done. Dependent tables repopulated.")

if __name__ == "__main__":
    main()