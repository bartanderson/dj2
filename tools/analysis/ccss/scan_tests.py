# tools/analysis/ccss/scan_tests.py

import ast
from pathlib import Path
from typing import List

from tools.analysis.ccss.model import TestSignal
from collections import Counter

BUILTIN_IGNORE = {
    "str",
    "int",
    "float",
    "bool",
    "dict",
    "list",
    "set",
    "tuple",
    "len",
    "isinstance",
    "open",
}

INFRASTRUCTURE_IGNORE = {
    "tmp_path",
    "capsys",
    "f",
}

def filter_candidate_symbols(symbols: list[str]) -> list[str]:
    return sorted(
        {
            s
            for s in symbols
            if s not in BUILTIN_IGNORE
            and s not in INFRASTRUCTURE_IGNORE
        }
    )


def extract_symbols_from_node(node: ast.AST) -> List[str]:
    symbols = []

    for n in ast.walk(node):
        # function calls
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                symbols.append(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                symbols.append(n.func.attr)

        # direct name usage
        elif isinstance(n, ast.Name):
            symbols.append(n.id)

    return list(set(symbols))


def scan_test_file(file_path: Path) -> List[TestSignal]:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    signals = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):

            symbols = extract_symbols_from_node(node)

            raw_symbols = extract_symbols_from_node(node)

            candidate_symbols = filter_candidate_symbols(
                raw_symbols
            )

            signals.append(
                TestSignal(
                    test_name=node.name,
                    file_path=str(file_path),
                    raw_symbols=raw_symbols,
                    candidate_symbols=candidate_symbols,
                )
            )

    return signals