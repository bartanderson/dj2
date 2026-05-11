from tools.analysis.persistence.persist_file_analysis import create_database

db = create_database("tools/analysis/data/analysis.db")
cursor = db.cursor()

cursor.execute("""
SELECT caller, callee
FROM symbol_references
LIMIT 30
""")

for row in cursor.fetchall():
    print(row)