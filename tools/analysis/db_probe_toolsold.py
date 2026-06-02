# tools/analysis/db_probe_toolsold.py

import sqlite3
import sys

DB = sys.argv[1]

conn = sqlite3.connect(DB)
cur = conn.cursor()

def q(label, sql):
    print(f"\n[{label}]")
    rows = cur.execute(sql).fetchall()
    for r in rows[:20]:
        print(r)
    print(f"rows: {len(rows)}")

# ----------------------------------------
# 1. Did ingestion actually persist files?
# ----------------------------------------
q("FILES", """
SELECT file_path, line_count, is_hot
FROM files
LIMIT 20;
""")

# ----------------------------------------
# 2. Are ANY old system files present?
# ----------------------------------------
q("TOOLS.OLD FILTER", """
SELECT file_path
FROM files
WHERE file_path LIKE '%tools.old%'
LIMIT 50;
""")

# ----------------------------------------
# 3. Symbol reference explosion check
# ----------------------------------------
q("SYMBOL REFS SAMPLE", """
SELECT caller, callee, bucket, edge_role
FROM symbol_references
LIMIT 50;
""")

# ----------------------------------------
# 4. Bucket distribution sanity check
# ----------------------------------------
q("BUCKET DISTRIBUTION", """
SELECT bucket, COUNT(*)
FROM symbol_references
GROUP BY bucket;
""")

# ----------------------------------------
# 5. Edge existence check (critical)
# ----------------------------------------
q("FILE EDGES", """
SELECT from_file, to_module
FROM file_edges
LIMIT 50;
""")

# ----------------------------------------
# 6. Are we losing classification entirely?
# ----------------------------------------
q("NULL / MISSING BUCKETS", """
SELECT COUNT(*)
FROM symbol_references
WHERE bucket IS NULL OR bucket = '';
""")

# ----------------------------------------
# 7. CLASSIFIER HIT RATE
# ----------------------------------------
q("CLASSIFICATION COVERAGE", """
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN bucket IS NOT NULL AND bucket != '' THEN 1 ELSE 0 END) as classified
FROM symbol_references;
""")

conn.close()