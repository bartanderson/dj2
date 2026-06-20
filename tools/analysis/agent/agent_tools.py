# tools/analysis/agent/agent_tools.py
#
# Tool functions for the local conversational agent (DESIGN.md section 8).
# Each tool is a plain function: takes (oracle, assessor, args_dict) and
# returns a plain string or list. All are independently testable against
# a real corpus DB before being wired into the agent loop.
#
# Tools are intentionally thin wrappers over existing layers - no logic
# lives here that belongs in the layers themselves.

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.analysis.oracle.db_oracle import DBOracle
    from tools.analysis.assessor.assessor import Assessor


# ------------------------------------------------------------------
# DISCOVERY TOOLS
# ------------------------------------------------------------------

def search_symbols(oracle: "DBOracle", args: dict) -> str:
    """
    search_symbols(query) - find symbols by name substring.
    Returns up to 20 matches: name, file, line, type.
    """
    query = args.get("query", "").strip()
    if not query:
        return "ERROR: query argument required"
    results = oracle.find_symbols(query, limit=20)
    if not results:
        return f"No symbols found matching '{query}'"
    lines = [f"Symbols matching '{query}':"]
    for r in results:
        file_short = r["file_path"].replace("\\", "/").split("/")[-1]
        lines.append(f"  {r['name']} ({r['symbol_type']}) in {file_short} line {r['line_number']}")
    return "\n".join(lines)


