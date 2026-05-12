# tools/analysis/ingestion/scan_project_files.py

from __future__ import annotations

import ast
from tools.analysis.ingestion.extract_symbols import extract_symbols
from pathlib import Path
from typing import Generator, Iterable, List

from tools.analysis.ingestion.parse_ast import parse_ast, _safe_read_file
from tools.analysis.shared.types import FileAnalysis
from tools.analysis.graph.module_resolution import normalize_file_path
from tools.analysis.persistence.persist_file_analysis import create_database
from tools.analysis.graph.symbol_index import build_symbol_index



DEFAULT_IGNORED_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "archive",
    "tools_old",
}


def should_ignore_path(
    path: Path,
    ignored_directory_names: Iterable[str],
) -> bool:
    ignored = set(ignored_directory_names)

    for part in path.parts:
        if part in ignored:
            return True

    return False


def discover_python_files(
    project_root: str | Path,
    ignored_directory_names: Iterable[str] | None = None,
) -> List[Path]:
    root = Path(project_root).resolve()

    ignored = (
        set(ignored_directory_names)
        if ignored_directory_names is not None
        else DEFAULT_IGNORED_DIRECTORIES
    )

    discovered_files: List[Path] = []

    for path in root.rglob("*.py"):
        if should_ignore_path(path, ignored):
            continue

        discovered_files.append(path)

    return sorted(discovered_files)

def scan_project_files(
    project_root: str | Path,
    ignored_directory_names: Iterable[str] | None = None,
) -> Generator[FileAnalysis, None, None]:
    """
Deterministic project scan.

Two-phase pipeline:

PASS 1:
- discover Python files
- apply ignore filtering
- build GLOBAL_SYMBOLS from per-file local symbol extraction

PASS 2:
- parse each file into FileAnalysis
- resolve symbol references using GLOBAL_SYMBOLS

Constraints:
- no database access during scanning or analysis
- no persistence in this module
- no cross-file graph construction here

Outputs:
- FileAnalysis stream (generator)
    """

    python_files = discover_python_files(
        project_root=project_root,
        ignored_directory_names=ignored_directory_names,
    )

    # -------------------------
    # PASS 1 — GLOBAL SYMBOLS
    # -------------------------
    GLOBAL_SYMBOLS: set[str] = set()

    for file_path in python_files:
        source = Path(file_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        symbols = extract_symbols(tree)

        # normalize to set safety (extract_symbols may return dict or set)
        if isinstance(symbols, dict):
            GLOBAL_SYMBOLS.update(symbols.get("all", set()))
        else:
            GLOBAL_SYMBOLS.update(symbols)

    # -------------------------
    # PASS 2 — FULL ANALYSIS
    # -------------------------
    for file_path in python_files:
        normalized_path = normalize_file_path(file_path)

        analysis = parse_ast(
            normalized_path,
            global_known_symbols=GLOBAL_SYMBOLS,
        )

        if analysis is None:
            continue

        yield analysis