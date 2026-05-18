# tools/analysis/persistence/persist_file_analysis.py

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from tools.analysis.shared.types import FileAnalysis
from tools.analysis.graph.module_resolution import normalize_file_path
from tools.analysis.graph.context_classification import (
    classify_symbol_with_context,
)
from tools.analysis.graph.graph_builder import GraphBuilder
from tools.analysis.graph.evaluation_snapshot import build_evaluation_snapshot
from tools.analysis.graph.edge_semantics import classify_edge_semantics

from collections import defaultdict
bucket_counts = defaultdict(int)

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
        line_number INTEGER,
        bucket TEXT,
        edge_role TEXT
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
    
    project_symbols = getattr(analysis, "project_symbols", None) or set()
    
    ctx = ProjectGraphContext(
        project_prefixes=project_prefixes,
        project_symbols=project_symbols,
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

        cls = classify_symbol_with_context(
            identity,
            ctx,
        )

        print("CLASSIFY OUTPUT:", canonical, "->", cls)

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

    failure_events = []
    failure_breakdown = defaultdict(int)
    unknown_examples = []
    gap_samples = []
    seen_edges = set()
    builder = GraphBuilder()

    for ref in analysis.symbol_references:

        key = (ref.caller, ref.callee, ref.line_number)
        if key in seen_edges:
            continue
        seen_edges.add(key)

        full = ref.callee

        edge_role = classify_edge_semantics(ref.caller, ref.callee)

        # SINGLE SOURCE OF TRUTH
        result = classify_symbol_with_context(full, ctx)

        # ----------------------------
        # HARD NORMALIZATION CONTRACT
        # ----------------------------
        if isinstance(result, dict):

            bucket = result.get("bucket") or "classification_gap"

            failure_events.append(result)

            if bucket == "classification_gap":
                gap_samples.append({
                    "callee": full,
                    "caller": ref.caller,
                    "line": ref.line_number,
                    "normalized": normalize_symbol(full),
                    "in_global_symbols": normalize_symbol(full) in ctx.project_symbols,
                    "root": full.split(".")[0],
                })

        elif result is None:
            bucket = "classification_gap"

        else:
            bucket = str(result)

        failure_breakdown[bucket] += 1
        bucket_counts[bucket] += 1

        builder.add_reference(
            caller=ref.caller,
            callee=ref.callee,
            line_number=ref.line_number,
            bucket=bucket,   # ALWAYS STRING NOW
        )

        # persist EVERYTHING


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
            bucket,
            edge_role,
        ))

    connection.commit()

    graph = builder.build()
    print("GRAPH EDGES:", len(graph.edges))
    snapshot = build_evaluation_snapshot(
        analysis,
        bucket_counts,
        graph,
        failure_events=failure_events,
    )
    print("\n===== EVALUATION SNAPSHOT =====")
    print(snapshot)
    return graph


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