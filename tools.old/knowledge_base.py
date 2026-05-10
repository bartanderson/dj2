import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

KNOWLEDGE_DB = Path(__file__).parent.parent / "ai_context" / "knowledge.db"

def get_db():
    """Return a connection to the knowledge DB, creating tables if needed."""
    KNOWLEDGE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(KNOWLEDGE_DB))
    conn.execute("PRAGMA journal_mode=WAL")
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
    return conn

def compute_parameters_hash(tool_name: str, params: dict) -> str:
    """Return a stable hash for tool name and parameters."""
    canonical = json.dumps({"tool": tool_name, "params": params}, sort_keys=True)
    return hashlib.md5(canonical.encode()).hexdigest()

def get_fresh_result(tool_name: str, params: dict, max_age_seconds: int = 86400) -> Union[dict, list, None]:
    """
    Check if a fresh result exists for this tool call.
    Returns parsed result if found and fresh, else None.
    """
    conn = get_db()
    try:
        h = compute_parameters_hash(tool_name, params)
        cur = conn.execute(
            "SELECT result_data FROM knowledge WHERE parameters_hash = ? AND julianday('now') - julianday(timestamp) < ?",
            (h, max_age_seconds / 86400.0)
        )
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()

def store_knowledge_with_hash(
    tool_name: str,
    result: Any,
    params: dict,
    query: Optional[str] = None,
    file_path: Optional[str] = None,
    concepts: Optional[List[str]] = None,
    thread_id: Optional[str] = None,
    parent_id: Optional[int] = None
):
    """Store result with computed hash."""
    h = compute_parameters_hash(tool_name, params)
    conn = get_db()
    try:
        result_json = json.dumps(result, default=str)
        concepts_str = ','.join(concepts) if concepts else None
        conn.execute(
            """INSERT INTO knowledge 
               (tool_name, query_text, file_path, concepts, result_data, parameters_hash, thread_id, parent_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tool_name, query, file_path, concepts_str, result_json, h, thread_id, parent_id)
        )
        conn.commit()
    finally:
        conn.close()

def retrieve_knowledge(
    query: Optional[str] = None,
    thread_id: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Retrieve knowledge entries by concept keywords or thread ID."""
    conn = get_db()
    try:
        sql = "SELECT id, tool_name, query_text, file_path, concepts, result_data, timestamp, parent_id, thread_id FROM knowledge WHERE 1=1"
        params = []
        if thread_id:
            sql += " AND thread_id = ?"
            params.append(thread_id)
        if query:
            words = query.lower().split()
            conditions = []
            for word in words:
                conditions.append("(concepts LIKE ? OR query_text LIKE ?)")
                params.extend([f'%{word}%', f'%{word}%'])
            sql += " AND (" + " OR ".join(conditions) + ")"
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "tool_name": row[1],
                "query_text": row[2],
                "file_path": row[3],
                "concepts": row[4].split(',') if row[4] else [],
                "result_data": json.loads(row[5]),
                "timestamp": row[6],
                "parent_id": row[7],
                "thread_id": row[8]
            })
        return results
    finally:
        conn.close()