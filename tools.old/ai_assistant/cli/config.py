#tools/ai_assistant/config.py
"""
Configuration for the AI Assistant indexing and analysis
Simplified version
"""

from pathlib import Path
from typing import Set, List, Dict

class AIConfig:
    """Configuration for the AI Assistant"""

    # Archive configuration
    ARCHIVE_DIRS: List[str] = ['archive', 'old', 'legacy', 'backup', 'deprecated']  # Folders to treat as archives
    
    # Directories to always exclude from indexing
    EXCLUDED_DIRS: Set[str] = {
        '.git', '__pycache__', 'node_modules', 'venv', '.env',
        '.vscode', '.idea', '.pytest_cache', '.mypy_cache', '.ruff_cache',
        'dist', 'build', '*.egg-info', 'site-packages',
        'Lib', 'Scripts', 'Include',  # Python installation
        'archive', 'backups', 'snapshots', 'temp', 'tmp',
        'ai_context','.nativeclaw','.whoosh_index',  # Our own index directory
    }

    # File type groups for smart filtering
    FILE_TYPE_GROUPS: Dict[str, Set[str]] = {
        'code': {'.py', '.js', '.ts', '.html', '.css', '.vue', '.jsx', '.tsx'},
        'docs': {'.md', '.txt', '.rst', '.adoc'},
        'config': {'.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.env'},
        'ui': {'.html', '.css', '.js', '.ts', '.vue', '.jsx', '.tsx'},
        'python': {'.py'},
        'markdown': {'.md'},
        'json': {'.json'},
        'yaml': {'.yml', '.yaml'},
        'text': {'.txt', '.md', '.rst'},
        'all': set()  # Empty set means all indexed extensions
    }
    
    # File extensions to index
    INDEXED_EXTENSIONS: Set[str] = {
        # Code files
        '.py', '.html', '.htm', '.css', '.js', '.ts', '.vue', '.jsx', '.tsx',
        # Data files
        '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.env',
        # Documentation
        '.md', '.txt', '.rst', '.adoc',
        # Config/misc
        '.xml', '.csv', '.sql', '.sh', '.bat', '.ps1',
    }
    
    # File patterns to exclude (glob patterns)
    EXCLUDED_PATTERNS: List[str] = [
        '*.pyc', '*.pyo', '*.pyd', '*.so', '*.dll', '*.dylib',
        '*.exe', '*.bin', '*.dat', '*.db', '*.sqlite', '*.sqlite3',
        '*.log', '*.cache', '*.lock', '*.pid',
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.ico',
        '*.mp3', '*.mp4', '*.wav', '*.ogg', '*.pdf', '*.zip',
        '*.tar', '*.gz', '*.7z', '*.rar',
    ]
    
    # Maximum file size to index (in bytes)
    MAX_FILE_SIZE: int = 2 * 1024 * 1024  # 2MB
    
    # Phase system keywords (for tagging)
    PHASE_KEYWORDS: Set[str] = {
        'input_phase', 'interpretation_phase', 'authority_phase',
        'state_mutation_phase', 'consequence_phase', 'persistence_phase',
        'view_projection_phase',
        'gameengine', 'session_system', 'dmchatai', 'authority_system',
    }
    
    # System ownership patterns (from SYSTEM_OWNERSHIP.md)
    SYSTEM_PATTERNS = [
        ('dungeon_neo/', 'system:dungeon'),
        ('world_controller', 'system:world_controller'),
        ('game_engine', 'system:game_engine'),
        ('tools/', 'system:tools'),
        ('templates/', 'system:templates'),
        ('static/', 'system:static'),
        ('world/', 'system:world_subsystem'),
        ('tests/', 'system:tests'),
        ('ai_assistant/', 'system:ai_assistant'),
    ]

    @classmethod
    def is_archive_path(cls, path: Path) -> bool:
        """Check if a path is in an archive directory"""
        path_str = str(path)
        # Convert to forward slashes for consistency
        normalized_path = path_str.replace('\\', '/')
        # Check if any archive directory appears in the path
        for archive_dir in cls.ARCHIVE_DIRS:
            if f"/{archive_dir}/" in normalized_path or normalized_path.startswith(f"{archive_dir}/"):
                return True
        return False
    
    @classmethod
    def get_file_extensions_for_group(cls, group_name: str) -> Set[str]:
        """Get file extensions for a group name"""
        return cls.FILE_TYPE_GROUPS.get(group_name.lower(), set())
    
    @classmethod
    def is_valid_group(cls, group_name: str) -> bool:
        """Check if a group name is valid"""
        return group_name.lower() in cls.FILE_TYPE_GROUPS
    
    @classmethod
    def should_exclude_path(cls, path: Path) -> bool:
        """Check if a path should be excluded"""
        # Check each part of the path (individual directory names)
        for part in path.parts:
            # Check against excluded directories
            for excluded_dir in cls.EXCLUDED_DIRS:
                if '*' in excluded_dir:
                    import fnmatch
                    if fnmatch.fnmatch(part, excluded_dir):
                        return True
                elif part.lower() == excluded_dir.lower():  # Case-insensitive
                    return True
        return False