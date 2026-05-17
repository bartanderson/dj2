# tools/analysis/persistence/persist_file_analysis.py

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.analysis.shared.types import FileAnalysis
from tools.analysis.graph.module_resolution import normalize_file_path
from tools.analysis.graph.symbol_classifier import (
    classify_symbol,
    project_key,
)
from tools.analysis.graph.symbol_router import route_symbol
from tools.analysis.graph.context_classification import (
    classify_symbol_with_context,
)

def _identity_symbol(name: str) -> str:
    if not name:
        return name
    return name.split(".")[-1]   # LAST segment = correct stable identity

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
        from_file TEXT,
        to_module TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        symbol_type TEXT,
        name TEXT,
        line_number INTEGER,
        signature TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbol_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        caller TEXT,
        callee TEXT,
        line_number INTEGER
    )
    """)

    connection.commit()


def _canonical_symbol(name: str) -> str:
    if not name:
        return name
    return name.split(".")[-1]


def persist_file_analysis(
    connection: sqlite3.Connection,
    analysis: FileAnalysis,
    project_prefixes,
) -> None:

    analysis.file_path = normalize_file_path(analysis.file_path)
    cursor = connection.cursor()

    runtime_bindings = analysis.runtime_bindings

    from tools.analysis.graph.project_graph_context import (
        ProjectGraphContext,
    )

    ctx = ProjectGraphContext(
        project_prefixes=project_prefixes,
        project_symbols=analysis.project_symbols,
        runtime_bindings=runtime_bindings,
    )

    functions = list(analysis.functions)
    classes = list(analysis.classes)

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

    for function in functions:
        canonical = _canonical_symbol(function.name)
        identity = _identity_symbol(function.name)   # MUST BE FIRST

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
            canonical,
            function.line_number,
            function.return_type,
            json.dumps(function.arguments),
        ))

        cls = classify_symbol_with_context(
            canonical,
            ctx,
        )

        print("CLASSIFY OUTPUT:", canonical, "->", cls)

        if cls == "project":
            _insert_symbol(
                cursor,
                analysis.file_path,
                "function",
                canonical,
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

    for class_obj in classes:
        identity = _identity_symbol(class_obj.name)
        canonical = _canonical_symbol(class_obj.name)

        route = route_symbol(
            canonical,
            runtime_bindings,
            analysis.project_symbols
        )

        print("ROUTE DEBUG |", canonical, "->", route)

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
            canonical,
            class_obj.line_number,
            json.dumps(class_obj.methods),
            json.dumps(class_obj.base_classes),
        ))

        cls = classify_symbol(
            identity,
            route,
            project_prefixes,
            runtime_bindings,
            analysis.project_symbols
        )

        if cls == "project":
            _insert_symbol(
                cursor,
                analysis.file_path,
                "class",
                canonical,
                class_obj.line_number,
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
    # SYMBOL REFERENCES (FIXED)
    # -------------------------
    cursor.execute(
        "DELETE FROM symbol_references WHERE file_path = ?",
        (analysis.file_path,),
    )

    from collections import defaultdict
    bucket_counts = defaultdict(int)
    KNOWN_BUCKETS = {
        "project",
        "builtin",
        "stdlib",
        "runtime",
        "external_lib",
        "external_unknown",
    }

    seen_edges = set()

    for ref in analysis.symbol_references:

        key = (ref.caller, ref.callee, ref.line_number)
        if key in seen_edges:
            continue
        seen_edges.add(key)

        full = ref.callee
        identity = _identity_symbol(full)

        result = classify_symbol_with_context(
            full,
            ctx,
        )

        print("CLASSIFY:", full, "->", result)

        bucket_counts[result] += 1

        full = ref.callee
        identity = _identity_symbol(full)

        result = classify_symbol_with_context(
            full,
            ctx,
        )

        # REQUIRED ADDITION
        bucket_counts[result] += 1

        has_dot = "." in full
        root = full.split(".")[-1] if full else full

        is_project = (
            project_key(full) in {
                project_key(symbol)
                for symbol in analysis.project_symbols
            }
            if analysis.project_symbols
            else False
        )

        print(
            "CLASSIFY DEBUG |",
            "raw=", full,
            "| identity=", identity,
            "| root=", root,
            "| dot=", has_dot,
            "| project_match=", is_project
        )

        if result.startswith("external_lib."):
            base = "external_lib"
        elif result in KNOWN_BUCKETS:
            base = result
        else:
            print("⚠ UNKNOWN BUCKET:", result, "for", full)
            base = result

        bucket_counts[base] += 1

        if result == "external_lib" and not has_dot:
            print("⚠ OVERMATCH external_lib without dot:", full)

        if result == "external_unknown" and has_dot:
            print("⚠ MISCLASSIFIED dotted symbol as unknown:", full)

        if result == "project" and not analysis.project_symbols:
            print("⚠ EMPTY PROJECT SYMBOL SET BUT PROJECT CLASSIFIED:", full)

        if result != "project":
            continue

        cursor.execute("""
        INSERT INTO symbol_references (
            file_path,
            caller,
            callee,
            line_number
        )
        VALUES (?, ?, ?, ?)
        """, (
            analysis.file_path,
            ref.caller,
            ref.callee,
            ref.line_number,
        ))

    connection.commit()
    external_roots = defaultdict(int)

    for k, v in bucket_counts.items():
        if k.startswith("external_lib."):
            root = k.split(".", 1)[1]
            external_roots[root] += v

    summary = {
        "project": bucket_counts.get("project", 0),
        "builtin": bucket_counts.get("builtin", 0),
        "stdlib": bucket_counts.get("stdlib", 0),
        "runtime": bucket_counts.get("runtime", 0),
        "external_lib_total": sum(v for k, v in bucket_counts.items() if k.startswith("external_lib")),
        "external_roots": dict(sorted(external_roots.items(), key=lambda x: -x[1])[:10]),
        "external_unknown": bucket_counts.get("external_unknown", 0),
    }

    print("\n===== CLASSIFICATION SUMMARY (STRUCTURED) =====")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("==============================================\n")
    print(
        f"SNAPSHOT | "
        f"P={summary['project']} "
        f"B={summary['builtin']} "
        f"S={summary['stdlib']} "
        f"R={summary['runtime']} "
        f"E={summary['external_lib_total']} "
        f"U={summary['external_unknown']}"
    )


def create_database(database_path: str | Path) -> sqlite3.Connection:
    database_path = Path(database_path)

    if database_path.exists():
        print("\n" + "=" * 80)
        print("⚠️  WARNING: Existing database detected")
        print(f"📁 Path: {database_path}")
        print("\nIf results look wrong:")
        print("1. delete the DB file manually")
        print("2. rerun pipeline")
        print("=" * 80 + "\n")

    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(database_path))
    initialize_database(connection)

    return connection


def _insert_symbol(cursor, file_path, symbol_type, name, line_number, signature=""):
    cursor.execute("""
    INSERT INTO symbols (
        file_path,
        symbol_type,
        name,
        line_number,
        signature
    )
    VALUES (?, ?, ?, ?, ?)
    """, (file_path, symbol_type, name, line_number, signature))

def run_sql(connection: sqlite3.Connection, query: str):
    """
    Debug utility ONLY.
    Centralized SQL execution so we don't scatter ad-hoc scripts.
    """
    cursor = connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()