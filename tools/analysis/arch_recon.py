#!/usr/bin/env python3
"""
arch_recon.py – Architecture Reconnaissance + Scout + Recon + Ask + Context + Consult + Test

Modes:
  --scout                     : full project scan → SQLite DB
  <intent>                    : instant intent‑driven report (no truncation)
  --hot / --mutations / etc.  : pre‑canned reports
  --ask                       : interactive menu + free‑form questions
  --context <intent>          : build AI‑ready context package (brief|standard|deep)
  --consult <intent>          : context + send to AI (auto‑routed)
  --test <intent>             : generate pytest file using AI
  --test-update               : update existing test using git diff
  --extract-patterns <file>   : analyze a test file and store patterns in DB
"""

import json
import sqlite3
import io
import contextlib
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any, Dict, Union

from tools.analysis.scanner import run_scout
from tools.analysis.reporters import (
    report_hot, report_mutations, report_largest, report_concepts,
    report_exporters, report_summary, report_risk_heatmap
)
from tools.analysis.intent_matcher import _get_top_files_for_intent
from tools.analysis.utils import clean_ascii

MIN_CONCEPT_LENGTH = 3

def ensure_db_fresh(db_path: Path, force: bool = False, no_prompt: bool = False,
                    project_root: str = '.', ignore_dirs: List[str] = None, verbose: bool = False):
    """Check if DB exists/prompt to scan. Returns True if ready, False if cancelled."""
    if db_path.exists() and not force:
        # Optional: check age (e.g., older than 1 day)
        age = datetime.now() - datetime.fromtimestamp(db_path.stat().st_mtime)
        if age.days >= 1 and not no_prompt:
            print(f"Note: Scout DB is {age.days} day(s) old.")
            answer = input("Rescan now? (Y/n): ").strip().lower()
            if answer != 'n':
                force = True
        # else proceed
    if not db_path.exists() and not no_prompt:
        print("Note: Scout DB not found.")
        answer = input("Run a full scout scan now? (Y/n): ").strip().lower()
        if answer != 'n':
            force = True
        else:
            return False

    if force:
        print("Running forced scout scan to rebuild db...")
        run_scout(project_root, str(db_path), force=True, ignore_dirs=ignore_dirs, verbose=verbose)
    return True
