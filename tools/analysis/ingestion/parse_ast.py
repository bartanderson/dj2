# tools/analysis/ingestion/parse_ast.py

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

from tools.analysis.shared.types import (
    FileAnalysis,
    FileMetadata,
    FunctionRepresentation,
    ClassRepresentation,
    ImportRepresentation,
    BehavioralContract,
    MutationEvent,
)


# ----------------------------
# Helpers (pure AST extraction)
# ----------------------------

def _safe_read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _extract_imports(tree: ast.AST) -> List[ImportRepresentation]:
    imports: List[ImportRepresentation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportRepresentation(
                        module=alias.name,
                        import_type="import",
                        line_number=getattr(node, "lineno", -1),
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(
                ImportRepresentation(
                    module=module,
                    import_type="from_import",
                    line_number=getattr(node, "lineno", -1),
                )
            )

    return imports


def _extract_functions(tree: ast.AST) -> List[FunctionRepresentation]:
    results: List[FunctionRepresentation] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [
                arg.arg
                for arg in node.args.args
                if arg.arg != "self"
            ]

            results.append(
                FunctionRepresentation(
                    name=node.name,
                    line_number=node.lineno,
                    arguments=args,
                    return_type=ast.unparse(node.returns) if getattr(node, "returns", None) else None,
                    docstring=ast.get_docstring(node),
                )
            )

    return results


def _extract_classes(tree: ast.AST) -> List[ClassRepresentation]:
    results: List[ClassRepresentation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                n.name
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            results.append(
                ClassRepresentation(
                    name=node.name,
                    line_number=node.lineno,
                    methods=methods,
                    base_classes=[ast.unparse(b) for b in node.bases],
                )
            )

    return results


def _extract_mutations(tree: ast.AST) -> List[MutationEvent]:
    # Minimal deterministic placeholder extraction
    # (you already have richer mutation logic elsewhere; we unify later)

    mutations: List[MutationEvent] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            target = None
            if isinstance(node.func.value, ast.Name):
                target = node.func.value.id

            if target:
                mutations.append(
                    MutationEvent(
                        line_number=node.lineno,
                        target=target,
                        operation=node.func.attr,
                        raw_expression=ast.unparse(node),
                    )
                )

    return mutations


def _extract_behavioral_contracts(tree: ast.AST) -> List[BehavioralContract]:
    contracts: List[BehavioralContract] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        doc = ast.get_docstring(node) or ""

        contracts.append(
            BehavioralContract(
                function_name=node.name,
                line_number=node.lineno,
                description=(doc.split("\n")[0].strip() if doc else ""),
                side_effects=[],
                raises=[],
                testable_behaviors=[],
                complexity_score=0,
            )
        )

    return contracts


# ----------------------------
# Core API (the only thing other modules should call)
# ----------------------------

def parse_ast(file_path: str | Path) -> Optional[FileAnalysis]:
    path = Path(file_path)

    source = _safe_read_file(path)
    if source is None:
        return None

    try:
        tree = ast.parse(source)
        print("DEBUG FILE:", file_path)
        print("SOURCE LENGTH:", len(source))
        print("IMPORT NODES:", len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]))
    except SyntaxError:
        return None

    functions = _extract_functions(tree)
    classes = _extract_classes(tree)
    imports = _extract_imports(tree)
    mutations = _extract_mutations(tree)

    return FileAnalysis(
        file_path=str(path).replace("\\", "/"),
        metadata=FileMetadata(
            line_count=len(source.splitlines()),
            is_hot=False,
            role=None,
        ),

        functions=functions,
        classes=classes,
        imports=imports,
        mutations=mutations,

        behavioral_contracts=[],  # intentionally deferred or simplified
        phase_violations=[],
    )