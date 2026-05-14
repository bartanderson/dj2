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
from tools.analysis.audit.symbol_audit import SymbolAudit



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

        path = path.resolve()

        # HARD BOUNDARY: must remain inside project root
        if not str(path).startswith(str(root)):
            continue

        # HARD ENVIRONMENT EXCLUSION
        if any(part in {"site-packages", "__pycache__", ".venv", "Lib"} for part in path.parts):
            continue

        # your existing ignore rules
        if should_ignore_path(path, ignored):
            continue

        discovered_files.append(path)

    return sorted(discovered_files)

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

    # normalize early so filtering is consistent
    python_files = [
        Path(p).resolve()
        for p in python_files
    ]

    # -------------------------------------------------
    # HARD BOUNDARY FILTER (prevents environment leakage)
    # -------------------------------------------------
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
        source = Path(file_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        module_prefix = normalize_file_path(file_path).replace("/", ".").rstrip(".py")

        symbols = extract_symbols(tree, module_prefix)

        if isinstance(symbols, dict):
            sym_set = symbols.get("all", set())
        else:
            sym_set = symbols

        GLOBAL_SYMBOLS.update(sym_set)

        # # audit: definition frequency only
        # for s in sym_set:
        #     audit.symbol_counts[s] += 1

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

        # -------------------------
        # PER-FILE PROJECT SYMBOLS
        # -------------------------

        project_symbols: set[str] = set()

        # functions
        for f in analysis.functions:
            project_symbols.add(f.name.split(".")[-1]) # get the last name in dotted list and add to functions

        # classes
        for c in analysis.classes:
            for method in c.methods:
                project_symbols.add(c.name.split(".")[-1]) # get the last name in dotted list and add to classes

        # attach semantic truth to analysis object
        analysis.project_symbols = project_symbols

        # # audit: usage frequency ONLY
        # for ref in analysis.symbol_references:
        #     audit.total += 1
        #     audit.symbol_counts[ref.callee] += 1

        yield analysis

    # print("\n=== SYMBOL AUDIT ===")
    # print("Total references:", audit.total)
    # print("Unique symbols:", len(audit.symbol_counts))

    # print("\nTop symbols:")
    # for k, v in audit.symbol_counts.most_common(15):
    #     print(v, k)