# tools/analysis/ccss/pass1.py

import ast
from dataclasses import dataclass
from typing import List, Dict, Any
from pathlib import Path

@dataclass
class Symbol:
    symbol_index: int
    symbol_uid: str
    surface: str
    context: str
    line: int


@dataclass
class TestBlock:
    test_name: str
    test_id: str
    start_line: int
    end_line: int
    symbols: List[Symbol]


def _get_test_name(node: ast.FunctionDef) -> str:
    return node.name


def _is_test(fn_name: str) -> bool:
    return fn_name.startswith("test_")

def canonical_file_id(file_path: str) -> str:
    return Path(file_path).resolve().as_posix()

def extract_symbols(node: ast.AST, symbol_start_index: int, test_id: str):
    """
    PURE structural extraction only.
    NO classification, NO semantics.
    """
    symbols = []
    idx = symbol_start_index

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            symbols.append(Symbol(
                symbol_index=idx,
                symbol_uid=f"{idx}",
                surface=child.id,
                context="unknown",
                line=getattr(child, "lineno", -1),
            ))
            idx += 1

        elif isinstance(child, ast.Attribute):
            symbols.append(Symbol(
                symbol_index=idx,
                symbol_uid=f"{idx}",
                surface=child.attr,
                context="attribute",
                line=getattr(child, "lineno", -1),
            ))
            idx += 1

    return symbols, idx


# =========================================================
# FIX: signature now matches run_pipeline
# =========================================================
def run_pass1(file_path: str) -> Dict[str, Any]:
    file_id = canonical_file_id(file_path)

    # PASS1 now owns IO (required for deterministic pipeline execution)
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    tests: List[TestBlock] = []
    symbol_global_index = 0

    for node in ast.walk(tree):

        if isinstance(node, ast.FunctionDef) and _is_test(node.name):

            test_name = _get_test_name(node)
            test_id = f"{test_name}"

            symbols, symbol_global_index = extract_symbols(
                node,
                symbol_global_index,
                test_id
            )

            tests.append(TestBlock(
                test_name=test_name,
                test_id=test_id,
                start_line=getattr(node, "lineno", -1),
                end_line=getattr(node, "end_lineno", -1),
                symbols=symbols
            ))

    return {
        "file_id": file_id,
        "tests": [
            {
                "test_name": t.test_name,
                "test_id": t.test_id,
                "start_line": t.start_line,
                "end_line": t.end_line,
                "symbols": [
                    {
                        "symbol_index": s.symbol_index,
                        "symbol_uid": s.symbol_uid,
                        "surface": s.surface,
                        "context": s.context,
                        "line": s.line
                    }
                    for s in t.symbols
                ]
            }
            for t in tests
        ]
    }