def search_files(oracle: "DBOracle", args: dict) -> str:
    """
    search_files(query) - find files by path substring.
    Returns matching file paths with line counts.
    """
    query = args.get("query", "").strip()
    if not query:
        return "ERROR: query argument required"
    results = oracle.find_files(pattern=query)
    if not results:
        return f"No files found matching '{query}'"
    lines = [f"Files matching '{query}':"]
    for r in results:
        path = r["file_path"].replace("\\", "/")
        # trim to project-relative
        for prefix in [oracle.get_project_root().replace("\\", "/") + "/"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
        lines.append(f"  {path} ({r['line_count']} lines)")
    return "\n".join(lines)


def list_callers(oracle: "DBOracle", args: dict) -> str:
    """
    list_callers(symbol) - direct callers from graph_edges.
    Matches bare name and module.name qualified forms.
    """
    symbol = args.get("symbol", "").strip()
    if not symbol:
        return "ERROR: symbol argument required"
    rows = oracle.conn.execute(
        """
        SELECT ge.caller, sr.file_path, ge.line_number
        FROM graph_edges ge
        LEFT JOIN symbol_references sr
            ON ge.caller = sr.caller AND ge.callee = sr.callee
        WHERE ge.callee = ? OR ge.callee LIKE ?
        ORDER BY sr.file_path, ge.line_number
        """,
        (symbol, f"%.{symbol}"),
    ).fetchall()
    if not rows:
        return f"No direct callers found for '{symbol}'"
    lines = [f"Direct callers of '{symbol}':"]
    for r in rows:
        file_short = (r[1] or "?").replace("\\", "/").split("/")[-1]
        lines.append(f"  {r[0]} in {file_short} line {r[2]}")
    return "\n".join(lines)


def list_callees(oracle: "DBOracle", args: dict) -> str:
    """
    list_callees(symbol) - what this symbol calls, from graph_edges.
    """
    symbol = args.get("symbol", "").strip()
    if not symbol:
        return "ERROR: symbol argument required"
    rows = oracle.conn.execute(
        """
        SELECT ge.callee, sr.file_path, ge.line_number
        FROM graph_edges ge
        LEFT JOIN symbol_references sr
            ON ge.caller = sr.caller AND ge.callee = sr.callee
        WHERE ge.caller = ?
        ORDER BY ge.line_number
        LIMIT 30
        """,
        (symbol,),
    ).fetchall()
    if not rows:
        return f"No callees found for '{symbol}' (symbol may not exist or makes no calls)"
    lines = [f"'{symbol}' calls:"]
    for r in rows:
        file_short = (r[1] or "?").replace("\\", "/").split("/")[-1]
        lines.append(f"  {r[0]} in {file_short} line {r[2]}")
    return "\n".join(lines)


def symbols_in_file(oracle: "DBOracle", args: dict) -> str:
    """
    symbols_in_file(file_path) - all functions and classes in a file.
    file_path may be relative (e.g. 'world/encounter_generator.py').
    """
    file_path = args.get("file_path", "").strip()
    if not file_path:
        return "ERROR: file_path argument required"
    # match on suffix so relative paths work
    normalized = file_path.replace("\\", "/")
    rows = oracle.conn.execute(
        """
        SELECT name, symbol_type, line_number, docstring
        FROM (
            SELECT name, 'function' as symbol_type, line_number, docstring
            FROM functions WHERE file_path LIKE ?
            UNION ALL
            SELECT name, 'class' as symbol_type, line_number, docstring
            FROM classes WHERE file_path LIKE ?
        )
        ORDER BY line_number
        """,
        (f"%{normalized}", f"%{normalized}"),
    ).fetchall()
    if not rows:
        return f"No symbols found in '{file_path}' (file may not be in corpus)"
    lines = [f"Symbols in '{file_path}':"]
    for r in rows:
        has_doc = " [has docstring]" if r[3] else ""
        lines.append(f"  line {r[2]}: {r[1]} {r[0]}{has_doc}")
    return "\n".join(lines)


def files_in_directory(oracle: "DBOracle", args: dict) -> str:
    """
    files_in_directory(path) - list files in a directory from the corpus.
    path is a relative directory name e.g. 'world' or 'dungeon_neo'.
    """
    path = args.get("path", "").strip().rstrip("/").rstrip("\\")
    if not path:
        return "ERROR: path argument required"
    results = oracle.find_files(pattern=f"/{path}/")
    if not results:
        # try without leading slash for edge cases
        results = oracle.find_files(pattern=path)
    if not results:
        return f"No files found in directory '{path}'"
    root = oracle.get_project_root().replace("\\", "/")
    lines = [f"Files in '{path}/':"]
    for r in results:
        fp = r["file_path"].replace("\\", "/")
        if root and fp.startswith(root + "/"):
            fp = fp[len(root) + 1:]
        lines.append(f"  {fp} ({r['line_count']} lines)")
    return "\n".join(lines)


# ------------------------------------------------------------------
# UNDERSTANDING TOOLS
# ------------------------------------------------------------------

def describe_file(assessor: "Assessor", args: dict) -> str:
    """
    describe_file(file_path) - AI semantic summary of a file.
    file_path may be relative e.g. 'world/encounter_generator.py'.
    Auto-reads source via Assessor (Layer 3). Falls back to heuristic
    stub if Ollama is unavailable - result will say [heuristic].
    """
    file_path = args.get("file_path", "").strip()
    if not file_path:
        return "ERROR: file_path argument required"
    result = assessor.semantic_summary(file_path, kind="file")
    content = result.get("content", "")
    cache_note = " [cached]" if result.get("cache_hit") else ""
    return f"Summary of '{file_path}'{cache_note}:\n{content}"


def symbol_intent(oracle: "DBOracle", args: dict) -> str:
    """
    symbol_intent(symbol) - docstring for a function or class (Layer 2).
    Returns None-equivalent message if no docstring exists.
    """
    symbol = args.get("symbol", "").strip()
    if not symbol:
        return "ERROR: symbol argument required"
    row = oracle.conn.execute(
        "SELECT name, file_path, line_number, docstring FROM functions WHERE name = ? LIMIT 1",
        (symbol,),
    ).fetchone()
    if not row:
        row = oracle.conn.execute(
            "SELECT name, file_path, line_number, docstring FROM classes WHERE name = ? LIMIT 1",
            (symbol,),
        ).fetchone()
    if not row:
        return f"'{symbol}' not found in corpus"
    if not row[3]:
        file_short = row[1].replace("\\", "/").split("/")[-1]
        return f"'{symbol}' in {file_short} line {row[2]}: no docstring"
    file_short = row[1].replace("\\", "/").split("/")[-1]
    return f"'{symbol}' in {file_short} line {row[2]}:\n{row[3]}"


def symbol_brief(assessor: "Assessor", args: dict) -> str:
    """
    symbol_brief(symbol) - full two-tier brief: direct callers + impact zone.
    Calls generate_task_md. Richest single-symbol output available.
    """
    symbol = args.get("symbol", "").strip()
    if not symbol:
        return "ERROR: symbol argument required"
    return assessor.generate_task_md(symbol)


# ------------------------------------------------------------------
# KNOWLEDGE TOOLS
# ------------------------------------------------------------------

def get_findings(assessor: "Assessor", args: dict) -> str:
    """
    get_findings(symbol) - stored knowledge artifacts for a symbol.
    Matches bare symbol name, file::symbol form, and LIKE %::symbol.
    Provenance-ranked: human-confirmed first. Flags stale findings.
    """
    symbol = args.get("symbol", "").strip()
    if not symbol:
        return "ERROR: symbol argument required"
    # Try exact match first, then suffix match for file::symbol subjects
    artifacts = assessor.get_artifacts(symbol)
    if not artifacts and assessor._knowledge_conn:
        rows = assessor._knowledge_conn.execute(
            "SELECT id, subject, kind, content, provenance, created_at, file_hash, needs_review "
            "FROM knowledge_artifacts WHERE subject LIKE ? ORDER BY created_at DESC",
            (f"%::{symbol}",),
        ).fetchall()
        from tools.analysis.intent.knowledge_artifact import _row_to_dict, _PROVENANCE_RANK
        artifacts = [_row_to_dict(r) for r in rows]
        artifacts.sort(key=lambda r: _PROVENANCE_RANK.get(r["provenance"], 0), reverse=True)
    if not artifacts:
        return f"No stored findings for '{symbol}'"
    lines = [f"Findings for '{symbol}':"]
    for a in artifacts:
        stale = " [STALE - needs review]" if a.get("needs_review") else ""
        lines.append(f"  [{a['kind']} / {a['provenance']}]{stale}")
        lines.append(f"    {a['content']}")
    return "\n".join(lines)


def store_finding(assessor: "Assessor", args: dict) -> str:
    """
    store_finding(symbol, kind, content) - write a derived finding to knowledge.db.
    Provenance is always ai-generated. Valid kinds:
    file_purpose / strategy_decision / query_finding / design_note / known_issue
    Use when a non-obvious finding took multiple tool calls to derive.
    """
    symbol = args.get("symbol", "").strip()
    kind = args.get("kind", "").strip()
    content = args.get("content", "").strip()
    if not symbol or not kind or not content:
        return "ERROR: symbol, kind, and content are all required"
    try:
        assessor.add_artifact(symbol, kind, content, "ai-generated")
        return f"Stored {kind} finding for '{symbol}'"
    except ValueError as e:
        return f"ERROR: {e}"


# ------------------------------------------------------------------
# TRUTH LAYER TOOL
# ------------------------------------------------------------------

def ask_truth_layer(assessor: "Assessor", args: dict) -> str:
    """
    ask_truth_layer(question) - NL query through the Truth Kernel algebra.
    Returns structured answer from the 7 truth views. Use for system-wide
    structural questions, not per-symbol questions (use other tools for those).
    """
    question = args.get("question", "").strip()
    if not question:
        return "ERROR: question argument required"
    try:
        result = assessor.ask(question)
        # result is a QuerySessionResult - extract readable content
        answer = result.get_field("content") if hasattr(result, "get_field") else str(result)
        return f"Truth layer answer:\n{answer}"
    except Exception as e:
        return f"Truth layer error: {e}"


# ------------------------------------------------------------------
# TOOL REGISTRY - maps tool name -> (function, required_arg, layer)
# layer: 'oracle' | 'assessor' (determines which object to pass)
# ------------------------------------------------------------------

TOOLS = {
    "search_symbols":    (search_symbols,    "oracle"),
    "search_files":      (search_files,      "oracle"),
    "list_callers":      (list_callers,      "oracle"),
    "list_callees":      (list_callees,      "oracle"),
    "symbols_in_file":   (symbols_in_file,   "oracle"),
    "files_in_directory":(files_in_directory,"oracle"),
    "describe_file":     (describe_file,     "assessor"),
    "symbol_intent":     (symbol_intent,     "oracle"),
    "symbol_brief":      (symbol_brief,      "assessor"),
    "get_findings":      (get_findings,      "assessor"),
    "store_finding":     (store_finding,     "assessor"),
    "ask_truth_layer":   (ask_truth_layer,   "assessor"),
}


def dispatch(tool_name: str, args: dict, oracle: "DBOracle", assessor: "Assessor") -> str:
    """Execute a tool by name. Returns result string."""
    if tool_name not in TOOLS:
        available = ", ".join(TOOLS)
        return f"ERROR: unknown tool '{tool_name}'. Available: {available}"
    fn, layer = TOOLS[tool_name]
    obj = oracle if layer == "oracle" else assessor
    try:
        return fn(obj, args)
    except Exception as e:
        return f"ERROR in {tool_name}: {type(e).__name__}: {e}"
