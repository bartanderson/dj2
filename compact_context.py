#!/usr/bin/env python3
"""
Generate a compact AI context package for a given primary file and its direct imports.
Uses the scout DB to resolve import paths and include the source of imported modules.
"""

import sqlite3
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Set

def load_scout_db(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def get_file_data(conn, file_path: str) -> Dict[str, Any]:
    cur = conn.cursor()
    row = cur.execute("SELECT data FROM files WHERE path = ?", (file_path,)).fetchone()
    if not row:
        return None
    return json.loads(row[0])

def module_to_path(conn, module: str) -> str | None:
    """Convert a module name (e.g., 'world.character') to a relative file path with OS separator."""
    # Use os.path.join to construct path with correct separator
    # Convert module dots to separators
    parts = module.split('.')
    # Try .py
    candidate = os.path.join(*parts) + '.py'
    if get_file_data(conn, candidate):
        return candidate
    # Try package __init__.py
    pkg_candidate = os.path.join(*parts, '__init__.py')
    if get_file_data(conn, pkg_candidate):
        return pkg_candidate
    return None

def collect_imported_files(conn, file_path: str, visited: Set[str] = None) -> Set[str]:
    """Recursively collect all imported files (direct imports only, one level)."""
    if visited is None:
        visited = set()
    data = get_file_data(conn, file_path)
    if not data:
        return set()
    imports = data.get('imports', [])
    result = set()
    for imp in imports:
        if imp.get('type') == 'import':
            for name in imp.get('names', []):
                mod = name['name'].split('.')[0]
                path = module_to_path(conn, mod)
                if path and path not in visited:
                    result.add(path)
                    visited.add(path)
        elif imp.get('module'):
            mod = imp['module'].split('.')[0]
            path = module_to_path(conn, mod)
            if path and path not in visited:
                result.add(path)
                visited.add(path)
    return result

def load_global_rules(project_root: Path) -> Dict[str, str]:
    """Same as in arch_recon.py"""
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

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('primary_file', help='Path to the main file under test (relative to project root)')
    parser.add_argument('--db', default='ai_context/scout.db', help='Path to scout DB')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--intent', default='', help='Intent description (optional)')
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    db_path = project_root / args.db
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}")
        sys.exit(1)

    conn = load_scout_db(db_path)

    # Normalize primary file path to match DB (OS separator)
    primary_file_norm = os.path.normpath(args.primary_file)

    # 1. Verify primary file exists in DB
    primary_data = get_file_data(conn, primary_file_norm)
    if not primary_data:
        print(f"❌ Primary file '{primary_file_norm}' not found in DB.")
        sys.exit(1)

    # 2. Collect direct imports of primary file
    imported_files = collect_imported_files(conn, primary_file_norm)

    # 3. Also include the Character class definition if not already included
    #    (we know it's likely in world/character.py)
    character_file_norm = os.path.normpath('world/character.py')
    if character_file_norm not in imported_files and character_file_norm != primary_file_norm:
        if get_file_data(conn, character_file_norm):
            imported_files.add(character_file_norm)

    # 4. Load global architectural rules
    rules = load_global_rules(project_root)

    # 5. Build context
    lines = []
    lines.append("=" * 80)
    lines.append(f"COMPACT CONTEXT PACKAGE")
    lines.append(f"Intent: {args.intent or '(not specified)'}")
    lines.append(f"Primary file: {primary_file_norm}")
    lines.append("=" * 80)
    lines.append("")

    # Architectural rules (condensed)
    lines.append("## ARCHITECTURAL RULES")
    if rules['ai_contract']:
        lines.append(rules['ai_contract'])
    else:
        lines.append("\n".join(rules['ai_contract_rules']))
    lines.append("")
    lines.append(f"Phase sequence: {rules['phase_sequence']}")
    lines.append("")
    lines.append(rules['role_definitions'])
    lines.append("")

    # Primary file: full source
    lines.append(f"## PRIMARY FILE: {primary_file_norm}")
    primary_full_path = project_root / primary_file_norm
    if primary_full_path.exists():
        lines.append(primary_full_path.read_text(encoding='utf-8'))
    else:
        lines.append(f"⚠️  Primary file not found on disk.")
    lines.append("")

    # Imported files: full source
    if imported_files:
        lines.append("## IMPORTED MODULES (full source)")
        for imp_path in sorted(imported_files):
            full_path = project_root / imp_path
            if full_path.exists():
                lines.append(f"--- {imp_path} ---")
                lines.append(full_path.read_text(encoding='utf-8'))
                lines.append("")
            else:
                lines.append(f"⚠️  Imported file not found: {imp_path}")
    else:
        lines.append("## IMPORTED MODULES")
        lines.append("(No direct imports detected in DB)")

    conn.close()
    print("\n".join(lines))

if __name__ == '__main__':
    main()