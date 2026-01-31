#tools/ai_assistant/cli.py
#!/usr/bin/env python3
"""
AI Assistant CLI - Unified interface for code analysis
Simplified version without backup functionality
"""
import sys
import codecs

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

def setup_subparsers():
    """Setup argparse with subparsers for each command"""
    parser = argparse.ArgumentParser(
        description="AI Assistant CLI - Code analysis and orchestration (Direct edits - use --dry-run)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\n
Examples:
  python ai.py index                            # Update the Whoosh index
  python ai.py search "phase violation"         # Search for phase violations
  python ai.py analyze "DMChatHandler"          # Analyze a component
  python ai.py violations .                     # Find phase boundary violations
  python ai.py delete --file path.py --start 10 --end 20  # Delete lines (direct)
  python ai.py bridge-status                    # Check AI Bridge status
  python ai.py archive-index                    # Index archive/legacy code
  python ai.py archive-search "old function"    # Search only archive
  python ai.py combined-search "GameEngine"     # Search both current and archive
        """
    )
    
    parser.add_argument(
        '--index-dir', 
        default='.whoosh_index', 
        help='Whoosh index directory'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Verbose output'
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        description='Available commands',
        help='Command to execute'
    )
    
    # Index command
    index_parser = subparsers.add_parser('index', help='Create/update Whoosh index')
    index_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    index_parser.set_defaults(func=index_command)
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search the codebase')
    search_parser.add_argument('query', nargs='?', help='Search query (optional)')
    search_parser.add_argument('--path', '-p', help='File path to examine')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='Result limit')
    search_parser.add_argument('--file-type', help='Filter by file type (comma-separated)')
    search_parser.add_argument('--group', '-g', 
                                help='Filter by file group: code, docs, config, ui, python, markdown, json, yaml, text, all')
    search_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    search_parser.set_defaults(func=search_command)
    
    # Context command
    context_parser = subparsers.add_parser('context', help='Build context for DeepSeek')
    context_parser.add_argument('query', nargs='?', help='Analysis query (optional)')
    context_parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    context_parser.add_argument('--output', '-o', help='Output file path')
    context_parser.set_defaults(func=context_command)
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a DeepSeek response')
    validate_parser.add_argument('--response-file', help='File containing DeepSeek response')
    validate_parser.add_argument('--response-text', help='Direct response text')
    validate_parser.add_argument('--output', '-o', help='Output file for validation report')
    validate_parser.set_defaults(func=validate_command)
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a topic')
    analyze_parser.add_argument('query', nargs='?', help='Analysis topic (optional)')
    analyze_parser.add_argument('--deep', action='store_true', help='Run deep analysis with llama3.2')
    analyze_parser.add_argument('--detail', action='store_true', help='Show detailed analysis')
    analyze_parser.set_defaults(func=analyze_command)
    
    # Guardrails command
    guardrails_parser = subparsers.add_parser('guardrails', help='Show and validate guardrails')
    guardrails_parser.add_argument('--list', action='store_true', help='List available guardrails')
    guardrails_parser.add_argument('--summary', action='store_true', help='Show summary only')
    guardrails_parser.add_argument('--limit', type=int, default=1000, help='Character limit for output')
    guardrails_parser.set_defaults(func=guardrails_command)
    
    # Phase-check command
    phase_parser = subparsers.add_parser('phase-check', help='Check phase compliance')
    phase_parser.add_argument('--patterns', help='Comma-separated patterns to check')
    phase_parser.add_argument('--limit', type=int, default=10, help='Result limit')
    phase_parser.set_defaults(func=phase_check_command)
    
    # Analysis commands from old cli.py
    violations_parser = subparsers.add_parser('violations', help='Find phase boundary violations')
    violations_parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    violations_parser.set_defaults(func=violations_command)
    
    todos_parser = subparsers.add_parser('todos', help='Find TODOs and FIXMEs')
    todos_parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    todos_parser.set_defaults(func=todos_command)
    
    deps_parser = subparsers.add_parser('deps', help='Show dependency analysis')
    deps_parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    deps_parser.set_defaults(func=deps_command)
    
    structure_parser = subparsers.add_parser('structure', help='Show project structure')
    structure_parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    structure_parser.set_defaults(func=structure_command)
    
    # Architecture commands
    refactor_plan_parser = subparsers.add_parser('refactor-plan', help='Generate refactoring plan')
    refactor_plan_parser.set_defaults(func=refactor_plan_command)
    
    js_css_check_parser = subparsers.add_parser('js-css-check', help='Check JS/CSS separation')
    js_css_check_parser.set_defaults(func=js_css_check_command)
    
    analyze_project_parser = subparsers.add_parser('analyze-project', help='Complete project analysis')
    analyze_project_parser.set_defaults(func=analyze_project_command)
    
    # Workflow commands
    feature_report_parser = subparsers.add_parser('feature-report', help='Generate dynamic feature report')
    feature_report_parser.set_defaults(func=feature_report_command)
    
    living_workflow_parser = subparsers.add_parser('living-workflow', help='Run complete living system workflow')
    living_workflow_parser.set_defaults(func=living_workflow_command)
    
    # Bridge commands
    bridge_status_parser = subparsers.add_parser('bridge-status', help='Check AI Bridge status')
    bridge_status_parser.set_defaults(func=bridge_status_command)
    
    # File editing commands (direct, no backup)
    delete_parser = subparsers.add_parser('delete', help='Delete lines from file (direct)')
    delete_parser.add_argument('--file', required=True, help='File to edit')
    delete_parser.add_argument('--start', type=int, required=True, help='Start line')
    delete_parser.add_argument('--end', type=int, required=True, help='End line')
    delete_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    delete_parser.set_defaults(func=delete_command)
    
    insert_parser = subparsers.add_parser('insert', help='Insert lines into file (direct)')
    insert_parser.add_argument('--file', required=True, help='File to edit')
    insert_parser.add_argument('--line', type=int, required=True, help='Line number to insert at')
    insert_parser.add_argument('--text', required=True, help='Text to insert (use \\n for newlines)')
    insert_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    insert_parser.set_defaults(func=insert_command)
    
    replace_parser = subparsers.add_parser('replace', help='Replace lines in file (direct)')
    replace_parser.add_argument('--file', required=True, help='File to edit')
    replace_parser.add_argument('--start', type=int, required=True, help='Start line')
    replace_parser.add_argument('--end', type=int, required=True, help='End line')
    replace_parser.add_argument('--text', required=True, help='Replacement text (use \\n for newlines)')
    replace_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    replace_parser.set_defaults(func=replace_command)
    
    write_parser = subparsers.add_parser('write', help='Write or overwrite file (direct)')
    write_parser.add_argument('--file', required=True, help='File to write')
    write_parser.add_argument('--text', required=True, help='File content (use \\n for newlines)')
    write_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    write_parser.set_defaults(func=write_command)
    
    replace_text_parser = subparsers.add_parser('replace-text', help='Replace text in file (direct)')
    replace_text_parser.add_argument('--file', required=True, help='File to edit')
    replace_text_parser.add_argument('--search', required=True, help='Text to search for')
    replace_text_parser.add_argument('--replace', required=True, help='Replacement text')
    replace_text_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    replace_text_parser.set_defaults(func=replace_text_command)
    
    extract_class_parser = subparsers.add_parser('extract-class', help='Extract class to new file (direct)')
    extract_class_parser.add_argument('--source', required=True, help='Source file')
    extract_class_parser.add_argument('--class', dest='class_name', required=True, help='Class name')
    extract_class_parser.add_argument('--target', help='Target file (default: classname.py)')
    extract_class_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    extract_class_parser.set_defaults(func=extract_class_command)
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract component for refactoring analysis')
    extract_parser.add_argument('--component', required=True, help='Component to extract')
    extract_parser.add_argument('--output', '-o', help='Output file for extraction data')
    extract_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    extract_parser.set_defaults(func=extract_command)
    
    # Extract lines command (direct)
    extract_lines_parser = subparsers.add_parser('extract-lines', help='Extract lines to new file (direct)')
    extract_lines_parser.add_argument('--source', required=True, help='Source file')
    extract_lines_parser.add_argument('--start', type=int, required=True, help='Start line (1-indexed)')
    extract_lines_parser.add_argument('--end', type=int, required=True, help='End line (1-indexed)')
    extract_lines_parser.add_argument('--target', required=True, help='Target file')
    extract_lines_parser.add_argument('--dry-run', action='store_true', help='Show what would change')
    extract_lines_parser.set_defaults(func=extract_lines_command)
    
    # Find class command
    find_class_parser = subparsers.add_parser('find-class', help='Find class definition lines')
    find_class_parser.add_argument('file', help='File to search')
    find_class_parser.add_argument('class_name', help='Class name to find')
    find_class_parser.set_defaults(func=find_class_command)
    
    # Help command
    help_parser = subparsers.add_parser('help', help='Show help')
    help_parser.set_defaults(func=lambda args: parser.print_help())

    # Archive indexing command
    archive_index_parser = subparsers.add_parser('archive-index', 
                                                 help='Index archive/legacy code separately')
    archive_index_parser.add_argument('--index-dir', 
                                     default='.archive_index', 
                                     help='Archive index directory')
    archive_index_parser.add_argument('--verbose', '-v', action='store_true', 
                                     help='Verbose output')
    archive_index_parser.set_defaults(func=archive_index_command)

    # Archive search command
    archive_search_parser = subparsers.add_parser('archive-search', 
                                                 help='Search archive index only')
    archive_search_parser.add_argument('query', nargs='?', help='Search query (optional)')
    archive_search_parser.add_argument('--limit', '-l', type=int, default=10, 
                                      help='Result limit')
    archive_search_parser.add_argument('--verbose', '-v', action='store_true', 
                                      help='Verbose output')
    archive_search_parser.set_defaults(func=archive_search_command)

    # Combined search command (main + archive)
    combined_search_parser = subparsers.add_parser('combined-search',
                                                  help='Search both main and archive indexes')
    combined_search_parser.add_argument('query', help='Search query')
    combined_search_parser.add_argument('--limit', '-l', type=int, default=10,
                                       help='Result limit (per index)')
    combined_search_parser.add_argument('--verbose', '-v', action='store_true',
                                       help='Verbose output')
    combined_search_parser.set_defaults(func=combined_search_command)
    
    return parser

# Command implementations
from .archive_indexer import ArchiveIndexer

def archive_index_command(args):
    """Index archive/legacy code separately"""
    indexer = ArchiveIndexer(index_dir=args.index_dir)
    
    if args.verbose:
        print("Starting archive index creation/update...")
    
    indexer.create_or_update_index()
    
    # Print summary
    with indexer.index.searcher() as searcher:
        print(f"✓ Archive index updated. Total archive documents: {searcher.doc_count()}")
        
        if args.verbose:
            # Count by type
            types = {}
            for doc in searcher.documents():
                file_type = doc.get('file_type', 'unknown')
                types[file_type] = types.get(file_type, 0) + 1
            
            print("\nArchive document types:")
            for file_type, count in sorted(types.items()):
                print(f"  {file_type}: {count}")
    
    return 0

def archive_search_command(args):
    """Search only the archive index"""
    from .indexer import CodebaseIndexer
    from .archive_indexer import ArchiveIndexer
    from .config import AIConfig
    
    indexer = ArchiveIndexer(index_dir='.archive_index')
    
    # If no query provided, prompt
    if not args.query and not args.path:
        args.query = input("Enter search query for archive: ")
    
    # Build query parameters
    search_params = {
        "limit": args.limit,
    }
    
    if args.query:
        results = indexer.search(args.query, **search_params)
        
        if not results:
            print("No results found in archive.")
            return 0
        
        print(f"\nFound {len(results)} results in archive for: {args.query}")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['path']} [ARCHIVE] (score: {result['score']:.3f})")
            if args.verbose:
                print(f"   Type: {result['file_type']}")
                print(f"   Preview: {result['content_preview'][:200]}...")
    
    return 0

def combined_search_command(args):
    """Search both main and archive indexes"""
    from .indexer import CodebaseIndexer
    from .archive_indexer import ArchiveIndexer
    main_indexer = CodebaseIndexer(index_dir='.whoosh_index')
    archive_indexer = ArchiveIndexer(index_dir='.archive_index')
    
    print(f"Searching both indexes for: {args.query}")
    print("=" * 80)
    
    # Search main index
    print("\n=== MAIN CODEBASE RESULTS ===")
    main_results = main_indexer.search(args.query, limit=args.limit)
    
    if main_results:
        for i, result in enumerate(main_results[:args.limit], 1):
            archive_flag = " [ARCHIVE]" if result.get('is_archive') else ""
            print(f"\n{i}. {result['path']}{archive_flag}")
            print(f"   Score: {result['score']:.3f}")
            if args.verbose:
                print(f"   Type: {result['file_type']}")
    else:
        print("  No results in main codebase")
    
    # Search archive index
    print("\n=== ARCHIVE RESULTS ===")
    archive_results = archive_indexer.search(args.query, limit=args.limit)
    
    if archive_results:
        for i, result in enumerate(archive_results[:args.limit], 1):
            print(f"\n{i}. {result['path']} [ARCHIVE]")
            print(f"   Score: {result['score']:.3f}")
            if args.verbose:
                print(f"   Type: {result['file_type']}")
    else:
        print("  No results in archive")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Main codebase: {len(main_results)} results")
    print(f"Archive: {len(archive_results)} results")
    print(f"Total: {len(main_results) + len(archive_results)} results")
    
    return 0

def index_command(args):
    """Create or update the Whoosh index"""
    from .indexer import CodebaseIndexer
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    if args.verbose:
        print("Starting index creation/update...")
    
    indexer.create_or_update_index()
    
    # Print summary
    with indexer.index.searcher() as searcher:
        print(f"✓ Index updated. Total documents: {searcher.doc_count()}")
        
        if args.verbose:
            # Count by type
            types = {}
            for doc in searcher.documents():
                file_type = doc.get('file_type', 'unknown')
                types[file_type] = types.get(file_type, 0) + 1
            
            print("\nDocument types:")
            for file_type, count in sorted(types.items()):
                print(f"  {file_type}: {count}")
    
    return 0

def search_command(args):
    """Search the codebase"""
    from .indexer import CodebaseIndexer
    from .config import AIConfig
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    # If no query provided, prompt
    if not args.query and not args.path:
        args.query = input("Enter search query: ")
    
    # Build query parameters
    search_params = {
        "limit": args.limit,
    }
    
    # Handle file type filter - prioritize group over file-type
    if args.group:
        # Convert group to file extensions
        group_name = args.group.lower()
        if AIConfig.is_valid_group(group_name):
            extensions = AIConfig.get_file_extensions_for_group(group_name)
            if extensions:  # Not empty set
                # Convert to Whoosh format (without dot)
                file_types = [ext.lstrip('.') for ext in extensions]
                search_params["file_types"] = file_types
                print(f"Filtering by group '{group_name}': {', '.join(sorted(extensions))}")
            else:
                # 'all' group - no filtering
                print("Searching all file types")
        else:
            print(f"Warning: Unknown group '{group_name}'. Available: {', '.join(AIConfig.FILE_TYPE_GROUPS.keys())}")
            print("Falling back to all file types.")
    
    elif args.file_type:
        # Strip dots from each file type for consistency
        file_types = [ft.strip().lstrip('.') for ft in args.file_type.split(',')]
        search_params["file_types"] = file_types
        if args.verbose:
            print(f"Filtering by file types: {', '.join(file_types)}")
        
    # Handle path filter
    if args.path:
        # Convert Windows path to normalized form for indexing
        path_str = args.path.replace('/', '\\')
        search_params["path_filter"] = path_str
    
    if args.query:
        results = indexer.search(args.query, **search_params)
        
        if not results:
            print("No results found.")
            return 0
        
        print(f"\nFound {len(results)} results for: {args.query}")
        if args.path:
            print(f"Filtered to path: {args.path}")
        if args.group:
            print(f"Filtered to group: {args.group}")
        elif args.file_type:
            print(f"Filtered to file types: {args.file_type}")
        print("-" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['path']} (score: {result['score']:.3f})")
            if args.verbose:
                print(f"   Type: {result['file_type']}")
                if result['phase_tags']:
                    print(f"   Phase tags: {', '.join(result['phase_tags'])}")
                print(f"   Preview: {result['content_preview'][:200]}...")
    
    elif args.path:
        # Show file details (existing behavior)
        from whoosh.qparser import QueryParser
        
        if not indexer.index:
            indexer.index = indexer.index.open_dir(str(args.index_dir))

        # Normalize path for lookup - FIXED
        path_str = args.path.replace('/', '\\')
        
        with indexer.index.searcher() as searcher:
            doc = searcher.document(path=path_str)
            if doc:
                print(f"\nFile: {args.path}")
                print(f"Type: {doc.get('file_type', 'unknown')}")
                print(f"Last modified: {doc.get('last_modified', 'unknown')}")
                print(f"Phase tags: {doc.get('phase_tags', '')}")
                print(f"System tags: {doc.get('system_tags', '')}")
                
                # Show AST info if available
                ast_info = doc.get('ast_info')
                if ast_info:
                    try:
                        ast_data = json.loads(ast_info)
                        if ast_data.get('imports'):
                            print(f"\nImports: {', '.join(ast_data['imports'][:10])}")
                        if ast_data.get('classes'):
                            print(f"Classes: {', '.join(ast_data['classes'][:10])}")
                    except:
                        pass
                
                # Show related files
                related = indexer.get_related_files(args.path)
                if related:
                    print(f"\nRelated files ({len(related)}):")
                    for rel in related[:5]:
                        print(f"  - {rel['path']} ({rel['relation']})")
            else:
                print(f"File not indexed: {args.path}")
    
    return 0

def context_command(args):
    """Build context for DeepSeek analysis"""
    from .indexer import CodebaseIndexer
    from .context_builder import BridgeAgent
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # If query provided via args, use it
    query = args.query
    if not query and args.interactive:
        print("Enter your analysis query (Ctrl+D to finish, blank line to end):")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        query = "\n".join(lines)
    elif not query:
        query = input("Enter analysis query: ")
    
    if not query or query.strip() == "":
        print("No query provided.")
        return 1
    
    print(f"\nBuilding context for query: {query[:100]}...")
    print("=" * 80)
    
    context = agent.build_context_for_query(query)
    
    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(exist_ok=True)
        
        # Save full context as JSON
        with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, default=str)
        
        # Save formatted context as text
        with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            f.write(format_context_for_deepseek(context))
        
        print(f"\n✓ Context saved to:")
        print(f"  - {output_path.with_suffix('.json')} (full data)")
        print(f"  - {output_path.with_suffix('.txt')} (formatted for DeepSeek)")
    
    # Print formatted context
    print(format_context_for_deepseek(context))
    
    return 0

def format_context_for_deepseek(context: Dict) -> str:
    """Format context for DeepSeek query"""
    output = []
    output.append("=" * 80)
    output.append("DEEPSEEK ANALYSIS CONTEXT")
    output.append("=" * 80)
    output.append(f"\nQuery: {context['query']}")
    
    structured = context.get('structured_context', {})
    
    if structured.get('key_insights'):
        output.append("\nKEY INSIGHTS:")
        output.append(structured['key_insights'])
    
    if structured.get('relevant_files'):
        output.append("\nRELEVANT FILES:")
        for file in structured['relevant_files'][:10]:
            output.append(f"  - {file}")
    
    if structured.get('phase_warnings'):
        output.append("\nPHASE COMPLIANCE WARNINGS:")
        for warning in structured['phase_warnings'][:5]:
            output.append(f"  • {warning}")
    
    # Add actual code snippets
    if context.get('whoosh_results'):
        output.append("\nCODE SNIPPETS:")
        for i, result in enumerate(context['whoosh_results'][:5], 1):
            output.append(f"\n--- {result['path']} ---")
            preview = result.get('content_preview', '')
            if preview:
                output.append(preview[:300] + "..." if len(preview) > 300 else preview)
    
    # Add guardrail reminders
    output.append("\n" + "=" * 80)
    output.append("GUARDRAIL REMINDERS:")
    output.append("1. Check phase compliance (AI never mutates state)")
    output.append("2. Maintain system ownership boundaries")
    output.append("3. Preserve backward compatibility")
    output.append("4. Use git for version control")
    output.append("=" * 80)
    
    return "\n".join(output)

def validate_command(args):
    """Validate a DeepSeek response"""
    from .indexer import CodebaseIndexer
    from .context_builder import BridgeAgent
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # Read response
    if args.response_file:
        with open(args.response_file, 'r', encoding='utf-8') as f:
            response = f.read()
    elif args.response_text:
        response = args.response_text
    else:
        print("Paste DeepSeek response (Ctrl+D to finish, blank line to end):")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        response = "\n".join(lines)
    
    if not response.strip():
        print("No response provided.")
        return 1
    
    # Create minimal context
    context = {
        "query": "Validation only",
        "structured_context": {
            "relevant_files": [],
            "key_insights": "Validating DeepSeek response against project rules"
        }
    }
    
    print("\nValidating DeepSeek response...")
    validation = agent.validate_deepseek_response(response, context)
    
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    
    if validation.get('is_valid', True):
        print("✅ Response is VALID")
    else:
        print("❌ Response has ISSUES")
    
    if validation.get('issues'):
        print("\nISSUES FOUND:")
        for i, issue in enumerate(validation['issues'], 1):
            print(f"  {i}. {issue}")
    
    if validation.get('suggested_fixes'):
        print("\nSUGGESTED FIXES:")
        for i, fix in enumerate(validation.get('suggested_fixes', []), 1):
            print(f"  {i}. {fix}")
    
    phase_check = validation.get('phase_compliance_check', 'unknown')
    print(f"\nPHASE COMPLIANCE: {phase_check.upper()}")
    
    if phase_check == 'fail':
        print("  ⚠️  This change may violate phase boundaries!")
    elif phase_check == 'needs_review':
        print("  ⚠️  Manual review required for phase compliance")
    
    # Save validation report
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(validation, f, indent=2)
        print(f"\n✓ Validation report saved to: {args.output}")
    
    return 0 if validation.get('is_valid', True) else 1

def analyze_command(args):
    """Run comprehensive analysis on a topic"""
    from .indexer import CodebaseIndexer
    from .context_builder import BridgeAgent
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # Build context
    query = args.query
    if not query:
        query = input("Enter analysis topic: ")
    
    print(f"\nAnalyzing: {query}")
    print("=" * 80)
    
    context = agent.build_context_for_query(query)
    
    # Get phase violations from the indexer (for summary)
    phase_context = indexer.get_phase_violation_context()
    
    # Get related files
    whoosh_results = context['whoosh_results']
    
    # Print analysis
    print("\nANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Topic: {query}")
    
    # System boundaries affected
    systems = set()
    for result in whoosh_results:
        for tag in result.get('system_tags', []):
            systems.add(tag.replace('system:', ''))
    
    if systems:
        print(f"\nAffected systems: {', '.join(sorted(systems))}")
    
    # Get ACTUAL phase violations with code using ASTAnalyzer
    print("\nScanning for phase violations in code...")
    import sys
    from pathlib import Path
    
    # Import ASTAnalyzer
    analysis_dir = Path(__file__).parent.parent / 'analysis'
    sys.path.insert(0, str(analysis_dir))
    from ast_analyzer import ASTAnalyzer
    
    analyzer = ASTAnalyzer()
    project_data = analyzer.scan_project(".")
    
    # Extract violations WITH CODE CONTEXT
    violations_with_code = []
    for file_data in project_data:
        if 'phase_violations' not in file_data:
            continue
            
        for violation in file_data['phase_violations']:
            # Get code context
            context = analyzer._get_code_context(
                file_data['source'], 
                violation['line']
            )
            
            violations_with_code.append({
                'file': file_data['path'],
                'line': violation['line'],
                'type': violation.get('type', 'PHASE_VIOLATION'),
                'pattern': violation.get('pattern', 'unknown'),
                'full_line': violation.get('text', ''),
                'context': context,
            })
    
    print(f"\nPhase violations in project: {len(violations_with_code)}")
    
    # Show a few violations in the summary
    if violations_with_code:
        print("\nTop violations found:")
        for i, violation in enumerate(violations_with_code[:3], 1):
            print(f"  {i}. {violation['file']}:{violation['line']} - {violation.get('pattern', '')}")
    
    # Key files - FILTER OUT DOCUMENTATION
    if whoosh_results:
        # Filter out documentation files
        def is_code_file(path: str) -> bool:
            path_lower = path.lower()
            code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.h', '.cs']
            doc_patterns = ['\\docs\\', '/docs/', '\\doc\\', '/doc/', '\\documentation\\', '/documentation/']
            
            # Must be a code file
            if not any(path_lower.endswith(ext) for ext in code_extensions):
                return False
            
            # Must NOT be in documentation directory
            if any(pattern in path_lower for pattern in doc_patterns):
                return False
            
            return True
        
        # Filter whoosh results
        code_files = [r for r in whoosh_results if is_code_file(r['path'])]
        
        print(f"\nCode files ({len(code_files)} found):")
        for result in code_files[:8]:
            score_str = f"({result['score']:.2f})" if args.detail else ""
            print(f"  - {result['path']} {score_str}")
        
        # Optionally show documentation files separately
        if args.detail and len(code_files) < len(whoosh_results):
            doc_files = [r for r in whoosh_results if not is_code_file(r['path'])]
            print(f"\nRelated documentation ({len(doc_files)} found):")
            for result in doc_files[:3]:
                print(f"  - {result['path']}")
    
    # Use llama3.2 for deeper analysis
    if args.deep:
        print("\n" + "=" * 80)
        print("DEEP ANALYSIS (using llama3.2)")
        print("=" * 80)
        
        if violations_with_code:
            # Build a prompt that includes ACTUAL CODE VIOLATIONS
            analysis_prompt = f"""
            Analysis Topic: {query}
            
            Found {len(whoosh_results)} relevant files.
            
            PHASE VIOLATIONS ANALYSIS:
            Found {len(violations_with_code)} actual phase violations in code:
            
            """
            
            # Add each violation with code context
            for i, violation in enumerate(violations_with_code[:10], 1):
                analysis_prompt += f"\n{'='*60}"
                analysis_prompt += f"\nVIOLATION {i}: {violation['file']}:{violation['line']}"
                analysis_prompt += f"\nType: {violation['type']}"
                analysis_prompt += f"\nPattern: {violation['pattern']}"
                analysis_prompt += f"\n\nCode context:\n{violation['context']}"
                analysis_prompt += f"\nFull line: {violation['full_line']}"
            
            analysis_prompt += f"""
            {'='*60}
            TASK: Analyze these SPECIFIC phase violations and provide:
            
            1. For EACH violation:
               - Is this actually a PHASE/ARCHITECTURAL violation? (Yes/No with reason)
               - What specific architectural rule does it violate?
               - What's the exact fix needed?
               - Priority level (High/Medium/Low)
            
            2. Overall recommendations:
               - Most critical violations to fix first
               - Estimated effort for fixes
               - Architectural improvements needed
            
            IMPORTANT: Focus only on PHASE/ARCHITECTURAL violations (boundary crossings, layer violations, direct external calls).
            IGNORE general code quality issues (unused imports, magic numbers, long methods, etc.).
            """
        else:
            print("✅ No architectural violations found.")
            print("\nFor comprehensive project analysis:")
            print("  python ai.py analyze-project       # Full structure + phase compliance")
            print("  python ai.py refactor-plan         # Generate refactoring plan")
            print("  python ai.py living-workflow       # Complete workflow analysis")
            print("\nFor detailed phase violation analysis:")
            print("  python tools/analysis/ast_analyzer.py . --mode violations --show-code")
        
        analysis = agent._call_ollama(analysis_prompt)
        print(analysis)

def guardrails_command(args):
    """Show and validate guardrails"""
    # Guardrail files are in DOCS/ directory
    guardrail_files = {
        'phase': 'DOCS/ENGINE_LOOP.md',
        'system': 'DOCS/SYSTEM_OWNERSHIP.md',
        'integration': 'DOCS/INTEGRATION_CHECKLIST.md',
        'documentation': 'DOCS/DOCUMENTATION_STANDARDS.md',
        'workflow': 'DOCS/DOCUMENTATION_WORKFLOW.md',
    }
    
    if args.list:
        print("Available guardrail categories:")
        for key, filename in guardrail_files.items():
            path = Path(filename)
            if path.exists():
                size = path.stat().st_size
                print(f"  {key}: {filename} ({size} bytes)")
            else:
                print(f"  {key}: {filename} (NOT FOUND)")
        return 0
    
    # Show default (development) if none specified
    from .indexer import CodebaseIndexer
    from .context_builder import BridgeAgent
    
    # Use BridgeAgent to parse and summarize guardrails
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # Get phase compliance summary
    phase_context = indexer.get_phase_violation_context()
    
    print("\nGUARDRAILS SUMMARY")
    print("=" * 80)
    
    if phase_context:
        violations = phase_context.get('total_violations', 0)
        print(f"Phase violations in project: {violations}")
        if violations > 0:
            print("\nRecent phase violations from audit:")
            for i, violation in enumerate(phase_context.get('violations', [])[:3], 1):
                print(f"\n{i}. {violation[:200]}...")
    
    # List key guardrail files
    print("\nKey guardrail files found:")
    for key, filename in guardrail_files.items():
        path = Path(filename)
        if path.exists():
            print(f"  ✓ {key}: {filename}")
        else:
            print(f"  ✗ {key}: {filename} (missing)")
    
    return 0

def phase_check_command(args):
    """Check phase compliance for specific files or patterns"""
    from .indexer import CodebaseIndexer
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    # Search for phase violations
    results = indexer.search("phase violation", limit=args.limit)
    
    if not results:
        print("No phase violations found in indexed files.")
        return 0
    
    print(f"\nFound {len(results)} files with phase violation references:")
    print("=" * 80)
    
    violation_files = []
    for result in results:
        file_path = result['path']
        if file_path.endswith('.py'):
            violation_files.append(file_path)
            print(f"  - {file_path} (score: {result['score']:.3f})")
    
    # Check specific patterns
    if args.patterns:
        print(f"\nChecking patterns: {args.patterns}")
        patterns = args.patterns.split(',')
        
        for pattern in patterns:
            pattern_results = indexer.search(pattern, limit=5)
            if pattern_results:
                print(f"\nPattern '{pattern}':")
                for result in pattern_results:
                    print(f"  - {result['path']}")
    
    return 0

# Analysis commands from old cli.py
def violations_command(args):
    """Run phase boundary violation analysis"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'analysis'
    
    # Find the analyzer
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "violations"])
    
    return subprocess.call(cmd)

