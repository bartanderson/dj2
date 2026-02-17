"""Database query functions for the scout DB."""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

def get_imports(db_path: Path, file_path: str) -> List[str]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT imported_module FROM imports WHERE importer_path = ?",
        (file_path,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_dict_keys(db_path: Path, file_path: str, function_name: str) -> List[str]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT key FROM dict_key_access WHERE file_path = ? AND function_name = ? ORDER BY key",
        (file_path, function_name)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_method_params(db_path: Path, file_path: str, method_name: str, class_name: Optional[str] = None) -> List[str]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    if class_name:
        rows = cur.execute(
            "SELECT param_name FROM method_params WHERE file_path = ? AND class_name = ? AND method_name = ? ORDER BY param_position",
            (file_path, class_name, method_name)
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT param_name FROM method_params WHERE file_path = ? AND class_name IS NULL AND method_name = ? ORDER BY param_position",
            (file_path, method_name)
        ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_class_constructor_params(db_path: Path, class_file: str, class_name: str) -> List[str]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT param_name FROM class_constructors WHERE file_path = ? AND class_name = ? ORDER BY param_position",
        (class_file, class_name)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_behavioral_contract(db_path: Path, file_path: str, function_name: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute(
        "SELECT description, side_effects, testable_behaviors FROM behavioral_contracts WHERE file_path = ? AND function_name = ?",
        (file_path, function_name)
    ).fetchone()
    conn.close()
    if row:
        return {
            "description": row["description"],
            "side_effects": json.loads(row["side_effects"] or "[]"),
            "testable_behaviors": json.loads(row["testable_behaviors"] or "[]")
        }
    return None

def get_file_list(db_path: Path) -> set:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute("SELECT path FROM files").fetchall()
    conn.close()
    return {r[0] for r in rows}