# tools/analysis/ingestion/parse_ast.py

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional
from tools.analysis.ingestion.extract_symbols import extract_symbols

from tools.analysis.shared.types import (
    FileAnalysis,
    FileMetadata,
    FunctionRepresentation,
    ClassRepresentation,
    ImportRepresentation,
    SymbolReference,
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


def _extract_imports(
    tree: ast.AST,
) -> tuple[List[ImportRepresentation], dict[str, str]]:
    imports: List[ImportRepresentation] = []
    alias_map: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name

                imports.append(
                    ImportRepresentation(
                        module=module_name,
                        import_type="import",
                        line_number=getattr(node, "lineno", -1),
                    )
                )

                local_name = alias.asname or alias.name.split(".")[-1]
                alias_map[local_name] = module_name

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            imports.append(
                ImportRepresentation(
                    module=module,
                    import_type="from_import",
                    line_number=getattr(node, "lineno", -1),
                )
            )

            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname or imported_name

                canonical_name = (
                    f"{module}.{imported_name}"
                    if module
                    else imported_name
                )

                alias_map[local_name] = canonical_name

    return imports, alias_map


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

def _extract_symbol_references(
    tree: ast.AST,
    known_symbols: set[str],
    alias_map: dict[str, str],
):
    references = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.current_function = "<module>"

        def visit_FunctionDef(self, node):
            previous = self.current_function
            self.current_function = f"{node.name}"

            self.generic_visit(node)

            self.current_function = previous

        def visit_Call(self, node):
            callee = None

            if isinstance(node.func, ast.Name):
                raw_name = node.func.id

                # alias resolution
                callee = alias_map.get(raw_name, raw_name)

            elif isinstance(node.func, ast.Attribute):
                callee = node.func.attr

            if callee:
                # normalize alias resolution first
                resolved = alias_map.get(callee, callee)

                # HARD FILTER: drop known stdlib / external patterns
                if (
                    resolved.startswith("pathlib.")
                    or resolved.startswith("dataclasses.")
                    or resolved.startswith("collections.")
                    or resolved in {"Path", "defaultdict", "field"}
                ):
                    return

                references.add((
                    self.current_function,
                    resolved,
                    node.lineno,
                ))

            self.generic_visit(node)

    Visitor().visit(tree)

    return [
        SymbolReference(caller=a, callee=b, line_number=c)
        for (a, b, c) in references
    ]


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

def parse_ast( file_path: str | Path, global_known_symbols: set[str] | None = None,) -> Optional[FileAnalysis]:
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
    imports, alias_map = _extract_imports(tree)
    known_symbols = global_known_symbols or set()
    symbol_references = _extract_symbol_references(
        tree,
        known_symbols,
        alias_map,
    )
    
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
        symbol_references=symbol_references,

        behavioral_contracts=[],  # intentionally deferred or simplified
        phase_violations=[],
    )