def todos_command(args):
    """Find TODOs and FIXMEs"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'analysis'
    
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "todos"])
    
    return subprocess.call(cmd)

def deps_command(args):
    """Show dependency analysis"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'analysis'
    
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "deps"])
    
    return subprocess.call(cmd)

def structure_command(args):
    """Show project structure"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'analysis'
    
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "structure"])
    
    return subprocess.call(cmd)

# Architecture commands
def refactor_plan_command(args):
    """Generate refactoring plan"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'architecture'
    
    architect_path = tools_dir / 'enhanced_architect.py'
    
    if not architect_path.exists():
        print(f"Error: Could not find architect at {architect_path}")
        return 1
    
    cmd = [sys.executable, str(architect_path), "--refactor-plan"]
    return subprocess.call(cmd)

def js_css_check_command(args):
    """Check JS/CSS separation"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'architecture'
    
    architect_path = tools_dir / 'enhanced_architect.py'
    
    if not architect_path.exists():
        print(f"Error: Could not find architect at {architect_path}")
        return 1
    
    cmd = [sys.executable, str(architect_path), "--check-js-css"]
    return subprocess.call(cmd)

def analyze_project_command(args):
    """Complete project analysis"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'architecture'
    
    architect_path = tools_dir / 'enhanced_architect.py'
    
    if not architect_path.exists():
        print(f"Error: Could not find architect at {architect_path}")
        return 1
    
    cmd = [sys.executable, str(architect_path), "--analyze"]
    return subprocess.call(cmd)

