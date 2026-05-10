import sqlite3

conn = sqlite3.connect("tools/analysis/data/analysis.db")
cursor = conn.cursor()

cursor.execute("SELECT file_path FROM files LIMIT 20")
rows = cursor.fetchall()

print("\nFILE PATHS IN DB:\n")
for r in rows:
    print(r[0])