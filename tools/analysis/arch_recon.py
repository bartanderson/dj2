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

import sys
import argparse
from pathlib import Path

# Add analysis directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import List

from scanner import run_scout
from reporters import (
    report_hot, report_mutations, report_largest, report_concepts,
    report_exporters, report_summary, report_risk_heatmap
)
from intent_matcher import _get_top_files_for_intent

def ensure_db_fresh(db_path: Path, force: bool = False, no_prompt: bool = False,
                    project_root: str = '.', ignore_dirs: List[str] = None, verbose: bool = False):
    """Check if DB exists/prompt to scan. Returns True if ready, False if cancelled."""
    if db_path.exists() and not force:
        # Optional: check age (e.g., older than 1 day)
        age = datetime.now() - datetime.fromtimestamp(db_path.stat().st_mtime)
        if age.days >= 1 and not no_prompt:
            print(f"≡ƒòÆ Scout DB is {age.days} day(s) old.")
            answer = input("Rescan now? (Y/n): ").strip().lower()
            if answer != 'n':
                force = True
        # else proceed
    if not db_path.exists() and not no_prompt:
        print("Γ¥î Scout DB not found.")
        answer = input("Run a full scout scan now? (Y/n): ").strip().lower()
        if answer != 'n':
            force = True
        else:
            return False

    if force:
        print("≡ƒöä Running scout scan...")
        run_scout(project_root, str(db_path), force=True, ignore_dirs=ignore_dirs, verbose=verbose)
    return True
    
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

    # ASK mode
    parser.add_argument('--ask', nargs='?', const='', help='Natural language question (if no argument, interactive)')

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

    # ASK mode
    if args.ask is not None:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=args.no_prompt,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        question = args.ask if args.ask else None
        return ask_mode(args.db, question)

    # Context mode
    if args.context:
        if not args.intent:
            print("❌ --context requires an intent (e.g., --context 'character creation')", file=sys.stderr)
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
            print("❌ --consult requires an intent (e.g., --consult 'character creation')", file=sys.stderr)
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
            print("❌ --test requires an intent...")
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
            print(f"❌ Could not import TestTemplateLibrary: {e}", file=sys.stderr)
            return 1

        lib = TestTemplateLibrary(Path(args.template_dir) if args.template_dir else None)
        template = lib.extract_template_from_file(Path(args.extract_template))
        if template:
            # Name the template after the original file without 'test_' prefix
            name = Path(args.extract_template).stem.replace('test_', '')
            lib.save_template(template, name)
            print(f"✅ Template extracted and saved as '{name}'")
            print(f"   Patterns found: {len(template['patterns']['test_structure'])} tests")
            categories = {e.get('focus', 'general') for e in template.get('example_tests', [])}
            print(f"   Example categories: {categories}")
        else:
            print("⚠️  Failed to extract template.")
        return 0

    # Test update mode
    if args.test_update:
        if not args.test_file or not args.diff:
            print("❌ --test-update requires --test-file and --diff", file=sys.stderr)
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

    # Default: if no intent, and no other action, and not --no-prompt, launch interactive ask mode
    if not args.intent:
        if not args.no_prompt:
            return ask_mode(args.db, question=None)
        else:
            print("No command specified. Use --help for usage.")
            return 0

    # Recon mode (requires intent)
    if not args.categories:
        default_cat = Path(args.db).parent / 'discovered_categories.json'
        if default_cat.exists():
            args.categories = str(default_cat)

    return run_recon(
        intent=args.intent,
        db_path=args.db,
        categories_path=args.categories,
        max_files=args.max_files,
        output_format=args.format,
        verbose=args.verbose
    )
if __name__ == '__main__':
    sys.exit(main())