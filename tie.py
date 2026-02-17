#!/usr/bin/env python3
"""
Test import extraction from a file without modifying the DB.
"""
import sys
import ast
from pathlib import Path

# Add tools/analysis to path to import arch_recon
script_dir = Path(__file__).parent
tools_analysis = script_dir / "tools" / "analysis"
if tools_analysis.exists():
    sys.path.insert(0, str(tools_analysis))
else:
    print("❌ Could not find tools/analysis directory.")
    sys.exit(1)

# Try to import the extraction function
try:
    from arch_recon import extract_imports_from_ast
except ImportError as e:
    print(f"❌ Could not import extract_imports_from_ast: {e}")
    # Fallback: define our own simple version
    def extract_imports_from_ast(tree, file_path):
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name.split('.')[0], 'import', node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_base = node.module.split('.')[0]
                    imports.append((module_base, 'from', node.lineno))
        return imports

# Target file
target = Path("world/character_builder.py")
if not target.exists():
    print(f"❌ File not found: {target}")
    sys.exit(1)

print(f"Reading {target}...")
with open(target, 'r', encoding='utf-8') as f:
    source = f.read()

try:
    tree = ast.parse(source)
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

imports = extract_imports_from_ast(tree, str(target))
print(f"\nFound {len(imports)} imports:")
for imp_mod, imp_type, lineno in imports:
    print(f"  {imp_type} {imp_mod} at line {lineno}")

# Also check the file's actual imports by scanning lines (simple grep-like)
print("\nRaw import lines from source:")
for i, line in enumerate(source.splitlines(), 1):
    line = line.strip()
    if line.startswith('import ') or line.startswith('from '):
        print(f"  Line {i}: {line}")