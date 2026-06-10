# tools/analysis/persistence/persistence_engine.py


from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from tools.analysis.shared.types import FileAnalysis
from tools.analysis.core.pathing import normalize_file_path
from tools.analysis.identity.edge_identity import edge_identity

def ensure_schema(connection):
    initialize_database(connection)

def _insert_symbol(cursor, file_path, symbol_type, name, line_number, signature=""):
    canonical_id = f"{file_path}:{symbol_type}:{name}:{line_number}"

    cursor.execute("""
    INSERT INTO symbols (
        file_path,
        symbol_type,
        name,
        line_number,
        signature,
        canonical_id
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        file_path,
        symbol_type,
        name,
        line_number,
        signature,
        canonical_id
    ))

def run_sql(connection: sqlite3.Connection, query: str):
    """
    Debug utility ONLY.
    Centralized SQL execution so we don't scatter ad-hoc scripts.
    """
    cursor = connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def initialize_database(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        file_path TEXT PRIMARY KEY,
        line_count INTEGER,
        role TEXT,
        is_hot INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS functions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        name TEXT,
        line_number INTEGER,
        return_type TEXT,
        arguments_json TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        name TEXT,
        line_number INTEGER,
        methods_json TEXT,
        base_classes_json TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        module TEXT,
        import_type TEXT,
        line_number INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS behavioral_contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        function_name TEXT,
        line_number INTEGER,
        description TEXT,
        side_effects_json TEXT,
        raises_json TEXT,
        testable_behaviors_json TEXT,
        complexity_score INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mutations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        line_number INTEGER,
        target TEXT,
        operation TEXT,
        raw_expression TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS file_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_file TEXT NOT NULL,
        to_module TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS graph_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        /* semantic identity layer (NEW PRIMARY MODEL) */
        source_id TEXT NOT NULL,
        target_id TEXT NOT NULL,

        /* legacy observational trace (optional but useful) */
        caller TEXT,
        callee TEXT,

        line_number INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        symbol_type TEXT,
        name TEXT,
        line_number INTEGER,
        signature TEXT,
        canonical_id TEXT UNIQUE
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbol_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        caller TEXT,
        callee TEXT,
        line_number INTEGER,
        bucket TEXT,
        edge_role TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        contract_name TEXT,
        layer TEXT,
        severity TEXT,
        message TEXT,
        observed_value TEXT,
        expected_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_drift_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_name TEXT,
    classification TEXT,
    layer TEXT,
    count INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
   """)

    connection.commit()


def create_indexes(connection: sqlite3.Connection, include_composite: bool = True) -> None:
    """Add performance indexes to an existing database."""
    cursor = connection.cursor()
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_functions_file_path ON functions(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name);",
        "CREATE INDEX IF NOT EXISTS idx_classes_file_path ON classes(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name);",
        "CREATE INDEX IF NOT EXISTS idx_imports_file_path ON imports(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_imports_module ON imports(module);",
        "CREATE INDEX IF NOT EXISTS idx_contracts_file_path ON behavioral_contracts(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_contracts_function_name ON behavioral_contracts(function_name);",
        "CREATE INDEX IF NOT EXISTS idx_mutations_file_path ON mutations(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_file_edges_from_file ON file_edges(from_file);",
        "CREATE INDEX IF NOT EXISTS idx_file_edges_to_module ON file_edges(to_module);",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_source_id ON graph_edges(source_id);",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_target_id ON graph_edges(target_id);",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_caller ON graph_edges(caller);",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_callee ON graph_edges(callee);",
        "CREATE INDEX IF NOT EXISTS idx_graph_edges_line ON graph_edges(line_number);",
        "CREATE INDEX IF NOT EXISTS idx_symbols_file_path ON symbols(file_path);",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_symbols_canonical ON symbols(canonical_id);",
        "CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);",
        "CREATE INDEX IF NOT EXISTS idx_symbols_type ON symbols(symbol_type);",
        "CREATE INDEX IF NOT EXISTS idx_symref_caller ON symbol_references(caller);",
        "CREATE INDEX IF NOT EXISTS idx_symref_callee ON symbol_references(callee);",
        "CREATE INDEX IF NOT EXISTS idx_symref_file_path ON symbol_references(file_path);",
        "CREATE INDEX IF NOT EXISTS idx_symref_bucket ON symbol_references(bucket);",
        "CREATE INDEX IF NOT EXISTS idx_contract_violations ON contract_violations(id);",
        "CREATE INDEX IF NOT EXISTS idx_contract_drift_name ON contract_drift_history(contract_name);",
        "CREATE INDEX IF NOT EXISTS idx_contract_drift_time ON contract_drift_history(timestamp);"
    ]
    if include_composite:
        indexes.extend([
            "CREATE INDEX IF NOT EXISTS idx_functions_file_name ON functions(file_path, name);",
            "CREATE INDEX IF NOT EXISTS idx_classes_file_name ON classes(file_path, name);",
            "CREATE INDEX IF NOT EXISTS idx_symbols_file_name ON symbols(file_path, name);",
        ])
    for sql in indexes:
        cursor.execute(sql)
    connection.commit()


