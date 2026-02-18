#!/usr/bin/env python3
import sys
import json
from pathlib import Path

def main():
    # Get inputs from command line
    inputs = json.loads(sys.argv[1])
    
    sources = inputs.get('sources', {}).get('files', [])
    tests = inputs.get('tests', {}).get('files', [])
    
    # Extract just filenames for comparison
    source_names = [Path(f).name for f in sources if f.endswith('.py')]
    test_names = [Path(f).name for f in tests if f.endswith('.py')]
    
    # Find which source files have corresponding test files
    covered = []
    uncovered = []
    
    for src in source_names:
        # Look for test_ prefix version
        test_name = f"test_{src}"
        if test_name in test_names:
            covered.append(src)
        else:
            uncovered.append(src)
    
    result = {
        'total_files': len(source_names),
        'covered_files': len(covered),
        'uncovered_files': uncovered,
        'coverage_percent': (len(covered) / len(source_names) * 100) if source_names else 0
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()