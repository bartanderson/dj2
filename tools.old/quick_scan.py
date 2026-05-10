#!/usr/bin/env python3
"""
Quick file inventory - using your ignore patterns
"""

from pathlib import Path
from datetime import datetime
import json

# Your ignore patterns from arch_recon
IGNORE_PATTERNS = ['__pycache__', 'venv', '.git', 'node_modules', 'Lib', 'docs', 'archive']

def should_ignore(path):
    """Check if path matches any ignore pattern."""
    path_str = str(path).lower()
    for pattern in IGNORE_PATTERNS:
        if pattern.lower() in path_str:
            return True
    return False

def scan():
    root = Path('.')
    files = []
    
    # Directories to scan
    scan_dirs = ['tools', 'scripts', '.']
    
    for scan_dir in scan_dirs:
        path = root / scan_dir
        if not path.exists():
            continue
            
        for py_file in path.rglob('*.py'):
            # Skip if matches ignore patterns
            if should_ignore(py_file):
                continue
                
            rel_path = str(py_file.relative_to(root))
            stat = py_file.stat()
            
            # Check for tool.yaml in same directory
            has_tool_yaml = (py_file.parent / 'tool.yaml').exists()
            
            files.append({
                'path': rel_path.replace('\\', '/'),
                'folder': str(py_file.parent.relative_to(root)).replace('\\', '/'),
                'name': py_file.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'has_tool_yaml': has_tool_yaml
            })
    
    # Summary by folder
    by_folder = {}
    for f in files:
        folder = f['folder']
        if folder not in by_folder:
            by_folder[folder] = {'count': 0, 'with_yaml': 0}
        by_folder[folder]['count'] += 1
        if f['has_tool_yaml']:
            by_folder[folder]['with_yaml'] += 1
    
    # Save to file
    output = {
        'files': files,
        'summary': {
            'total': len(files),
            'with_tool_yaml': sum(1 for f in files if f['has_tool_yaml']),
            'by_folder': by_folder
        },
        'ignored_patterns': IGNORE_PATTERNS
    }
    
    with open('tool_inventory.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Print quick summary
    print(f"\n📊 QUICK INVENTORY")
    print(f"   Total Python files: {output['summary']['total']}")
    print(f"   With tool.yaml: {output['summary']['with_tool_yaml']}")
    print(f"   Ignoring: {', '.join(IGNORE_PATTERNS)}")
    print("\n📁 By folder:")
    for folder, stats in sorted(by_folder.items()):
        pct = (stats['with_yaml'] / stats['count'] * 100) if stats['count'] else 0
        print(f"   {folder}: {stats['count']} files ({stats['with_yaml']} with yaml, {pct:.1f}%)")

if __name__ == '__main__':
    scan()