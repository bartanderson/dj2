#!/usr/bin/env python3
"""
Dump the full context that would be sent to the AI for test generation.
Improved import resolution: searches the files table for likely matches.
"""
import json
import sys
import argparse
import sqlite3
from pathlib import Path

# Add paths to import our modules
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from intent_matcher import _get_top_files_for_intent
from db_operations import get_imports_full
from utils import module_to_file_path

# ----------------------------------------------------------------------
# Helper: load architectural rules (same as before)
# ----------------------------------------------------------------------
def load_global_rules(project_root: Path) -> dict:
    rules = {
        'ai_contract': None,
        'playbook': None,
        'phase_sequence': 'Input → Interpretation → Authority → Mutation → Consequence → Persistence → View',
        'ai_contract_rules': [
            '1. AI NEVER owns state.',
            '2. AI NEVER mutates state directly.',
            '3. AI ONLY requests actions via interfaces.'
        ],
        'role_definitions': '\n'.join([
            '- Core: default role, no special path',
            '- Adapter: paths containing /routes/',
            '- AI-Facing: paths containing /ai/',
            '- Boundary: files matching dm_chat_ai or ai_boundary'
        ])
    }
    ai_contract = project_root / 'ai_context' / 'ai_contract.md'
    if ai_contract.exists():
        try:
            rules['ai_contract'] = ai_contract.read_text(encoding='utf-8')
        except:
            pass
    playbook = project_root / 'ai_context' / 'development_playbook.md'
    if playbook.exists():
        try:
            rules['playbook'] = playbook.read_text(encoding='utf-8')
        except:
            pass
    return rules

# ----------------------------------------------------------------------
# Helper: read file source
# ----------------------------------------------------------------------
def get_file_source(file_path: str, project_root: Path) -> str:
    full = project_root / file_path
    if full.exists():
        try:
            return full.read_text(encoding='utf-8')
        except Exception as e:
            return f"# Error reading {file_path}: {e}"
    else:
        return f"# File not found: {file_path}"

# ----------------------------------------------------------------------
# Improved import resolution
# ----------------------------------------------------------------------
def find_imported_file(conn, module_name: str, source_dir: str, project_root: Path) -> list:
    """
    Attempt to find the file for a given imported module.
    Returns list of candidate paths (relative to project_root).
    """
    candidates = []

    # If module_name contains dots, it's a dotted import (e.g., world.ai_integration)
    # We don't have that info, so we'll try to guess.

    # 1. Try as a direct file in the source directory
    direct = Path(source_dir) / f"{module_name}.py"
    if direct.exists():
        candidates.append(str(direct.relative_to(project_root)))

    # 2. Try as a file in the project root
    root_file = project_root / f"{module_name}.py"
    if root_file.exists():
        candidates.append(str(root_file.relative_to(project_root)))

    # 3. Try as a package __init__.py in a subdirectory
    pkg_dir = project_root / module_name
    pkg_init = pkg_dir / "__init__.py"
    if pkg_init.exists():
        candidates.append(str(pkg_init.relative_to(project_root)))

    # 4. Query the files table for any path containing the module name as a component
    cur = conn.cursor()
    # Use LIKE to match paths that have the module name as a directory or file stem
    # e.g., '%/world/ai_integration.py' for module 'ai_integration'
    # But we only have top-level module name, so this is a guess.
    rows = cur.execute(
        "SELECT path FROM files WHERE path LIKE ? OR path LIKE ?",
        (f"%/{module_name}.py", f"%/{module_name}/__init__.py")
    ).fetchall()
    for (path,) in rows:
        if path not in candidates:
            candidates.append(path)

    # 5. Also try searching for files where the stem matches the module name (anywhere)
    rows = cur.execute(
        "SELECT path FROM files WHERE path LIKE ?",
        (f"%{module_name}.py",)
    ).fetchall()
    for (path,) in rows:
        if path not in candidates:
            candidates.append(path)

    return candidates

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intent", help="Natural language intent")
    parser.add_argument("--db", default="ai_context/scout.db")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print("❌ Scout DB not found.", file=sys.stderr)
        return 1

    project_root = Path(args.project_root).resolve()
    conn = sqlite3.connect(str(db_path))

    # Find target file
    top_files = _get_top_files_for_intent(args.intent, db_path, None, max_files=1)
    if not top_files:
        print(f"❌ No file found for intent: {args.intent}", file=sys.stderr)
        conn.close()
        return 1
    target_file = top_files[0][0]
    print(f"Target file: {target_file}", file=sys.stderr)

    # Get imports
    imports = get_imports_full(db_path, target_file)  # returns list of module names (top-level)
    print(f"DEBUG: get_imports_full returned: {imports}", file=sys.stderr)
    source_dir = (project_root / target_file).parent

    # Load architectural rules
    rules = load_global_rules(project_root)

    # Build the context
    context_parts = []

    # Architectural rules
    context_parts.append("## ARCHITECTURAL RULES")
    if rules['ai_contract']:
        context_parts.append(rules['ai_contract'])
    else:
        context_parts.append("\n".join(rules['ai_contract_rules']))
        context_parts.append(f"Phase sequence: {rules['phase_sequence']}")
        context_parts.append(rules['role_definitions'])
    if rules['playbook']:
        context_parts.append(rules['playbook'])
    context_parts.append("")

    # Target file source
    context_parts.append(f"## SOURCE: {target_file}")
    context_parts.append("```python")
    context_parts.append(get_file_source(target_file, project_root))
    context_parts.append("```\n")

    # Resolve import paths and build imported files list
    import_paths = []
    external_packages = []
    for mod in imports:
        candidates = find_imported_file(conn, mod, str(source_dir), project_root)
        if candidates:
            for cand in candidates:
                if cand != target_file:
                    import_paths.append(cand)
                    break
        else:
            external_packages.append(mod)
            print(f"ℹ️  External package: {mod}", file=sys.stderr)

    # Imported files (local)
    if import_paths:
        context_parts.append("## DEPENDENCIES (imported modules)")
        for imp_path in import_paths:
            context_parts.append(f"### {imp_path}")
            context_parts.append("```python")
            context_parts.append(get_file_source(imp_path, project_root))
            context_parts.append("```\n")
    else:
        context_parts.append("## DEPENDENCIES\n(No local imports resolved.)\n")

    # External packages section
    if external_packages:
        context_parts.append("## EXTERNAL PACKAGES (to be mocked)")
        for pkg in external_packages:
            context_parts.append(f"- `{pkg}` – This is an external package (installed via pip). Do not import it directly in the test; instead, mock it completely. The test should patch `{pkg}` at the module level or use `sys.modules` to replace it with a MagicMock.")
        context_parts.append("")

    full_context = "\n".join(context_parts)


    return 0

if __name__ == "__main__":
    sys.exit(main())