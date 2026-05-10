#!/usr/bin/env python3
import sys
import json
import glob
from pathlib import Path

def main():
    # Get inputs from command line
    inputs = json.loads(sys.argv[1])
    
    path = inputs.get('path', '.')
    pattern = inputs.get('pattern', '*')
    
    # Find files
    search_path = Path(path)
    files = list(search_path.glob(pattern))
    
    # Output results as JSON
    result = {
        'files': [str(f) for f in files],
        'count': len(files)
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()