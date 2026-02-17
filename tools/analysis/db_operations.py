"""Database operations for scout data."""
import sqlite3
import json
from typing import List, Tuple, Optional, Dict, Any

def get_imports(db_path, file_path):
    """Return list of imported module names for a file."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT imported_module FROM imports WHERE importer_path = ?",
        (file_path,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]
    
# ----------------------------------------------------------------------
# Insert functions
# ----------------------------------------------------------------------

def insert_file(conn: sqlite3.Connection, file_path: str, file_data: dict, role: str, line_count: int, is_hot: bool) -> None:
    """Insert or replace a file record."""
    conn.execute(
        "INSERT OR REPLACE INTO files (path, data, role, line_count, is_hot) VALUES (?, ?, ?, ?, ?)",
        (file_path, json.dumps(file_data, default=str), role, line_count, 1 if is_hot else 0)
    )

def insert_import(conn: sqlite3.Connection, importer_path: str, imported_module: str, import_type: str, line_number: int) -> None:
    """Insert an import record."""
    conn.execute(
        "INSERT INTO imports (importer_path, imported_module, import_type, line_number) VALUES (?, ?, ?, ?)",
        (importer_path, imported_module, import_type, line_number)
    )

def insert_dict_key(conn: sqlite3.Connection, file_path: str, function_name: str, dict_var: str, key: str) -> None:
    """Insert a dictionary key access record."""
    conn.execute(
        "INSERT INTO dict_key_access (file_path, function_name, dict_var, key) VALUES (?, ?, ?, ?)",
        (file_path, function_name, dict_var, key)
    )

def insert_method_param(conn: sqlite3.Connection, file_path: str, class_name: Optional[str], method_name: str, param_name: str, position: int) -> None:
    """Insert a method parameter record."""
    conn.execute(
        "INSERT INTO method_params (file_path, class_name, method_name, param_name, param_position) VALUES (?, ?, ?, ?, ?)",
        (file_path, class_name, method_name, param_name, position)
    )

def insert_class_constructor(conn: sqlite3.Connection, file_path: str, class_name: str, param_name: str, position: int) -> None:
    """Insert a class constructor parameter record."""
    conn.execute(
        "INSERT INTO class_constructors (file_path, class_name, param_name, param_position) VALUES (?, ?, ?, ?)",
        (file_path, class_name, param_name, position)
    )

def insert_behavioral_contract(conn: sqlite3.Connection, file_path: str, function_name: str, line_number: int,
                               description: str, side_effects: List[str], testable_behaviors: List[str], complexity_score: int) -> None:
    """Insert a behavioral contract record."""
    conn.execute(
        """INSERT INTO behavioral_contracts 
           (file_path, function_name, line_number, description, side_effects, testable_behaviors, complexity_score)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (file_path, function_name, line_number, description,
         json.dumps(side_effects), json.dumps(testable_behaviors), complexity_score)
    )

def insert_embedding(conn: sqlite3.Connection, file_path: str, embedding_bytes: bytes) -> None:
    """Insert or replace a file embedding."""
    conn.execute(
        "INSERT OR REPLACE INTO file_embeddings (file_path, embedding) VALUES (?, ?)",
        (file_path, embedding_bytes)
    )

def insert_test_coverage(conn: sqlite3.Connection, source_path: str, test_path: Optional[str], test_exists: bool) -> None:
    """Insert or replace a test coverage record."""
    conn.execute(
        "INSERT OR REPLACE INTO test_coverage (source_path, test_path, test_exists) VALUES (?, ?, ?)",
        (source_path, test_path, 1 if test_exists else 0)
    )

def insert_concept(conn: sqlite3.Connection, concept: str, file_path: str) -> None:
    """Insert a concept-file association."""
    conn.execute(
        "INSERT OR IGNORE INTO concepts (concept, file_path) VALUES (?, ?)",
        (concept, file_path)
    )

def insert_cluster(conn: sqlite3.Connection, cluster_name: str, file_paths: List[str]) -> None:
    """Insert or replace a cluster."""
    conn.execute(
        "INSERT OR REPLACE INTO clusters (cluster_name, file_paths) VALUES (?, ?)",
        (cluster_name, json.dumps(file_paths))
    )

def insert_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Insert or replace a meta key."""
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, value)
    )

# ----------------------------------------------------------------------
# Clear functions (for force mode)
# ----------------------------------------------------------------------

def clear_table(conn: sqlite3.Connection, table_name: str) -> None:
    """Delete all rows from a table (but keep the table)."""
    conn.execute(f"DELETE FROM {table_name}")

def clear_all_dependent_tables(conn: sqlite3.Connection) -> None:
    """Clear all tables that have foreign keys to files (for a fresh start)."""
    tables = [
        "imports",
        "dict_key_access",
        "method_params",
        "class_constructors",
        "behavioral_contracts",
        "file_embeddings",
        "test_coverage",
        "concepts",
        "clusters",
        # Note: files table is not cleared here; it's handled separately if needed.
    ]
    for table in tables:
        clear_table(conn, table)