#!/usr/bin/env python3
"""
Test inserting imports for character_builder.py into the DB.
"""
import sqlite3
import ast
import sys
from pathlib import Path

db_path = Path("ai_context/scout.db")
target = Path("world/character_builder.py")
if not target.exists():
    print("❌ File not found")
    sys.exit(1)

# Connect to DB
conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# Read and parse file
with open(target, 'r', encoding='utf-8') as f:
    source = f.read()
tree = ast.parse(source)

# Use the same extraction function as before (local version)
def extract_imports_from_ast(tree, file_path):
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

imports = extract_imports_from_ast(tree, str(target))

# Insert into imports table
inserted = 0
for imp_mod, imp_type, lineno in imports:
    try:
        cur.execute(
            "INSERT INTO imports (importer_path, imported_module, import_type, line_number) VALUES (?, ?, ?, ?)",
            (str(target), imp_mod, imp_type, lineno)
        )
        inserted += 1
    except Exception as e:
        print(f"Error inserting {imp_mod}: {e}")

conn.commit()
conn.close()
print(f"Inserted {inserted} imports for {target}")