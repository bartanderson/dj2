"""Shared utility functions."""
import re
from pathlib import Path
from typing import List

MIN_CONCEPT_LENGTH = 3

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