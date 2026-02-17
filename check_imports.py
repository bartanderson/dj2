#!/usr/bin/env python3
"""
Check the imports table in the scout DB for a specific file.
"""
import sqlite3
import sys
from pathlib import Path

db_path = Path("ai_context/scout.db")
if not db_path.exists():
    print("❌ Scout DB not found.")
    sys.exit(1)

file_path = "world\\character_builder.py"  # adjust backslashes as needed

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# Check if the file exists in the files table
cur.execute("SELECT path FROM files WHERE path = ?", (file_path,))
file_row = cur.fetchone()
if file_row:
    print(f"✅ File found in files table: {file_row[0]}")
else:
    print(f"❌ File not found in files table: {file_path}")

# Query imports for this file
cur.execute("SELECT * FROM imports WHERE importer_path = ?", (file_path,))
rows = cur.fetchall()
print(f"\nImports found for {file_path}: {len(rows)}")
if rows:
    # Print column names (assuming we know them)
    print("\nColumns: importer_path, imported_module, import_type, line_number")
    for row in rows:
        print(row)
else:
    print("No imports found.")

# Optional: Show a sample of other imports to see if any data exists
cur.execute("SELECT COUNT(*) FROM imports")
total_imports = cur.fetchone()[0]
print(f"\nTotal imports in DB: {total_imports}")

if total_imports > 0:
    cur.execute("SELECT * FROM imports LIMIT 5")
    sample = cur.fetchall()
    print("\nSample imports (first 5):")
    for row in sample:
        print(row)

conn.close()