#!/usr/bin/env python3
"""
Generate a test for a given intent using full context:
- Target file source
- Sources of its direct imports
- Architectural rules (AI Contract, Development Playbook)
"""
import json
import sys
import argparse
import sqlite3
import re
from pathlib import Path

# Add paths to import our modules
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
scripts_dir = project_root / "scripts"
if scripts_dir.exists() and str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from intent_matcher import _get_top_files_for_intent
from context_manager import ContextManager
from db_operations import get_imports  # use existing function

# ----------------------------------------------------------------------
# Helper: load architectural rules
# ----------------------------------------------------------------------
def load_global_rules(project_root: Path) -> dict:
    """Load ai_contract.md and development_playbook.md if present."""
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
    """Return the full source of a file, or an error message."""
    full = project_root / file_path
    if full.exists():
        try:
            return full.read_text(encoding='utf-8')
        except Exception as e:
            return f"# Error reading {file_path}: {e}"
    else:
        return f"# File not found: {file_path}"

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intent", help="Natural language intent (e.g., 'character creation')")
    parser.add_argument("--db", default="ai_context/scout.db")
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print("❌ Scout DB not found.")
        return 1

    project_root = Path(args.project_root).resolve()

    # 1. Find target file
    top_files = _get_top_files_for_intent(args.intent, db_path, None, max_files=1)
    if not top_files:
        print(f"❌ No file found for intent: {args.intent}")
        return 1
    target_file = top_files[0][0]
    print(f"Target file: {target_file}")

    # 2. Get imports of target file
    imports = get_imports(db_path, target_file)  # returns list of module names
    # Convert module names to likely file paths (simple heuristic)
    import_paths = []
    for mod in imports:
        # Try as top-level .py file
        candidate = mod.replace('.', '/') + '.py'
        if (project_root / candidate).exists():
            import_paths.append(candidate)
        else:
            # Maybe it's a package? Skip for now.
            pass

    # 3. Load architectural rules
    rules = load_global_rules(project_root)

    # 4. Build the prompt
    prompt_parts = []
    prompt_parts.append("You are a senior test engineer. Write a **pytest** test file for the module described below.\n")
    prompt_parts.append("Use `unittest.mock` to mock **all external dependencies** (AI calls, database, file I/O, network).")
    prompt_parts.append("Do **not** call real systems. Only test the public interfaces shown in the code.")
    prompt_parts.append("Include clear docstrings and follow the Arrange‑Act‑Assert pattern.")
    prompt_parts.append("The test should be self‑contained and run in <0.1s.\n")

    # Architectural rules
    prompt_parts.append("## ARCHITECTURAL RULES")
    if rules['ai_contract']:
        prompt_parts.append(rules['ai_contract'])
    else:
        prompt_parts.append("\n".join(rules['ai_contract_rules']))
        prompt_parts.append(f"Phase sequence: {rules['phase_sequence']}")
        prompt_parts.append(rules['role_definitions'])
    if rules['playbook']:
        prompt_parts.append(rules['playbook'])
    prompt_parts.append("")

    # Target file source
    prompt_parts.append(f"## SOURCE: {target_file}")
    prompt_parts.append("```python")
    prompt_parts.append(get_file_source(target_file, project_root))
    prompt_parts.append("```\n")

    # Imported files
    if import_paths:
        prompt_parts.append("## DEPENDENCIES (imported modules)")
        for imp_path in import_paths:
            prompt_parts.append(f"### {imp_path}")
            prompt_parts.append("```python")
            prompt_parts.append(get_file_source(imp_path, project_root))
            prompt_parts.append("```\n")
    else:
        prompt_parts.append("## DEPENDENCIES\n(No direct imports found or resolved.)\n")

    prompt_parts.append("## INSTRUCTIONS")
    prompt_parts.append("Write a complete pytest test file for the primary class in the source above.")
    prompt_parts.append("Output **only** the Python code, no explanations, no markdown.")

    full_prompt = "\n".join(prompt_parts)

    # 5. Send to DeepSeek
    mgr = ContextManager()
    package = mgr.build_package(args.intent)
    package['formatted'] = full_prompt
    success = mgr.send(package, target='deepseek', keep_open=False)
    if not success:
        print("❌ DeepSeek call failed.")
        return 1

    # 6. Get the latest response
    session_dir = mgr.session_dir
    resp_files = list(session_dir.glob("deepseek_response*.txt"))
    if not resp_files:
        print("❌ No response file found.")
        return 1
    latest = max(resp_files, key=lambda p: p.stat().st_mtime)
    test_code = latest.read_text(encoding='utf-8')

    # 7. Clean (remove markdown) and save
    match = re.search(r"```(?:python)?\n(.*?)\n```", test_code, re.DOTALL)
    if match:
        test_code = match.group(1).strip()
    else:
        test_code = test_code.strip()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(test_code, encoding='utf-8')
    print(f"✅ Test written to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())