# ----------------------------------------------------------------------
# GLOBAL ARCHITECTURE RULES – loaded from files or embedded
# ----------------------------------------------------------------------
def load_global_rules(project_root: Path) -> Dict[str, str]:
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
    # Try to load from files
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
# CONTEXT PACKAGE GENERATION (tiered, with dynamic phase extraction)
# ----------------------------------------------------------------------
def generate_context_package(intent: str, db_path: Path, categories_path: Optional[str] = None,
                             max_files: int = 5, level: str = 'standard', verbose: bool = False):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    top_files = _get_top_files_for_intent(intent, db_path, categories_path, max_files, verbose)
    if not top_files:
        print(f"⚠️  No files matched intent '{intent}'.", file=sys.stderr)
        return 1
    project_root = Path(db_path).parent.parent
    rules = load_global_rules(project_root)

    summary_data = {}
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        report_summary(str(db_path), 'json')
    try:
        summary_data = json.loads(f.getvalue())
    except:
        summary_data = {"error": "Could not parse summary"}

    lines = []
    lines.append("=" * 80)
    lines.append(f"ARCHITECTURE RECONNAISSANCE – CONTEXT PACKAGE")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Intent: {intent}")
    lines.append(f"Context level: {level}")
    lines.append(f"Max files: {max_files}")
    lines.append("=" * 80)
    lines.append("")

    # Global rules
    lines.append("## GLOBAL ARCHITECTURAL RULES")
    if rules['ai_contract']:
        lines.append(clean_ascii(rules['ai_contract']))
    else:
        lines.append("### AI Contract")
        for rule in rules['ai_contract_rules']:
            lines.append(rule)
        lines.append("")
        lines.append("### Phase Sequence")
        lines.append(rules['phase_sequence'])
        lines.append("")
        lines.append("### Role Definitions")
        lines.append(rules['role_definitions'])
    if rules['playbook']:
        lines.append("")
        lines.append("### Development Playbook")
        lines.append(clean_ascii(rules['playbook']))
    lines.append("")

    # Dynamic phase model
    lines.append("## PHASE MODEL (from engine/phases.py)")
    phases_file = project_root / 'engine' / 'phases.py'
    if phases_file.exists():
        try:
            with open(phases_file, 'r', encoding='utf-8') as f:
                content = f.read()
            import ast
            module = ast.parse(content)
            docstring = ast.get_docstring(module)
            if docstring:
                lines.append(docstring.strip())
            phase_order = []
            for node in ast.walk(module):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'ALL_PHASES':
                            if isinstance(node.value, ast.List):
                                phase_order = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]
                            break
            if phase_order:
                lines.append("**Phase sequence:** " + " → ".join(phase_order))
            else:
                lines.append("**Phase sequence:** Input → Interpretation → Authority → Mutation → Consequence → Persistence → View")
        except Exception as e:
            lines.append(f"*[Could not parse phases.py: {e}]*")
    else:
        lines.append("*[engine/phases.py not found – using fallback]*")
        lines.append("Input → Interpretation → Authority → Mutation → Consequence → Persistence → View")
    lines.append("")

    # Project health summary
    lines.append("## PROJECT HEALTH SUMMARY")
    if "error" not in summary_data:
        lines.append(f"- Python files: {summary_data.get('python_files', '?')}")
        lines.append(f"- Total lines: {summary_data.get('total_lines', 0):,}")
        lines.append(f"- Hot files: {summary_data.get('hot_files', '?')}")
        lines.append(f"- Mutation files: {summary_data.get('mutation_files', '?')}")
        lines.append(f"- Unique concepts: {summary_data.get('unique_concepts', '?')}")
        lines.append(f"- Clusters: {summary_data.get('clusters', '?')}")
    else:
        lines.append(f"- {summary_data.get('error')}")
    lines.append("")

    # Intent‑matched files
    lines.append(f"## INTENT-MATCHED FILES (top {len(top_files)})")
    for idx, (file_path, score, data) in enumerate(top_files, 1):
        lines.append("")
        lines.append("---")
        lines.append(f"### {idx}. `{file_path}` (score: {score})")
        lines.append(f"- **Role**: {data.get('role', 'Unknown')}")
        lines.append(f"- **Hot**: {'Yes' if data.get('is_hot') else 'No'}")
        lines.append(f"- **Line count**: {data.get('line_count', 0)}")
        lines.append(f"- **Phase violations**: {len(data.get('phase_violations', []))}")
        for v in data.get('phase_violations', []):
            lines.append(f"  - line {v.get('line', '?')}: {v.get('pattern', 'unknown')}")
        lines.append(f"- **Mutations**: {len(data.get('mutations', []))}")
        for m in data.get('mutations', []):
            lines.append(f"  - line {m.get('line', '?')}: {m.get('call', '?')}")
        lines.append(f"- **Read-only methods**: {', '.join(data.get('read_only_methods', [])) if data.get('read_only_methods') else 'None'}")
        lines.append(f"- **Importers**: {len(data.get('imported_by', []))} files")
        if data.get('imported_by'):
            lines.append(f"  - {', '.join(Path(p).name for p in data['imported_by'])}")
        lines.append(f"- **Imports**: {len(data.get('imports', []))} modules")

        lines.append("")
        lines.append("#### Interfaces")
        lines.append("```python")
        for cls in data.get('classes', []):
            lines.append(f"class {cls['name']}:")
            for meth in cls.get('methods', []):
                args = ', '.join(meth.get('args', []))
                ret = f" -> {meth['returns']}" if meth.get('returns') else ''
                lines.append(f"    def {meth['name']}({args}){ret}")
            if cls.get('read_only_methods'):
                lines.append(f"    # read-only: {', '.join(cls['read_only_methods'])}")
        for func in data.get('functions', []):
            args = ', '.join(func.get('args', []))
            ret = f" -> {func['returns']}" if func.get('returns') else ''
            lines.append(f"def {func['name']}({args}){ret}")
        lines.append("```")
        lines.append("")

        include_source = False
        if level == 'deep':
            include_source = True
        elif level == 'standard':
            if data.get('is_hot') or idx == 1:
                include_source = True
        if include_source:
            try:
                full_path = project_root / file_path
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        source = f.read()
                    lines_limit = 500 if level == 'deep' else 200
                    source_lines = source.splitlines()
                    if len(source_lines) > lines_limit:
                        source = '\n'.join(source_lines[:lines_limit]) + f"\n... (truncated at {lines_limit} lines)"
                    lines.append("#### Source code")
                    lines.append("```python")
                    lines.append(source)
                    lines.append("```")
                    lines.append("")
            except Exception as e:
                lines.append(f"*[Error reading source: {e}]*")

    lines.append("## RIPPLE IMPACT")
    for file_path, score, data in top_files:
        importers = data.get('imported_by', [])
        if importers:
            lines.append(f"- **{Path(file_path).name}** is imported by {len(importers)} files:")
            lines.append(f"  - {', '.join(Path(p).name for p in importers[:5])}")
            if len(importers) > 5:
                lines.append(f"    ... and {len(importers)-5} more")
        else:
            lines.append(f"- **{Path(file_path).name}** has no direct importers.")
    lines.append("")

    lines.append("## CONCEPTUAL OVERLAP")
    intent_words = set(w for w in intent.lower().split() if len(w) >= MIN_CONCEPT_LENGTH)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    concept_counts = []
    for word in intent_words:
        count = cur.execute("SELECT COUNT(DISTINCT file_path) FROM concepts WHERE concept = ?", (word,)).fetchone()[0]
        if count > 0:
            concept_counts.append((word, count))
    conn.close()
    if concept_counts:
        lines.append("Concepts in your intent and their prevalence:")
        for word, count in sorted(concept_counts, key=lambda x: x[1], reverse=True):
            lines.append(f"- `{word}` appears in {count} files")
    else:
        lines.append("No strong concept overlap found.")
    lines.append("")

    if categories_path and Path(categories_path).exists():
        try:
            with open(categories_path, 'r') as f:
                cat_data = json.load(f)
            clusters = cat_data.get('clusters', [])
            matched_names = set()
            for word in intent_words:
                for cl in clusters:
                    if word in cl.get('concepts', []):
                        matched_names.add(cl['name'])
            if matched_names:
                lines.append("Related clusters (from discovered_categories.json):")
                for name in matched_names:
                    lines.append(f"- {name}")
        except:
            pass

    lines.append("=" * 80)
    print("\n".join(lines))
    return 0
    
