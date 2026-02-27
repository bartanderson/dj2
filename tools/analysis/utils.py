"""Shared utility functions."""
import os
import re
from pathlib import Path
from typing import List, Optional

MIN_CONCEPT_LENGTH = 3

def clean_ascii(text):
    """Remove non-ASCII characters and normalize whitespace."""
    if not text:
        return ""
    import unicodedata
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

def module_to_file_path(full_module: str, project_root: Path) -> Optional[Path]:
    """
    Convert a dotted module name (e.g., 'world.ai_integration') to a file path.
    Returns a Path if the file exists, otherwise None.
    """
    # Replace dots with OS separator and add .py
    rel_path = full_module.replace('.', os.sep) + '.py'
    candidate = project_root / rel_path
    if candidate.exists():
        return candidate
    # If not found, try __init__.py in the package directory
    pkg_path = project_root / full_module.replace('.', os.sep) / '__init__.py'
    if pkg_path.exists():
        return pkg_path
    return None

def split_identifier(name: str) -> List[str]:
    if not name:
        return []
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    s = s.replace('_', ' ')
    words = s.lower().split()
    return [w for w in words if len(w) >= MIN_CONCEPT_LENGTH]

def classify_role(path: str) -> str:
    ROLE_RULES = [
        (lambda p: '/routes/' in p, 'Adapter'),
        (lambda p: '/ai/' in p, 'AI-Facing'),
        (lambda p: 'dm_chat_ai' in p or 'ai_boundary' in p, 'Boundary'),
    ]
    DEFAULT_ROLE = 'Core'
    posix_path = path.replace('\\', '/')
    for condition, role in ROLE_RULES:
        if condition(posix_path):
            return role
    return DEFAULT_ROLE

def should_ignore(path: Path, ignore_dirs: List[str]) -> bool:
    for part in path.parts:
        if part in ignore_dirs:
            return True
    return False