import sqlite3
from pathlib import Path

db = Path("ai_context/scout.db")
file_path = "world\\character_builder.py"

conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute("SELECT full_module, import_type, line_number FROM imports WHERE importer_path = ?", (file_path,))
rows = cur.fetchall()
conn.close()

print("Imports for", file_path)
for row in rows:
    print(row)