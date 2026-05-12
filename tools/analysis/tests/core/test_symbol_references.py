from tools.analysis.persistence.persist_file_analysis import create_database
from tools.analysis.pipeline.pipeline_guard import validate_symbol_trace

db = create_database("tools/analysis/data/analysis.db")
cursor = db.cursor()

cursor.execute("""
SELECT caller, callee
FROM symbol_references
LIMIT 30
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

# 🔒 THIS IS THE ACTUAL ENFORCEMENT STEP
validate_symbol_trace(rows)