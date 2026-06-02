# tools/analysis/inspection/system_shape.py

from __future__ import annotations

import sqlite3
from collections import defaultdict


def generate_system_shape(connection: sqlite3.Connection) -> dict:
    cursor = connection.cursor()

    # --------------------------
    # FILE OVERVIEW
    # --------------------------
    cursor.execute("""
        SELECT file_path, role, is_hot, line_count
        FROM files
    """)
    files = cursor.fetchall()

    role_counts = defaultdict(int)
    hot_files = []
    total_lines = 0

    for file_path, role, is_hot, line_count in files:
        role_counts[role or "unknown"] += 1
        total_lines += line_count or 0

        if is_hot:
            hot_files.append(file_path)

    # --------------------------
    # IMPORT STRUCTURE
    # --------------------------
    cursor.execute("""
        SELECT file_path, module
        FROM imports
    """)
    imports = cursor.fetchall()

    external = 0
    internal = 0
    module_frequency = defaultdict(int)

    for _, module in imports:
        module_frequency[module] += 1
        if module.startswith("tools."):
            internal += 1
        else:
            external += 1

    # --------------------------
    # SYMBOL GRAPH DENSITY
    # --------------------------
    cursor.execute("""
        SELECT caller, callee
        FROM symbol_references
    """)
    edges = cursor.fetchall()

    node_degree = defaultdict(int)

    for caller, callee in edges:
        node_degree[caller] += 1
        node_degree[callee] += 1

    top_connected = sorted(
        node_degree.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    # --------------------------
    # CONTRACT HEALTH
    # --------------------------
    cursor.execute("""
        SELECT severity, contract_name
        FROM contract_violations
    """)
    violations = cursor.fetchall()

    severity_counts = defaultdict(int)
    for severity, _ in violations:
        severity_counts[severity or "unknown"] += 1

    # --------------------------
    # SYSTEM SHAPE INFERENCE
    # --------------------------
    shape_tags = []

    if external > internal:
        shape_tags.append("external_dependency_heavy")

    if len(violations) > 20:
        shape_tags.append("contract_weak_system")

    if len(hot_files) > len(files) * 0.2:
        shape_tags.append("hotspot_concentrated")

    if max(node_degree.values(), default=0) > 50:
        shape_tags.append("high_coupling_core")

    # --------------------------
    # FINAL OUTPUT
    # --------------------------
    return {
        "file_count": len(files),
        "total_lines": total_lines,

        "role_distribution": dict(role_counts),

        "imports": {
            "internal": internal,
            "external": external,
            "top_modules": sorted(module_frequency.items(), key=lambda x: x[1], reverse=True)[:10],
        },

        "graph": {
            "edge_count": len(edges),
            "most_connected_nodes": [
                {"symbol": k, "degree": v} for k, v in top_connected
            ],
        },

        "contracts": {
            "violations": len(violations),
            "severity": dict(severity_counts),
        },

        "hot_files": hot_files[:10],

        "system_shape_tags": shape_tags,
    }