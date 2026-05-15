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

    print("IMPORT DEBUG:", [(a.asname, a.name) for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names])

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

    runtime_bindings = _extract_runtime_bindings(tree)

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.current_function = "<module>"

        def visit_FunctionDef(self, node):
            previous = self.current_function
            self.current_function = node.name

            self.generic_visit(node)

            self.current_function = previous

        def visit_Call(self, node):
            full = None

            # CASE 1: direct call (foo())
            if isinstance(node.func, ast.Name):
                raw = node.func.id
                base = alias_map.get(raw, runtime_bindings.get(raw, raw))
                full = base

            # CASE 2: attribute call (a.b.c())
            if isinstance(node.func, ast.Attribute):
                base = node.func.value

                # CASE 1: simple name (runtime object or module alias access)
                if isinstance(base, ast.Name):
                    base_name = alias_map.get(base.id)

                    # ONLY resolve if it's a known import alias
                    if base_name is not None:
                        full = f"{base_name}.{node.func.attr}"
                    else:
                        return  # unresolved base name; cannot resolve to import alias

                # CASE 2: chained attributes (a.b.c)
                elif isinstance(base, ast.Attribute):
                    parts = []

                    current = base
                    while isinstance(current, ast.Attribute):
                        parts.append(current.attr)
                        current = current.value

                    if isinstance(current, ast.Name):
                        parts.append(alias_map.get(current.id, current.id))
                        full = ".".join(reversed(parts + [node.func.attr]))
                    else:
                        return
                else:
                    return

            if full:
                references.add((
                    self.current_function,
                    full,
                    node.lineno,
                ))

            self.generic_visit(node)

    Visitor().visit(tree)

    print("ALIAS MAP:", alias_map)

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

def parse_ast(
    file_path: str | Path,
    global_known_symbols: set[str] | None = None,
    runtime_bindings: dict[str, str] | None = None,
    ) -> Optional[FileAnalysis]:

    path = Path(file_path)

    source = _safe_read_file(path)
    if source is None:
        print("PARSE_AST DROP: source is None for", file_path)
        print("PARSE_AST RETURN NONE:", file_path)
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print("PARSE_AST SYNTAX ERROR:", file_path)
        print("  error:", repr(e))
        print("PARSE_AST RETURN NONE:", file_path)
        return None
    except Exception as e:
        print("PARSE_AST UNKNOWN ERROR:", file_path)
        print("  error:", repr(e))
        print("PARSE_AST RETURN NONE:", file_path)
        return None
        runtime_bindings = _extract_runtime_bindings(tree)
        print("DEBUG FILE:", file_path)
        print("SOURCE LENGTH:", len(source))
        print("IMPORT NODES:", len([n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]))
    except SyntaxError:
        print("PARSE_AST RETURN NONE:", file_path)
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

    print("SYMBOL REFERENCES:", len(symbol_references))

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

        runtime_bindings=runtime_bindings,

        behavioral_contracts=[],  # intentionally deferred or simplified
    )


def _extract_runtime_bindings(tree: ast.AST) -> dict[str, str]:
    bindings = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                var_name = node.targets[0].id

                # handle constructor calls
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        bindings[var_name] = node.value.func.id

                    elif isinstance(node.value.func, ast.Attribute):
                        parts = []
                        cur = node.value.func
                        while isinstance(cur, ast.Attribute):
                            parts.append(cur.attr)
                            cur = cur.value
                        if isinstance(cur, ast.Name):
                            parts.append(cur.id)
                            bindings[var_name] = ".".join(reversed(parts))

                # NEW: handle attribute assignments (Flask injection, containers, globals)
                elif isinstance(node.value, ast.Attribute):
                    parts = []
                    cur = node.value

                    while isinstance(cur, ast.Attribute):
                        parts.append(cur.attr)
                        cur = cur.value

                    if isinstance(cur, ast.Name):
                        parts.append(cur.id)
                        resolved = ".".join(reversed(parts))

                        # Flask app injection normalization
                        if resolved == "current_app.world_controller":
                            resolved = "world.world_controller.WorldController"

                        bindings[var_name] = resolved
    return bindings