def _canonical_symbol(name: str) -> str:
    if not name:
        return name
    return name.split(".")[-1]

def persist_file_analysis(
    connection: sqlite3.Connection,
    analysis,
    project_prefixes,
) -> None:

    cursor = connection.cursor()

    analysis.file_path = normalize_file_path(analysis.file_path)


    # =========================
    # DEBUG (pre-persist inspection)
    # =========================
    print("\n[PERSIST START]")
    print("file:", analysis.file_path)
    print("symbol_refs:", len(analysis.symbol_references))


    # -------------------------
    # FILE
    # -------------------------
    cursor.execute("""
    INSERT OR REPLACE INTO files (
        file_path,
        line_count,
        role,
        is_hot
    )
    VALUES (?, ?, ?, ?)
    """, (
        analysis.file_path,
        analysis.metadata.line_count,
        analysis.metadata.role,
        int(analysis.metadata.is_hot),
    ))

    # -------------------------
    # FUNCTIONS
    # -------------------------
    cursor.execute(
        "DELETE FROM functions WHERE file_path = ?",
        (analysis.file_path,),
    )

    for function in analysis.functions:
        cursor.execute("""
        INSERT INTO functions (
            file_path,
            name,
            line_number,
            return_type,
            arguments_json
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            analysis.file_path,
            _canonical_symbol(function.name),
            function.line_number,
            function.return_type,
            json.dumps(function.arguments),
        ))

        # ONLY USE PRECOMPUTED VALUE
        if getattr(function, "bucket", None) == "project":
            _insert_symbol(
                cursor,
                analysis.file_path,
                "function",
                _canonical_symbol(function.name),
                function.line_number,
                function.return_type or "",
            )

    # -------------------------
    # CLASSES
    # -------------------------
    cursor.execute(
        "DELETE FROM classes WHERE file_path = ?",
        (analysis.file_path,),
    )

    for cls_obj in analysis.classes:
        cursor.execute("""
        INSERT INTO classes (
            file_path,
            name,
            line_number,
            methods_json,
            base_classes_json
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            analysis.file_path,
            _canonical_symbol(cls_obj.name),
            cls_obj.line_number,
            json.dumps(cls_obj.methods),
            json.dumps(cls_obj.base_classes),
        ))

        if getattr(cls_obj, "bucket", None) == "project":
            _insert_symbol(
                cursor,
                analysis.file_path,
                "class",
                _canonical_symbol(cls_obj.name),
                cls_obj.line_number,
            )

    # -------------------------
    # IMPORTS
    # -------------------------
    cursor.execute(
        "DELETE FROM imports WHERE file_path = ?",
        (analysis.file_path,),
    )

    for imp in analysis.imports:
        cursor.execute("""
        INSERT INTO imports (
            file_path,
            module,
            import_type,
            line_number
        )
        VALUES (?, ?, ?, ?)
        """, (
            analysis.file_path,
            imp.module,
            imp.import_type,
            imp.line_number,
        ))

    cursor.execute(
        "DELETE FROM file_edges WHERE from_file = ?",
        (analysis.file_path,),
    )

    for imp in analysis.imports:
        cursor.execute("""
        INSERT INTO file_edges (
            from_file,
            to_module
        )
        VALUES (?, ?)
        """, (
            analysis.file_path,
            imp.module,
        ))

    # -------------------------
    # BEHAVIORAL CONTRACTS
    # -------------------------
    cursor.execute(
        "DELETE FROM behavioral_contracts WHERE file_path = ?",
        (analysis.file_path,),
    )

    for contract in analysis.behavioral_contracts:
        cursor.execute("""
        INSERT INTO behavioral_contracts (
            file_path,
            function_name,
            line_number,
            description,
            side_effects_json,
            raises_json,
            testable_behaviors_json,
            complexity_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.file_path,
            contract.function_name,
            contract.line_number,
            contract.description,
            json.dumps(contract.side_effects),
            json.dumps(contract.raises),
            json.dumps(contract.testable_behaviors),
            contract.complexity_score,
        ))

    # -------------------------
    # MUTATIONS
    # -------------------------
    cursor.execute(
        "DELETE FROM mutations WHERE file_path = ?",
        (analysis.file_path,),
    )

    for mutation in analysis.mutations:
        cursor.execute("""
        INSERT INTO mutations (
            file_path,
            line_number,
            target,
            operation,
            raw_expression
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            analysis.file_path,
            mutation.line_number,
            mutation.target,
            mutation.operation,
            mutation.raw_expression,
        ))

    # -------------------------
    # SYMBOL REFERENCES
    # -------------------------
    cursor.execute(
        "DELETE FROM symbol_references WHERE file_path = ?",
        (analysis.file_path,),
    )

    for ref in analysis.symbol_references:
        cursor.execute("""
        INSERT INTO symbol_references (
            file_path,
            caller,
            callee,
            line_number,
            bucket,
            edge_role
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            analysis.file_path,
            ref.caller,
            ref.callee,
            ref.line_number,
            getattr(ref, "bucket", None),
            getattr(ref, "edge_role", None),
        ))

    print("[PERSIST MID] symbol_references inserted (in-memory):",
          len(analysis.symbol_references))

    connection.commit()

    # DB is now source of truth
    cursor.execute(
        "SELECT COUNT(*) FROM symbol_references WHERE file_path = ?",
        (analysis.file_path,)
    )

    db_count = cursor.fetchone()[0]

    print("\n[PERSIST END]")
    print("file:", analysis.file_path)
    print("db_rows:", db_count)
    print("in_memory:", len(analysis.symbol_references))
    print("match:", db_count == len(analysis.symbol_references))

def create_database(database_path: str | Path) -> sqlite3.Connection:
    database_path = Path(database_path)

    if database_path.exists():
        database_path.unlink()
        print(f"[RESET DB] {database_path}")

    connection = sqlite3.connect(str(database_path))
    initialize_database(connection)
    create_indexes(connection)

    return connection



# ==================================================
# PUBLIC ENTRY POINT (ONLY FUNCTION CALLED OUTSIDE)
# ==================================================
def persist_all(connection, file_analyses, graph, project_prefixes):
    """
    Single persistence orchestrator.

    ALL DB writes must flow through here.
    """

    # -----------------------------------------
    # 1. SCHEMA GUARANTEE (MUST BE FIRST)
    # -----------------------------------------
    ensure_schema(connection)

    cursor = connection.cursor()

    # -----------------------------------------
    # 2. OPTIONAL DEBUG (safe after schema exists)
    # -----------------------------------------
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    print("[DB TABLES]", cursor.fetchall())

    # -----------------------------------------
    # 3. SNAPSHOT (SAFE NOW)
    # -----------------------------------------
    cursor.execute("SELECT COUNT(*) FROM symbol_references")
    db_total = cursor.fetchone()[0]

    db_snapshot = {
        "symbol_reference_count": db_total
    }

    # -----------------------------------------
    # 4. PERSIST FILE LAYER
    # -----------------------------------------
    _persist_file_analysis(connection, file_analyses, project_prefixes)

    # -----------------------------------------
    # 5. PERSIST GRAPH LAYER
    # -----------------------------------------
    _persist_graph_edges(connection, graph)

# ==================================================
# --- SYMBOL IDENTITY LAYER (NEW) ---
# ==================================================

def make_canonical_id(file_path, symbol_type, name, line_number):
    return f"{file_path}:{symbol_type}:{name}:{line_number}"

# ==================================================
# FILE / SYMBOL PERSISTENCE (LEGACY BUT CONTAINED)
# ==================================================
def _persist_file_analysis(connection, file_analyses, project_prefixes):
    cursor = connection.cursor()

    for analysis in file_analyses:

        # existing legacy persistence
        persist_file_analysis(connection, analysis, project_prefixes)

        # 🔥 THIS WAS MISSING
        for ref in analysis.symbol_references:

            caller_id = make_canonical_id(
                analysis.file_path,
                "caller",
                ref.caller,
                ref.line_number
            )

            callee_id = make_canonical_id(
                analysis.file_path,
                "callee",
                ref.callee,
                ref.line_number
            )

            cursor.execute("""
                INSERT OR IGNORE INTO symbols (
                    file_path,
                    symbol_type,
                    name,
                    line_number,
                    signature,
                    canonical_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                analysis.file_path,
                "caller",
                ref.caller,
                ref.line_number,
                getattr(ref, "signature", ""),
                caller_id
            ))

            cursor.execute("""
                INSERT OR IGNORE INTO symbols (
                    file_path,
                    symbol_type,
                    name,
                    line_number,
                    signature,
                    canonical_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                analysis.file_path,
                "callee",
                ref.callee,
                ref.line_number,
                "",
                callee_id
            ))


# ==================================================
# GRAPH EDGE PERSISTENCE (TRUTH LAYER)
# ==================================================
def _persist_graph_edges(connection, graph):
    cursor = connection.cursor()

    # -----------------------------------------
    # GRAPH TABLE RESET (NOT file_edges)
    # -----------------------------------------
    cursor.execute("DELETE FROM graph_edges")

    # -----------------------------------------
    # INSERT CALL GRAPH
    # -----------------------------------------
    for edge in getattr(graph, "edges", []):
        source_id, target_id = edge_identity(edge.caller, edge.callee)
        cursor.execute("""
        INSERT INTO graph_edges (
            source_id,
            target_id,
            caller,
            callee,
            line_number
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            source_id,
            target_id,
            edge.caller,
            edge.callee,
            getattr(edge, "line_number", None)
        ))

    connection.commit()