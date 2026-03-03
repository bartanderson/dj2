import hashlib
import json

def compute_parameters_hash(tool_name: str, params: dict) -> str:
    """Return a stable hash for tool name and parameters."""
    # Sort keys to ensure consistent serialization
    canonical = json.dumps({"tool": tool_name, "params": params}, sort_keys=True)
    return hashlib.md5(canonical.encode()).hexdigest()

def get_fresh_result(tool_name: str, params: dict, max_age_seconds: int = 86400):
    """Check if a fresh result exists for this tool call."""
    conn = get_db()
    try:
        h = compute_parameters_hash(tool_name, params)
        cur = conn.execute(
            "SELECT result_data FROM knowledge WHERE parameters_hash = ? AND julianday('now') - julianday(timestamp) < ?",
            (h, max_age_seconds / 86400.0)  # convert to days
        )
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None
    finally:
        conn.close()

def store_knowledge_with_hash(tool_name: str, result: Any, params: dict, **kwargs):
    """Store result with computed hash."""
    h = compute_parameters_hash(tool_name, params)
    conn = get_db()
    try:
        result_json = json.dumps(result, default=str)
        concepts_str = ','.join(kwargs.get('concepts', [])) if kwargs.get('concepts') else None
        conn.execute(
            """INSERT INTO knowledge 
               (tool_name, query_text, file_path, concepts, result_data, parameters_hash, thread_id, parent_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tool_name, kwargs.get('query'), kwargs.get('file_path'), concepts_str,
             result_json, h, kwargs.get('thread_id'), kwargs.get('parent_id'))
        )
        conn.commit()
    finally:
        conn.close()