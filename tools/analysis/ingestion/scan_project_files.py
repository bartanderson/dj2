# tools/analysis/ingestion/scan_project_files.py

from __future__ import annotations

import ast
from pathlib import Path
from typing import Generator, Iterable, List
from collections import defaultdict

from tools.analysis.ingestion.extract_symbols import extract_symbols
from tools.analysis.ingestion.parse_ast import parse_ast
from tools.analysis.shared.types import FileAnalysis
from tools.analysis.graph.module_resolution import normalize_file_path
from tools.analysis.audit.symbol_audit import SymbolAudit
from tools.analysis.graph.module_resolution import (
    normalize_file_path,
    module_name_from_file_path,
)


# -------------------------
# DEBUG / METRICS
# -------------------------
symbol_counts = defaultdict(int)


# -------------------------
# IGNORED DIRECTORIES
# -------------------------
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


def should_ignore_path(path: Path, ignored_directory_names: Iterable[str]) -> bool:
    ignored = set(ignored_directory_names)
    return any(part in ignored for part in path.parts)

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
        path = path.resolve()

        if not str(path).startswith(str(root)):
            continue

        if any(part in {"site-packages", "__pycache__", ".venv", "Lib"} for part in path.parts):
            continue

        if should_ignore_path(path, ignored):
            continue

        discovered_files.append(path)

    return sorted(discovered_files)


# -------------------------
# MAIN PIPELINE
# -------------------------
def scan_project_files(
    project_root: str | Path,
    project_prefixes: list[str],
    ignored_directory_names: Iterable[str] | None = None,
) -> Generator[FileAnalysis, None, None]:

    project_root = Path(project_root).resolve()
    audit = SymbolAudit()

    python_files = discover_python_files(
        project_root=project_root,
        ignored_directory_names=ignored_directory_names,
    )

    python_files = [Path(p).resolve() for p in python_files]

    runtime_bindings = {}  # keep stable for now (no-op but explicit)

    # -------------------------
    # HARD BOUNDARY FILTER
    # -------------------------
    python_files = [
        p for p in python_files
        if str(p).startswith(str(project_root))
        and "site-packages" not in str(p)
        and "Lib\\site-packages" not in str(p)
        and ".venv" not in str(p)
        and "__pycache__" not in str(p)
    ]

    # -------------------------
    # PASS 1 — GLOBAL SYMBOLS
    # -------------------------
    GLOBAL_SYMBOLS: set[str] = set()

    for file_path in python_files:

        # -------------------------
        # SKIP NON-INFORMATIVE FILES
        # -------------------------
        if "__pycache__" in str(file_path):
            continue

        if file_path.name == "__init__.py":
            continue

        source = Path(file_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        # -------------------------
        # CANONICAL MODULE IDENTITY
        # -------------------------
        module_prefix = module_name_from_file_path(
            file_path=file_path,
            project_root=project_root,
        )

        if not module_prefix:
            continue

        symbols = extract_symbols(tree, module_prefix)

        if isinstance(symbols, dict):
            sym_set = symbols.get("all", set())
        else:
            sym_set = symbols

        # -------------------------
        # filtering: drop empty or null-like symbol entries
        # -------------------------
        sym_set = {s for s in sym_set if s}

        if not sym_set:
            continue

        GLOBAL_SYMBOLS.update(sym_set)

        print("FILE PASS1:", file_path)
        print("SYMS:", len(sym_set))
        print("GLOBAL SIZE:", len(GLOBAL_SYMBOLS))

    # -------------------------
    # PASS 2 — FULL ANALYSIS
    # -------------------------
    for file_path in python_files:

        normalized_path = normalize_file_path(file_path)

        analysis = parse_ast(
            normalized_path,
            global_known_symbols=GLOBAL_SYMBOLS,
            runtime_bindings=runtime_bindings,
        )

        print("FILE:", normalized_path)

        if analysis is None:
            continue

        # -------------------------
        # ATTACH TO ANALYSIS OBJECT
        # -------------------------
        analysis.project_symbols = GLOBAL_SYMBOLS

        print(
            "PROJECT SYMBOLS:",
            len(analysis.project_symbols)
        )

        # -------------------------
        # YIELD RESULT
        # -------------------------
        yield analysis