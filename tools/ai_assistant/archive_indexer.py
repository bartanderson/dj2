#tools/ai_assistant/archive_indexer.py
"""
Separate indexer for archive/legacy code
Simplified version
"""

import os
from pathlib import Path
from typing import Set, List, Dict

from .indexer import CodebaseIndexer
from .config import AIConfig

class ArchiveIndexer(CodebaseIndexer):
    """Specialized indexer for archive/legacy code"""
    
    def __init__(self, repo_root: str = ".", index_dir: str = ".archive_index"):
        super().__init__(repo_root, index_dir)

    def _should_exclude_dir(self, dir_path: Path) -> bool:
        """Check if a directory should be excluded from walking"""
        # Check each part of the path
        for part in dir_path.parts:
            for excluded_dir in AIConfig.EXCLUDED_DIRS:
                # Don't exclude archive directories!
                if excluded_dir in AIConfig.ARCHIVE_DIRS:
                    continue
                    
                if '*' in excluded_dir:
                    import fnmatch
                    if fnmatch.fnmatch(part, excluded_dir):
                        return True
                elif part.lower() == excluded_dir.lower():
                    return True
        return False
    
    def should_index(self, filepath: Path) -> bool:
        """Only index files in archive directories"""
        # First check if it's in an archive folder
        if not AIConfig.is_archive_path(filepath):
            return False
        
        # Then apply normal indexing rules (but don't check EXCLUDED_DIRS since we handled it in _should_exclude_dir)
        # Check extension
        if filepath.suffix.lower() not in AIConfig.INDEXED_EXTENSIONS:
            return False
        
        # Size check
        try:
            if filepath.stat().st_size > AIConfig.MAX_FILE_SIZE:
                return False
        except OSError:
            return False
        
        return True
    
    def create_or_update_index(self) -> None:
        """Create/update archive index with automatic cleanup"""
        print("=== ARCHIVE INDEXING ===")
        print(f"Looking for files in archive directories: {', '.join(AIConfig.ARCHIVE_DIRS)}")
        print(f"Note: Archive directories are NOT excluded from scanning")
        super().create_or_update_index()
    
    def search(self, query: str, limit: int = 20, file_types: List[str] = None, 
              path_filter: str = None) -> List[Dict]:
        """Search the archive index"""
        # Add archive tag to results
        results = super().search(query, limit, file_types, path_filter)
        
        # Tag results as archive
        for result in results:
            result['is_archive'] = True
        
        return results