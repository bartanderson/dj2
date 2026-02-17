#!/usr/bin/env python3
"""
Generate a test for a given intent using full context:
- Target file source
- Sources of its direct imports (resolved via full module paths)
- External packages noted
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
    conn = sqlite3.connect(str(db_path))

    # 1. Find target file
    top_files = _get_top_files_for_intent(args.intent, db_path, None, max_files=1)
    if not top_files:
        print(f"❌ No file found for intent: {args.intent}")
        conn.close()
        return 1
    target_file = top_files[0][0]
    print(f"Target file: {target_file}")

    # 2. Get full module imports
    imports = get_imports_full(db_path, target_file)  # returns list of full module names
    print(f"DEBUG: generate_test imports = {imports}", file=sys.stderr)
    
    # 3. Resolve import paths
    import_paths = []
    external_packages = []
    for full_mod in imports:
        file_path = module_to_file_path(full_mod, project_root)
        if file_path:
            rel_path = str(file_path.relative_to(project_root))
            if rel_path != target_file:  # avoid including the target itself
                import_paths.append(rel_path)
        else:
            external_packages.append(full_mod)
            print(f"ℹ️  External package: {full_mod}", file=sys.stderr)

    # 4. Load architectural rules
    rules = load_global_rules(project_root)

    # 5. Build the context
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

    # Save prompt for debugging - what's sent
    reason_text =  "\n".join(context_parts)
    prompt_file = Path("last_prompt.txt")
    prompt_file.write_text(reason_text, encoding='utf-8')
    print(f"📄 Prompt saved to {prompt_file}")

    # External packages section
    if external_packages:
        context_parts.append("## EXTERNAL PACKAGES (to be mocked)")
        for pkg in external_packages:
            context_parts.append(f"- `{pkg}` – This is an external package (installed via pip). Do not import it directly in the test; instead, mock it completely. The test should patch `{pkg}` at the module level or use `sys.modules` to replace it with a MagicMock.")
        context_parts.append("")

    full_context = "\n".join(context_parts)
    conn.close()

    # Prepend a clear instruction
    instruction = "Your task is to write a **pytest** test file for the CharacterBuilder class. Use the following architectural rules and source code to guide you. Output only the Python code, no explanations, no analysis.\n\n"
    full_context = instruction + full_context

    # 6. Send to DeepSeek
    mgr = ContextManager()
    package = mgr.build_package(args.intent)
    package['formatted'] = full_context
    success = mgr.send(package, target='deepseek', keep_open=False)
    if not success:
        print("❌ DeepSeek call failed.")
        return 1

    # 7. Get the latest response
    session_dir = mgr.session_dir
    resp_files = list(session_dir.glob("deepseek_response*.txt"))
    if not resp_files:
        print("❌ No response file found.")
        return 1
    latest = max(resp_files, key=lambda p: p.stat().st_mtime)
    test_code = latest.read_text(encoding='utf-8')

    # Save raw response (thinking, usually)
    raw_file = Path("last_response_raw.txt")
    raw_file.write_text(test_code, encoding='utf-8')
    print(f"📄 Raw response saved to {raw_file}")

    # 8. Clean (remove markdown) and save
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