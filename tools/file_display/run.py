#!/usr/bin/env python3
"""
Display file contents with optional JSON pretty-printing.
Follows NativeClaw output contract.
"""

import sys
import json
from pathlib import Path

def display_file(file_path, fmt='text'):
    """Read and display file according to format."""
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "error": f"File not found: {file_path}"}

    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return {"status": "error", "error": f"Could not read file: {e}"}

    if fmt == 'json':
        try:
            data = json.loads(content)
            # Pretty print with indent
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return {"status": "success", "data": formatted, "format": "json"}
        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Invalid JSON: {e}"}
    else:
        # text format: just output raw content
        return {"status": "success", "data": content, "format": "text"}

def main():
    # Parse JSON input
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "error": "No input provided"}))
        sys.exit(1)

    try:
        params = json.loads(' '.join(sys.argv[1:]))
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "error": "Invalid JSON input"}))
        sys.exit(1)

    path = params.get('path')
    fmt = params.get('format', 'text')

    if not path:
        print(json.dumps({"status": "error", "error": "Missing 'path' parameter"}))
        sys.exit(1)

    result = display_file(path, fmt)
    print(json.dumps(result))

if __name__ == '__main__':
    main()