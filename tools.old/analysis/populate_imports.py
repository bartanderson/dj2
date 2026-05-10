#!/usr/bin/env python3
"""
Populate the imports table from all files in the files table.
Run standalone: python tools/analysis/populate_imports.py
Or import and call populate_imports(db_path) after a scout scan.
"""
import sqlite3
import ast
import sys
from pathlib import Path

def extract_imports_from_file(file_path):
    """Return list of (imported_module, import_type, line_number) for a file."""
    full_path = Path(file_path)
    if not full_path.exists():
        return []
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return []
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

def populate_imports(db_path):
    """Read all files from the files table and insert their imports."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT path FROM files")
    files = cur.fetchall()
    print(f"Processing {len(files)} files...")
    cur.execute("DELETE FROM imports")  # optional: clear old data
    inserted = 0
    for (file_path,) in files:
        imports = extract_imports_from_file(file_path)
        for imp_mod, imp_type, lineno in imports:
            try:
                cur.execute(
                    "INSERT INTO imports (importer_path, imported_module, import_type, line_number) VALUES (?, ?, ?, ?)",
                    (file_path, imp_mod, imp_type, lineno)
                )
                inserted += 1
            except sqlite3.IntegrityError:
                # skip duplicates (shouldn't happen with DELETE)
                pass
    conn.commit()
    conn.close()
    print(f"Inserted {inserted} import rows.")
    return inserted

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    else:
        db_path = Path("ai_context/scout.db")
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    populate_imports(db_path)