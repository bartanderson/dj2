from tools.analysis.persistence.persist_file_analysis import create_database

db = create_database("tools/analysis/data/analysis.db")
cursor = db.cursor()

cursor.execute("""
SELECT symbol_type, name, file_path
FROM symbols
LIMIT 20
""")

for row in cursor.fetchall():
    print(row)