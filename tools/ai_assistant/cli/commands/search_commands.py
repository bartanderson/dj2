"""
Search-related commands for AI Assistant CLI
"""
import json
from pathlib import Path
import subprocess
from whoosh.qparser import QueryParser

# Import registry
from . import register_command

# Try relative imports for our modules
try:
    from ..indexer import CodebaseIndexer
    from ..archive_indexer import ArchiveIndexer
    from ..config import AIConfig
except ImportError:
    # Fallback for direct execution
    from tools.ai_assistant.indexer import CodebaseIndexer
    from tools.ai_assistant.archive_indexer import ArchiveIndexer
    from tools.ai_assistant.config import AIConfig

def search_command(args):
    """Search the codebase"""
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
        if not indexer.index:
            indexer.index = indexer.index.open_dir(str(args.index_dir))

        # Normalize path for lookup
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

def archive_search_command(args):
    """Search only the archive index"""
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

# Register all search commands
register_command('search', search_command, "Search the codebase")
register_command('archive-search', archive_search_command, "Search only the archive index", aliases=['archives'])
register_command('combined-search', combined_search_command, "Search both main and archive indexes", aliases=['csearch'])