# Workflow commands
def feature_report_command(args):
    """Generate dynamic feature report"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'workflow'
    
    analyzer_path = tools_dir / 'dynamic_feature_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path), "--report"]
    return subprocess.call(cmd)

def living_workflow_command(args):
    """Run complete living system workflow"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'workflow'
    
    workflow_path = tools_dir / 'living_workflow.py'
    
    if not workflow_path.exists():
        print(f"Error: Could not find workflow at {workflow_path}")
        return 1
    
    cmd = [sys.executable, str(workflow_path)]
    return subprocess.call(cmd)

# Bridge commands
def bridge_status_command(args):
    """Check AI Bridge status"""
    import subprocess
    tools_dir = Path(__file__).parent.parent / 'bridge'
    
    bridge_path = tools_dir / 'bridge_controller.py'
    
    if not bridge_path.exists():
        print(f"Error: Could not find bridge controller at {bridge_path}")
        return 1
    
    # Simple check for bridge components
    import requests
    try:
        print("Checking Ollama...")
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running")
            models = response.json().get("models", [])
            print(f"  Available models: {[m.get('name') for m in models]}")
        else:
            print(f"⚠️ Ollama returned HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Ollama not available: {e}")
    
    print("\nChecking DeepSeek Bridge...")
    try:
        # Try to import and initialize the bridge
        sys.path.insert(0, str(tools_dir))
        from bridge_controller import BridgeController
        from deepseek_bridge import DeepSeekBridge
        
        bridge = DeepSeekBridge()
        print("✅ DeepSeek Bridge imports successful")
        print(f"  Profile path: {bridge.profile_path}")
        
        controller = BridgeController(bridge)
        print("✅ Bridge Controller initialized")
        
    except Exception as e:
        print(f"❌ Bridge setup error: {e}")
    
    return 0

