import sqlite3
from pathlib import Path

db_path = Path("ai_context") / "knowledge.db"
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect(str(db_path))
conn.execute("""
    CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        tool_name TEXT NOT NULL,
        query_text TEXT,
        file_path TEXT,
        concepts TEXT,
        result_data TEXT NOT NULL,
        parameters_hash TEXT,
        git_commit TEXT,
        embedding BLOB,
        parent_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_parameters_hash ON knowledge(parameters_hash)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_concepts ON knowledge(concepts)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_thread ON knowledge(thread_id)")
conn.commit()
conn.close()
print("Knowledge database created.")