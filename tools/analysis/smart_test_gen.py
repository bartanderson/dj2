#!/usr/bin/env python3
"""
Smart test generator using pattern database.
Usage:
    python tools/analysis/smart_test_gen.py "character creation" --output tests/test_character_creation.py --target world/character_builder.py
"""
import sqlite3
import json
import sys
import argparse
from pathlib import Path

# ----------------------------------------------------------------------
# Ensure we can import arch_recon and context_manager
# ----------------------------------------------------------------------
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

scripts_dir = project_root / "scripts"
if scripts_dir.exists() and str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from arch_recon import _get_top_files_for_intent, clean_ai_response
from context_manager import ContextManager

# ----------------------------------------------------------------------
def get_target_file(intent, db_path, categories_path=None, override=None):
    if override:
        return override
    top = _get_top_files_for_intent(intent, db_path, categories_path, max_files=1)
    return top[0][0] if top else None

def get_imports(db_path, source_file):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT DISTINCT imported_module FROM imports WHERE importer_path = ?",
        (source_file,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_patterns(db_path, source_file):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT pattern_type, pattern_data FROM test_patterns WHERE source_file = ?",
        (source_file,)
    ).fetchall()
    conn.close()
    patterns = {'pre_import_mocks': [], 'fixtures': [], 'test_methods': []}
    for typ, data_json in rows:
        data = json.loads(data_json)
        if typ == 'pre_import_mock':
            patterns['pre_import_mocks'].append(data['module'])
        elif typ == 'fixture':
            patterns['fixtures'].append(data)
        elif typ == 'test_method':
            patterns['test_methods'].append(data)
    return patterns

def build_skeleton(target_file, imports, patterns, project_root):
    lines = []
    lines.append("import pytest")
    lines.append("from unittest.mock import Mock, patch, MagicMock")
    lines.append("import sys")
    lines.append("")

    # Pre-import mocks from patterns
    for mod in patterns['pre_import_mocks']:
        lines.append(f"# Mock {mod} before importing the module under test")
        lines.append(f"mock_{mod} = MagicMock()")
        lines.append(f"sys.modules['{mod}'] = mock_{mod}")
    lines.append("")

    # Lock the import of the target module
    mod_path = target_file.replace('/', '.').replace('\\', '.').replace('.py', '')
    lines.append(f"import {mod_path}")
    lines.append(f"# The class under test is CharacterBuilder (adjust if needed)")
    lines.append(f"CharacterBuilder = {mod_path}.CharacterBuilder")
    lines.append("")

    # Fixtures (from patterns or generic)
    if patterns['fixtures']:
        for fix in patterns['fixtures']:
            deps = ', '.join(fix['dependencies'])
            lines.append(f"@pytest.fixture")
            lines.append(f"def {fix['name']}({deps}):")
            lines.append(f"    # TODO: implement fixture")
            lines.append(f"    pass")
            lines.append("")
    else:
        lines.append("@pytest.fixture")
        lines.append("def mock_ai():")
        lines.append("    # TODO: return a configured Mock for the AI dependency")
        lines.append("    pass")
        lines.append("")
        lines.append("@pytest.fixture")
        lines.append("def character_builder(mock_ai):")
        lines.append("    # TODO: instantiate CharacterBuilder with mock_ai and any other mocks")
        lines.append("    pass")
        lines.append("")

    # Test methods (from patterns or generic)
    if patterns['test_methods']:
        for test in patterns['test_methods']:
            fixtures = ', '.join(test.get('fixtures_used', []))
            lines.append(f"def {test['name']}({fixtures}):")
            lines.append(f'    """{test.get("docstring", "TODO")}"""')
            lines.append("    # TODO: implement test (Arrange‑Act‑Assert)")
            lines.append("    pass")
            lines.append("")
    else:
        lines.append("def test_create_character(character_builder, mock_ai):")
        lines.append('    """Test that create_character returns a character with expected attributes."""')
        lines.append("    # TODO: implement test")
        lines.append("    pass")
        lines.append("")

    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intent", help="Feature intent")
    parser.add_argument("--db", default="ai_context/scout.db")
    parser.add_argument("--categories", help="discovered_categories.json")
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--target", required=True, help="Explicit target file (e.g., world/character_builder.py)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print("❌ Scout DB not found.")
        return 1

    target = args.target
    print(f"Target: {target}")

    imports = get_imports(db_path, target)
    patterns = get_patterns(db_path, target)

    skeleton = build_skeleton(target, imports, patterns, Path(args.project_root))

    # Now use AI to fill the TODOs
    mgr = ContextManager()
    prompt = f"""You are a senior test engineer. I have a skeleton test for {target}. Your task is to replace every line containing `# TODO` with actual working code. Do not change any other lines. Preserve the exact structure, imports, and comments. Output only the complete Python file.

Skeleton:
{skeleton}
"""
    package = mgr.build_package(args.intent)
    package['formatted'] = prompt
    success = mgr.send(package, target='deepseek', keep_open=False)
    if not success:
        print("❌ AI generation failed.")
        return 1

    # Get the response
    session_dir = mgr.session_dir
    resp_files = list(session_dir.glob("deepseek_response*.txt"))
    if not resp_files:
        print("❌ No response file.")
        return 1
    latest = max(resp_files, key=lambda p: p.stat().st_mtime)
    response = latest.read_text(encoding='utf-8')

    # Clean and save
    response = clean_ai_response(response)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response, encoding='utf-8')
    print(f"✅ Test written to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())