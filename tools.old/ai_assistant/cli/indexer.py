#tools/ai_assistant/indexer.py
"""
Whoosh-based indexer for code and documentation - Simplified version
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import ast
import json

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, KEYWORD, DATETIME
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.analysis import StemmingAnalyzer
from whoosh.query import Term, And, Or

from .config import AIConfig

class CodebaseIndexer:
    """Whoosh-based indexer for code and documentation"""
    
    def __init__(self, repo_root: str = ".", index_dir: str = ".whoosh_index"):
        self.repo_root = Path(repo_root).resolve()
        self.index_dir = Path(index_dir)
        self.schema = self._create_schema()
        self.index = None
        
    def _create_schema(self) -> Schema:
        """Define index schema"""
        return Schema(
            path=ID(stored=True, unique=True),
            filename=TEXT(stored=True, field_boost=3.0),
            definitions=TEXT(stored=True, field_boost=5.0),
            dirpath=ID(stored=True),
            content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            ast_info=TEXT(stored=True),
            file_type=KEYWORD(stored=True),
            last_modified=DATETIME(stored=True),
            sha256=ID(stored=True),
            phase_tags=KEYWORD(stored=True),
            system_tags=KEYWORD(stored=True)
        )
    
    def _extract_ast_info(self, filepath: Path, content: str) -> str:
        """Extract import relationships and class/method definitions"""
        try:
            if filepath.suffix != '.py':
                return ""
                
            tree = ast.parse(content)
            imports = []
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import:{alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"from:{module}.{alias.name}")
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    bases = [ast.unparse(base) for base in node.bases]
                    if bases:
                        classes[-1] += f" extends {', '.join(bases)}"
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
            
            return json.dumps({
                "imports": imports,
                "classes": classes,
                "functions": functions
            }, ensure_ascii=False)
        except SyntaxError:
            return ""

    def _extract_definitions(self, content: str) -> str:
        """Extract class and function definition lines as searchable text"""
        try:
            tree = ast.parse(content)
            definitions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    definitions.append(f"class {node.name}")
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            definitions.append(f"extends {base.id}")
                elif isinstance(node, ast.FunctionDef):
                    definitions.append(f"def {node.name}")
            return " ".join(definitions)
        except (SyntaxError, ValueError):
            return ""
    
    def should_index(self, filepath: Path) -> bool:
        """Determine if file should be indexed using config"""
        if not filepath.exists():
            return False
        
        if not filepath.is_file():
            return False
        
        # Check if path is excluded by config
        if AIConfig.should_exclude_path(filepath):
            return False
        
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
    
    def _extract_phase_tags(self, filepath: Path, content: str) -> List[str]:
        """Extract phase compliance tags from file content"""
        tags = []
        
        # Check file path against SYSTEM_OWNERSHIP.md patterns
        path_str = str(filepath)
        for pattern, tag in AIConfig.SYSTEM_PATTERNS:
            if pattern in path_str:
                tags.append(tag)
        
        # Check for phase keywords
        content_lower = content.lower()
        for keyword in AIConfig.PHASE_KEYWORDS:
            if keyword in content_lower:
                clean_keyword = keyword.replace('_phase', '').replace('_', ' ')
                tags.append(f"phase:{clean_keyword}")
        
        # Special: Check for phase violations
        violation_indicators = [
            'phase violation',
            'violates phase',
            'phase mixing',
            'ai state mutation',
            'boundary crossing',
        ]
        
        for indicator in violation_indicators:
            if indicator in content_lower:
                tags.append("warning:phase_violation_risk")
                break
        
        return tags
    
    def create_or_update_index(self) -> None:
        """Create or update the Whoosh index with automatic cleanup of deleted files"""
        if not self.index_dir.exists():
            self.index_dir.mkdir(parents=True)
            print(f"Created index directory: {self.index_dir}")
        
        # Track current files as we walk the filesystem
        current_paths = set()
        files_to_index = []
        
        print("Scanning filesystem for current files...")
        for root, dirs, files in os.walk(self.repo_root):
            root_path = Path(root)
            
            # Filter directories using config
            dirs[:] = [
                d for d in dirs 
                if not self._should_exclude_dir(root_path / d)
            ]
            
            for file in files:
                filepath = root_path / file
                if self.should_index(filepath):
                    try:
                        relative_path = filepath.relative_to(self.repo_root)
                        current_paths.add(str(relative_path))
                        files_to_index.append(filepath)
                    except ValueError:
                        continue
        
        print(f"Found {len(files_to_index)} files to index")
        
        # Open or create index
        if index.exists_in(str(self.index_dir)):
            ix = index.open_dir(str(self.index_dir))
            print(f"Opening existing index (has {ix.doc_count()} documents)...")
            
            # Get list of currently indexed paths
            with ix.searcher() as searcher:
                indexed_paths = set()
                for doc in searcher.documents():
                    indexed_paths.add(doc['path'])
            
            # Find paths that are in index but not on filesystem
            deleted_paths = indexed_paths - current_paths
            if deleted_paths:
                print(f"Found {len(deleted_paths)} deleted files to remove from index")
                writer = ix.writer()
                for path in deleted_paths:
                    writer.delete_by_term('path', path)
                writer.commit(merge=False)
                print(f"Removed {len(deleted_paths)} deleted files from index")
                # Reopen index after deletion
                ix = index.open_dir(str(self.index_dir))
                    
        else:
            ix = index.create_in(str(self.index_dir), self.schema)
            print("Creating new index...")
        
        writer = ix.writer()
        
        print(f"Indexing {len(files_to_index)} files...")
        
        indexed_count = 0
        skipped_count = 0
        error_count = 0
        
        for filepath in files_to_index:
            try:
                relative_path = filepath.relative_to(self.repo_root)
                
                # Show progress
                indexed_count += 1
                if indexed_count % 50 == 0:
                    print(f"  Indexed {indexed_count}/{len(files_to_index)} files...")
                
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                
                # Check if already indexed with same hash
                with ix.searcher() as searcher:
                    existing = searcher.document(path=str(relative_path))
                    if existing and existing.get('sha256') == content_hash:
                        skipped_count += 1
                        continue
                
                # Extract metadata
                ast_info = self._extract_ast_info(filepath, content)
                phase_tags = self._extract_phase_tags(filepath, content)
                system_tags = self._extract_system_tags(relative_path)

                # Extract definitions for boosting
                definitions = ""
                if filepath.suffix.lower() == '.py':
                    definitions = self._extract_definitions(content)
                
                # Add document
                writer.update_document(
                    path=str(relative_path),
                    filename=filepath.name,
                    dirpath=str(relative_path.parent),
                    content=content,
                    definitions=definitions,
                    ast_info=ast_info,
                    file_type=filepath.suffix.lower().lstrip('.'),
                    last_modified=datetime.fromtimestamp(filepath.stat().st_mtime),
                    sha256=content_hash,
                    phase_tags=" ".join(phase_tags),
                    system_tags=" ".join(system_tags)
                )
                
            except Exception as e:
                error_count += 1
                if error_count < 10:
                    print(f"  Warning: Error indexing {filepath}: {e}")
                continue
        
        writer.commit()
        self.index = ix
        
        print(f"\n✓ Index completed:")
        print(f"  - New/updated files: {indexed_count - skipped_count - error_count}")
        print(f"  - Skipped (unchanged): {skipped_count}")
        print(f"  - Errors: {error_count}")
        print(f"  - Deleted files removed: {len(deleted_paths) if 'deleted_paths' in locals() else 0}")
        print(f"  - Total documents in index: {ix.doc_count()}")
        
        # Show summary of file types
        with ix.searcher() as searcher:
            types = {}
            for doc in searcher.documents():
                file_type = doc.get('file_type', 'unknown')
                types[file_type] = types.get(file_type, 0) + 1
            
            print(f"\nDocument types in index:")
            for file_type, count in sorted(types.items()):
                print(f"  {file_type}: {count}")
    
    def _extract_system_tags(self, filepath: Path) -> List[str]:
        """Extract system ownership tags based on your SYSTEM_OWNERSHIP.md"""
        path_str = str(filepath)
        
        system_patterns = [
            ("dungeon_neo", "system:dungeon"),
            ("world_controller", "system:world_controller"),
            ("game_engine", "system:game_engine"),
            ("tools/", "system:tools"),
            ("templates/", "system:templates"),
            ("static/", "system:static"),
            ("world/", "system:world_subsystem"),
            ("tests/", "system:tests"),
        ]
        
        tags = []
        for pattern, tag in system_patterns:
            if pattern in path_str:
                tags.append(tag)
                
        return tags


    def _should_exclude_dir(self, dir_path: Path) -> bool:
        """Check if a directory should be excluded from walking"""
        # Check each part of the path
        for part in dir_path.parts:
            for excluded_dir in AIConfig.EXCLUDED_DIRS:
                if '*' in excluded_dir:
                    import fnmatch
                    if fnmatch.fnmatch(part, excluded_dir):
                        return True
                elif part.lower() == excluded_dir.lower():
                    return True
        return False  

    def search(self, query: str, limit: int = 20, file_types: List[str] = None, 
              path_filter: str = None) -> List[Dict]:
        """Search the index with optional filters"""
        
        if not self.index:
            self.index = index.open_dir(str(self.index_dir))
            
        with self.index.searcher() as searcher:
            # Build query - search in multiple fields with different boosts
            fieldnames = ["content", "definitions", "filename", "ast_info"]
            fieldboosts = {
                "definitions": 5.0,
                "filename": 3.0,
                "content": 1.0,
                "ast_info": 0.5
            }

            qp = MultifieldParser(fieldnames, schema=self.index.schema, 
                                 fieldboosts=fieldboosts)
            q = qp.parse(query)
            
            # Create a filter query for file types if specified
            filter_query = None
            if file_types:
                file_types_lower = [ft.lower() for ft in file_types]
                file_type_terms = [Term("file_type", ft) for ft in file_types_lower]
                if file_type_terms:
                    filter_query = Or(file_type_terms)
            
            # Determine search limit
            if path_filter:
                search_limit = searcher.doc_count()
            else:
                search_limit = limit * 2
            
            # Search with filter if provided
            if filter_query:
                results = searcher.search(q, filter=filter_query, limit=search_limit)
            else:
                results = searcher.search(q, limit=search_limit)
            
            # Apply path filter after the search if specified
            if path_filter:
                path_filter_normalized = path_filter.replace('/', '\\').lower()
                
                filtered_results = []
                for i, hit in enumerate(results):
                    indexed_path = hit["path"].lower()
                    
                    is_exact_file = (indexed_path == path_filter_normalized)
                    is_in_directory = (indexed_path.startswith(path_filter_normalized.rstrip('\\') + '\\'))

                    if is_exact_file or is_in_directory:
                        filtered_results.append(self._format_hit(hit))
                
                results = filtered_results[:limit]
            else:
                results = [self._format_hit(hit) for hit in results][:limit]
            
            return results
    
    def _format_hit(self, hit) -> Dict:
        """Format a Whoosh hit into our result format"""
        return {
            "path": hit["path"],
            "filename": hit["filename"],
            "score": hit.score,
            "content_preview": hit["content"][:500] if hit["content"] else "",
            "file_type": hit["file_type"],
            "phase_tags": hit.get("phase_tags", "").split(),
            "system_tags": hit.get("system_tags", "").split()
        }
    
    def get_related_files(self, filepath: str) -> List[Dict]:
        """Find files related to the given file"""
        if not self.index:
            return []
            
        with self.index.searcher() as searcher:
            target = searcher.document(path=filepath)
            if not target:
                return []
                
            related = []
            
            # Find files in same directory
            dir_path = Path(filepath).parent
            for doc in searcher.documents():
                if doc['dirpath'] == str(dir_path) and doc['path'] != filepath:
                    related.append({
                        "path": doc['path'],
                        "filename": doc['filename'],
                        "relation": "same_directory"
                    })
            
            return related[:10]
    
    def get_phase_violation_context(self) -> Dict:
        """Get context about phase violations from PHASE_AUDIT.md"""
        if not self.index:
            return {}
            
        with self.index.searcher() as searcher:
            results = searcher.search(
                QueryParser("content", self.index.schema).parse("phase violation")
            )
            
            for hit in results:
                if "phase_audit" in hit["path"].lower():
                    content = hit["content"]
                    violations = []
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "violation" in line.lower() and "phase" in line.lower():
                            context = '\n'.join(lines[max(0, i-3):min(len(lines), i+3)])
                            violations.append(context)
                    
                    return {
                        "file": hit["path"],
                        "violations": violations[:5],
                        "total_violations": len(violations)
                    }
            
            return {}