def main():
    parser = argparse.ArgumentParser(
    description='Architecture Reconnaissance – Scout + Recon + Ask + Context + Consult + Test',
    epilog='Examples:\n'
    ' arch_recon.py --scout\n'
    ' arch_recon.py "character creation"\n'
    ' arch_recon.py --context "movement" --context-level deep\n'
    ' arch_recon.py --consult "session persistence" --target deepseek\n'
    ' arch_recon.py --test "tool_system" --output tests/test_tool_system.py\n'
    ' arch_recon.py --test-update --test-file tests/test_character_builder.py --diff HEAD~1\n'
    ' arch_recon.py --extract-patterns tests/test_character_builder.py'
    )
    parser.add_argument('intent', nargs='?', help='Natural language intent (required for recon/context/consult/test)')
    parser.add_argument('--scout', action='store_true', help='Run scout (full project scan)')
    parser.add_argument('--db', default='ai_context/scout.db', help='SQLite DB path (default: ai_context/scout.db)')
    parser.add_argument('--categories', '-c', help='Path to discovered_categories.json (for intent parsing)')
    parser.add_argument('--project-root', '-r', default='.', help='Project root directory (for scout/consult/test)')
    parser.add_argument('--max-files', '-m', type=int, default=5, help='Max files in recon report or context')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text', help='Output format (recon/report modes)')
    parser.add_argument('--force', action='store_true', help='Force rescan (with --scout)')
    parser.add_argument('--ignore-dirs', '-i', nargs='+',
    default=['pycache', 'venv', '.git', 'node_modules', 'Lib', 'docs', 'archive'],
    help='Directories to ignore (scout only)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')


    # Report modes
    parser.add_argument('--hot', action='store_true', help='List all hot files')
    parser.add_argument('--mutations', action='store_true', help='List files with direct state mutations')
    parser.add_argument('--largest', action='store_true', help='Show largest files by line count')
    parser.add_argument('--concepts', action='store_true', help='Show most frequent concepts')
    parser.add_argument('--exporters', action='store_true', help='Show most imported files')
    parser.add_argument('--summary', action='store_true', help='Show project summary statistics')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Limit for report modes')

    # Context mode
    parser.add_argument('--context', action='store_true', help='Generate AI‑ready context package (requires intent)')
    parser.add_argument('--context-level', choices=['brief', 'standard', 'deep'], default='standard',
                        help='Detail level for context package (default: standard)')

    # Consult mode
    parser.add_argument('--consult', action='store_true', help='Generate context and send to AI (requires intent)')
    parser.add_argument('--target', choices=['auto', 'ollama', 'deepseek'], default='auto',
                        help='AI backend for consult mode (default: auto)')
    parser.add_argument('--save-session', action='store_true', help='Save the consultation session (context + response)')
    parser.add_argument('--keep-open', '-k', action='store_true', help='Leave DeepSeek browser open')

    # Test generation mode
    parser.add_argument('--test', action='store_true', help='Generate a pytest file for the given intent (requires --output or will auto‑name)')
    parser.add_argument('--test-update', action='store_true', help='Update an existing test based on git diff (requires --test-file and --diff)')
    parser.add_argument('--diff', help='Git revision range (e.g., HEAD~1) for test update')
    parser.add_argument('--test-file', help='Path to existing test file to update')
    parser.add_argument('--output', '-o', help='Output file path for generated test (default: tests/test_<intent>.py)')

    # Pattern extraction
    parser.add_argument('--extract-patterns', metavar='TEST_FILE',
                        help='Extract test patterns from an existing test file and store in DB')

    # Other options
    parser.add_argument('--risk-heatmap', action='store_true', help='Show risk-ranked files')
    parser.add_argument('--min-priority', default='MEDIUM', choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'])
    parser.add_argument('--include-tools', action='store_true', 
                    help='Include tools/ and Scripts/ folders in analysis (default: excluded)')
    parser.add_argument('--layer', action='append', choices=['world', 'dungeon_neo', 'engine', 'ai', 'tools', 'scripts'],
                    help='Filter by layer (can be used multiple times)')
    parser.add_argument('--no-prompt', action='store_true',
                    help='Skip all interactive prompts (DB rescan and default interactive menu). Use for scripting.')
    parser.add_argument('--extract-template', metavar='TEST_FILE',
                    help='Extract test patterns from an existing test file and save as template (legacy)')
    parser.add_argument('--test-with-template', action='store_true',
                        help='Use template library for test generation (requires --test)')
    parser.add_argument('--template-dir', default=None,
                        help='Directory where templates are stored (default: tools/analysis/templates)')

    args = parser.parse_args()

    # Handle pattern extraction (new)
    if args.extract_patterns:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return extract_test_patterns(args.extract_patterns, Path(args.db), Path(args.project_root).resolve())

    # Scout mode
    if args.scout:
        run_scout(
            project_root=args.project_root,
            db_path=args.db,
            force=args.force,
            ignore_dirs=args.ignore_dirs,
            verbose=args.verbose
        )
        return 0

    # Report modes
    if args.hot:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_hot(args.db, args.limit, args.format)
    if args.mutations:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_mutations(args.db, args.limit, args.format)
    if args.largest:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_largest(args.db, args.limit, args.format)
    if args.concepts:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_concepts(args.db, args.limit, args.format)
    if args.exporters:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_exporters(args.db, args.limit, args.format)
    if args.summary:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_summary(args.db, args.format)

    # Context mode
    if args.context:
        if not args.intent:
            print("[Error] --context requires an intent (e.g., --context 'character creation')", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return generate_context_package(
            intent=args.intent,
            db_path=Path(args.db),
            categories_path=args.categories,
            max_files=args.max_files,
            level=args.context_level,
            verbose=args.verbose
        )

    # Consult mode
    if args.consult:
        if not args.intent:
            print("[Error] --consult requires an intent (e.g., --consult 'character creation')", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
        return consult_mode(
            intent=args.intent,
            db_path=Path(args.db),
            project_root=project_root,
            categories_path=args.categories,
            max_files=args.max_files,
            level=args.context_level,
            target=args.target,
            save_session=args.save_session,
            keep_open=args.keep_open,
            verbose=args.verbose
        )

    # Test generation mode
    if args.test:
        if not args.intent:
            print("[Error] --test requires an intent...")
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
        if not args.template_dir:
            args.template_dir = Path(__file__).parent / 'templates'
        return generate_test(
            intent=args.intent,
            db_path=Path(args.db),
            categories_path=args.categories,
            project_root=project_root,
            output_file=args.output,
            use_template=args.test_with_template,
            template_dir=args.template_dir,
            verbose=args.verbose
        )

    if args.risk_heatmap:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_risk_heatmap(args.db, args.min_priority, args.format,
                                   args.include_tools, args.layer)

    if args.extract_template:
        try:
            from tools.analysis.test_templates import TestTemplateLibrary
        except ImportError as e:
            print(f"[Error] Could not import TestTemplateLibrary: {e}", file=sys.stderr)
            return 1

        lib = TestTemplateLibrary(Path(args.template_dir) if args.template_dir else None)
        template = lib.extract_template_from_file(Path(args.extract_template))
        if template:
            # Name the template after the original file without 'test_' prefix
            name = Path(args.extract_template).stem.replace('test_', '')
            lib.save_template(template, name)
            print(f"[Ok] Template extracted and saved as '{name}'")
            print(f"   Patterns found: {len(template['patterns']['test_structure'])} tests")
            categories = {e.get('focus', 'general') for e in template.get('example_tests', [])}
            print(f"   Example categories: {categories}")
        else:
            print("[Warn]  Failed to extract template.")
        return 0

    # Test update mode
    if args.test_update:
        if not args.test_file or not args.diff:
            print("[Error] --test-update requires --test-file and --diff", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
        return update_test(
            test_file=args.test_file,
            diff_range=args.diff,
            db_path=Path(args.db),
            categories_path=args.categories,
            project_root=project_root,
            verbose=args.verbose
        )

    if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                           project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                           verbose=args.verbose):
        return 1

    # Default: if no intent, and no other action, and not --no-prompt, print mesasge
    if not args.intent and not args.force:
        if not args.no_prompt:
            print("No command specified. Use --help for usage.")
            return 0
        else:
            # already handled
            print("No command specified. Use --help for usage.")
            return 0

if __name__ == '__main__':
    sys.exit(main())