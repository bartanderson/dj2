# tools/analysis/ingestion/scan_project_files.py

from __future__ import annotations

from pathlib import Path
from typing import Generator, Iterable, List

from tools.analysis.ingestion.parse_ast import parse_ast
from tools.analysis.shared.types import FileAnalysis


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

    Responsibilities:
    - discover Python files
    - apply ignore filtering
    - parse files into FileAnalysis objects

    Non-responsibilities:
    - persistence
    - embeddings
    - orchestration
    - reporting
    - semantic analysis
    """
    python_files = discover_python_files(
        project_root=project_root,
        ignored_directory_names=ignored_directory_names,
    )

    for file_path in python_files:
        analysis = parse_ast(file_path)

        if analysis is None:
            continue

        yield analysis