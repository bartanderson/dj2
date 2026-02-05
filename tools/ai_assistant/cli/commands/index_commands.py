"""
Indexing-related commands for AI Assistant CLI
"""
import json
from pathlib import Path

# Import registry
from . import register_command

def index_command(args):
    """Create or update the Whoosh index"""
    from ..indexer import CodebaseIndexer
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    if args.verbose:
        print("Starting index creation/update...")
    
    indexer.create_or_update_index()
    
    # Print summary
    with indexer.index.searcher() as searcher:
        print(f"[OK] Index updated. Total documents: {searcher.doc_count()}")
        
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

def archive_index_command(args):
    """Index archive/legacy code separately"""
    from ..archive_indexer import ArchiveIndexer
    
    indexer = ArchiveIndexer(index_dir=args.index_dir)
    
    if args.verbose:
        print("Starting archive index creation/update...")
    
    indexer.create_or_update_index()
    
    # Print summary
    with indexer.index.searcher() as searcher:
        print(f"[OK] Archive index updated. Total archive documents: {searcher.doc_count()}")
        
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

# Register indexing commands
register_command('index', index_command, "Create/update Whoosh index")
register_command('archive-index', archive_index_command, "Index archive/legacy code separately")