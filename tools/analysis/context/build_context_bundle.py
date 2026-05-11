# tools/analysis/context/build_context_bundle.py

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Set

from tools.analysis.query.query_file_analysis import (
    fetch_complete_file_analysis, fetch_all_symbol_names,
)
from tools.analysis.ingestion.parse_ast import _safe_read_file
from pathlib import Path

from tools.analysis.graph.symbol_index import build_symbol_index
from tools.analysis.graph.module_resolution import file_path_from_module_name


def _fetch_import_dependents(connection, module_name: str):
    cursor = connection.cursor()

    cursor.execute("""
    SELECT DISTINCT from_file
    FROM file_edges
    WHERE to_module = ?
    """, (module_name,))

    return [row[0] for row in cursor.fetchall()]


def _derive_module_name(file_path: str) -> str:
    normalized = file_path.replace("\\", "/")

    if normalized.endswith(".py"):
        normalized = normalized[:-3]

    return normalized.replace("/", ".")


def build_context_bundle(
    connection: sqlite3.Connection,
    entry_file_path: str,
    include_dependents: bool = True,
    max_dependency_files: int = 10,
) -> Dict[str, Any]:
    """
    Build focused structured context around a file.

    Goals:
    - deterministic
    - bounded
    - AI-consumable
    - no raw AST access
    """

    visited: Set[str] = set()

    known_symbols = fetch_all_symbol_names(connection)

    bundle: Dict[str, Any] = {
        "entry_file": None,
        "related_files": [],
    }
    print("ENTRY INPUT:", entry_file_path)
    normalized_entry_path = entry_file_path.replace("\\", "/")
    print("Normalized ENTRY INPUT:", normalized_entry_path)

    entry_file_path = str(Path(entry_file_path).resolve()).replace("\\", "/")

    entry_analysis = fetch_complete_file_analysis(
        connection,
        entry_file_path,
    )

    symbol_index = build_symbol_index(connection)

    known_symbols = set(symbol_index.keys())

    if entry_analysis is None:
        return bundle


    entry_analysis["symbol_references"] = [
        ref
        for ref in entry_analysis["symbol_references"]
        if ref["callee"] in known_symbols
    ]

    bundle["entry_file"] = entry_analysis

    visited.add(entry_file_path)

    if not include_dependents:
        return bundle

    imports = entry_analysis["imports"]

    dependent_files = set()

    for imp in imports:
        dependent_files.update(
            _fetch_import_dependents(connection, imp["module"])
        )

    related_count = 0

    for dependent_path in dependent_files:
        if dependent_path in visited:
            continue

        related_analysis = fetch_complete_file_analysis(
            connection,
            dependent_path,
        )

        if related_analysis is None:
            continue


        related_analysis["symbol_references"] = [
            ref
            for ref in related_analysis["symbol_references"]
            if ref["callee"] in known_symbols
        ]

        bundle["related_files"].append(related_analysis)

        visited.add(dependent_path)

        related_count += 1

        if related_count >= max_dependency_files:
            break

    return bundle