# Direct file editing commands (no backup)
def delete_command(args):
    """Delete lines from file directly"""
    from .editing_commands import EditingCommands
    
    try:
        if args.dry_run:
            print(f"DRY RUN: Would delete lines {args.start}-{args.end} from {args.file}")
            # Show what would be deleted
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if args.start <= len(lines) and args.end <= len(lines):
                    print("Lines that would be deleted:")
                    for i in range(args.start-1, min(args.end, len(lines))):
                        print(f"  {i+1}: {lines[i].rstrip()}")
                else:
                    print(f"Warning: Line numbers out of range (file has {len(lines)} lines)")
            except Exception as e:
                print(f"Error reading file: {e}")
            return 0
        
        # Ask for confirmation
        print(f"Delete lines {args.start}-{args.end} from {args.file}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Perform deletion
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if args.start < 1 or args.end > len(lines) or args.start > args.end:
            print(f"Error: Invalid line range (1-{len(lines)})")
            return 1
        
        # Delete lines
        del lines[args.start-1:args.end]
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Deleted lines {args.start}-{args.end} from {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def insert_command(args):
    """Insert lines into file directly"""
    from .editing_commands import EditingCommands
    
    try:
        # Handle newlines in text
        text_lines = args.text.replace('\\n', '\n').split('\n')
        
        if args.dry_run:
            print(f"DRY RUN: Would insert {len(text_lines)} lines at line {args.line} in {args.file}")
            print("Content that would be inserted:")
            for i, line in enumerate(text_lines):
                print(f"  [{i+1}] {line}")
            return 0
        
        # Ask for confirmation
        print(f"Insert {len(text_lines)} lines at line {args.line} in {args.file}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Read file
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if args.line < 1 or args.line > len(lines) + 1:
            print(f"Error: Invalid line position (1-{len(lines)+1})")
            return 1
        
        # Prepare new lines with newline characters
        new_lines = []
        for line in text_lines:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
        
        # Insert lines
        lines[args.line-1:args.line-1] = new_lines
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Inserted {len(new_lines)} lines at line {args.line} in {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def replace_command(args):
    """Replace lines in file directly"""
    from .editing_commands import EditingCommands
    
    try:
        # Handle newlines in text
        text_lines = args.text.replace('\\n', '\n').split('\n')
        
        if args.dry_run:
            print(f"DRY RUN: Would replace lines {args.start}-{args.end} in {args.file}")
            print(f"  With {len(text_lines)} lines of new content")
            print("New content:")
            for i, line in enumerate(text_lines):
                print(f"  [{i+1}] {line}")
            return 0
        
        # Ask for confirmation
        print(f"Replace lines {args.start}-{args.end} in {args.file} with {len(text_lines)} new lines?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Read file
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if args.start < 1 or args.end > len(lines) or args.start > args.end:
            print(f"Error: Invalid line range (1-{len(lines)})")
            return 1
        
        # Prepare new lines with newline characters
        new_lines = []
        for line in text_lines:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
        
        # Replace lines
        lines[args.start-1:args.end] = new_lines
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Replaced lines {args.start}-{args.end} in {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def write_command(args):
    """Write or overwrite file directly"""
    from .editing_commands import EditingCommands
    
    try:
        # Handle newlines in text
        content = args.text.replace('\\n', '\n')
        
        if args.dry_run:
            print(f"DRY RUN: Would write {len(content)} characters to {args.file}")
            print("First 500 characters of content:")
            print(content[:500])
            if len(content) > 500:
                print("...")
            return 0
        
        # Check if file exists
        import os
        if os.path.exists(args.file):
            print(f"⚠️  File {args.file} already exists. Overwrite?")
            response = input("Confirm (y/n): ").lower().strip()
        else:
            print(f"Create new file {args.file}?")
            response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Ensure content ends with newline if it has content
        if content and not content.endswith('\n'):
            content += '\n'
        
        # Write file
        with open(args.file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        action = "Overwrote" if os.path.exists(args.file) else "Created"
        print(f"✅ {action} file {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def replace_text_command(args):
    """Replace text in file directly"""
    from .editing_commands import EditingCommands
    
    try:
        if args.dry_run:
            print(f"DRY RUN: Would replace '{args.search}' with '{args.replace}' in {args.file}")
            # Count occurrences
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
                count = content.count(args.search)
                print(f"  Found {count} occurrence(s) of '{args.search}'")
                if count > 0:
                    # Show context
                    idx = content.find(args.search)
                    if idx >= 0:
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(args.search) + 50)
                        context = content[start:end].replace('\n', ' ')
                        print(f"  First occurrence context: ...{context}...")
            except Exception as e:
                print(f"  Error reading file: {e}")
            return 0
        
        # Ask for confirmation
        print(f"Replace all occurrences of '{args.search}' with '{args.replace}' in {args.file}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Read file
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if args.search not in content:
            print(f"⚠️  Text '{args.search}' not found in {args.file}")
            return 0
        
        # Replace text
        new_content = content.replace(args.search, args.replace)
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        count = content.count(args.search)
        print(f"✅ Replaced {count} occurrence(s) of '{args.search}' in {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def extract_class_command(args):
    """Extract class to new file directly"""
    from .editing_commands import EditingCommands
    
    try:
        if args.dry_run:
            print(f"DRY RUN: Would extract class {args.class_name} from {args.source}")
            if args.target:
                print(f"  Target file: {args.target}")
            return 0
        
        # Ask for confirmation
        action = f"Extract class {args.class_name} from {args.source}"
        if args.target:
            action += f" to {args.target}"
        print(f"{action}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Use EditingCommands to perform extraction
        result = EditingCommands.extract_class_direct(
            source_file=args.source,
            class_name=args.class_name,
            target_file=args.target
        )
        
        if result.get('success'):
            print(f"✅ {result['message']}")
            return 0
        else:
            print(f"❌ {result.get('error', 'Extraction failed')}")
            return 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def extract_command(args):
    """Extract specific components for refactoring analysis"""
    from .indexer import CodebaseIndexer
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    component = args.component
    print(f"\nExtracting analysis for: {component}")
    print("=" * 80)
    
    # Search for component
    results = indexer.search(component, limit=20)
    
    # We need to get full documents to check for class definitions
    definition_files = []
    usage_files = []
    
    # Open index searcher to access full documents
    from whoosh.qparser import QueryParser
    if not indexer.index:
        from whoosh import index as idx
        indexer.index = idx.open_dir(str(args.index_dir))
    
    with indexer.index.searcher() as searcher:
        for result in results:
            path = result['path']
            # Get the full document from the index
            doc = searcher.document(path=path)
            if doc:
                content = doc.get('content', '')
                
                # Use regex to find class definition (more robust)
                import re
                regex_pattern = re.compile(r'class\s+' + re.escape(component) + r'\s*[:\(]')
                is_definition = bool(regex_pattern.search(content))
                
                if is_definition:
                    definition_files.append((path, result))
                    print(f"  ✓ Definition found in: {path}")
                    
                    if args.verbose:
                        # Show the class definition context
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if regex_pattern.search(line):
                                start = max(0, i - 2)
                                end = min(len(lines), i + 5)
                                print("    " + "\n    ".join(lines[start:end]))
                                break
                elif component in content:
                    usage_files.append((path, result))
    
    print(f"\nSummary:")
    print(f"  Definition files: {len(definition_files)}")
    print(f"  Usage files: {len(usage_files)}")
    if not args.output:
        print(f"  Tip: Use --output file.json to save full analysis")
    
    if definition_files:
        print(f"\nDefinition files:")
        for path, _ in definition_files:
            print(f"    - {path}")

    if usage_files:
        print(f"\nUsage files (first 10 of {len(usage_files)}):")
        for path, _ in usage_files[:10]:
            print(f"    - {path}")
        if len(usage_files) > 10:
            print(f"    ... and {len(usage_files) - 10} more")
    
    # Save to file if requested
    if args.output:
        extraction_data = {
            'component': component,
            'definition_files': [p for p, _ in definition_files],
            'usage_files': [p for p, _ in usage_files],
            'total_references': len(results)
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(extraction_data, f, indent=2)
        
        print(f"\n✓ Extraction data saved to: {args.output}")
    
    return 0

def extract_lines_command(args):
    """Extract lines to new file directly"""
    from .editing_commands import EditingCommands
    
    try:
        if args.dry_run:
            print(f"DRY RUN: Would extract lines {args.start}-{args.end} from {args.source} to {args.target}")
            return 0
        
        # Ask for confirmation
        print(f"Extract lines {args.start}-{args.end} from {args.source} to {args.target}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Use EditingCommands to perform extraction
        result = EditingCommands.extract_lines_direct(
            source_file=args.source,
            start_line=args.start,
            end_line=args.end,
            target_file=args.target
        )
        
        if result.get('success'):
            print(f"✅ {result['message']}")
            return 0
        else:
            print(f"❌ {result.get('error', 'Extraction failed')}")
            return 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def find_class_command(args):
    """Find class definition lines"""
    from .editing_commands import EditingCommands
    
    result = EditingCommands.find_class_lines(args.file, args.class_name)
    
    if result:
        start, end = result
        print(f"Class '{args.class_name}' found in {args.file}:")
        print(f"  Start line: {start}")
        print(f"  End line: {end}")
        print(f"  Total lines: {end - start + 1}")
        
        # Show snippet
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            start_idx = max(0, start - 3)
            end_idx = min(len(lines), start + 7)
            print(f"\nContext (lines {start_idx+1}-{end_idx}):")
            for i in range(start_idx, end_idx):
                print(f"{i+1:4}: {lines[i].rstrip()}")
    else:
        print(f"Class '{args.class_name}' not found in {args.file}")
    
    return 0

def main():
    """Main entry point"""
    parser = setup_subparsers()
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        parser.print_help()
        return 0
    
    # Call the appropriate command function
    try:
        return args.func(args)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())