#!/usr/bin/env python3
"""
data.store tool – saves data to a JSON file and returns its path.
Usage: store.py <json-input>
"""

import sys
import json
import os
from pathlib import Path

def main():
    # NativeClaw passes the entire 'with' dict as a JSON string when input_format: json
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No input provided"}))
        return 1

    raw = sys.argv[1]
    try:
        params = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON input"}))
        return 1

    data = params.get('data')
    if data is None:
        print(json.dumps({"error": "Missing 'data' field"}))
        return 1

    # Determine session directory from environment (set by nativeclaw)
    session_dir = os.environ.get('NATIVECLAW_SESSION_DIR')
    if not session_dir:
        # Fallback to a temp directory (should not happen in normal use)
        import tempfile
        session_dir = tempfile.mkdtemp(prefix="nativeclaw_fallback_")
    session_path = Path(session_dir)
    session_path.mkdir(parents=True, exist_ok=True)

    # Create a unique filename – use step name if provided, otherwise a random hex
    step_name = params.get('_step_name', 'data')
    # Add a short random suffix to avoid collisions if the same step runs twice
    import secrets
    suffix = secrets.token_hex(4)  # 8 characters
    filename = f"{step_name}_{suffix}.json"
    file_path = session_path / filename

    # Write data
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(json.dumps({"error": f"Failed to write file: {e}"}))
        return 1

    # Return the path relative to the project root (cwd)
    # This makes it usable in subsequent steps without knowing the full path.
    cwd = Path.cwd()
    try:
        rel_path = file_path.relative_to(cwd)
    except ValueError:
        # If not under cwd, return absolute path
        rel_path = file_path

    print(json.dumps({"path": str(rel_path)}))
    return 0

if __name__ == "__main__":
    sys.exit(main())