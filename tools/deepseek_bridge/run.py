#!/usr/bin/env python3
"""
DeepSeek Bridge Tool – One-shot consultation.
Uses the shared library to perform a single consultation and print JSON result.
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.deepseek_bridge.bridge_lib import consult
from tools.bridge.unified_core import BridgeCore

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "error": "No input"}))
        return

    raw_input = ' '.join(sys.argv[1:])
    if raw_input.startswith(("'", '"')) and raw_input.endswith(("'", '"')):
        raw_input = raw_input[1:-1]
    try:
        params = json.loads(raw_input)
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "error": "Invalid JSON"}))
        return

    file_path = params.get('file')
    prompt = params.get('prompt', '')

    if not file_path:
        print(json.dumps({"status": "error", "error": "Missing 'file'"}))
        return

    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        print(json.dumps({"status": "error", "error": f"File not found: {path}"}))
        return

    # Initialize bridge core (opens browser)
    core = BridgeCore(verbose=False)
    if not core.connect():
        print(json.dumps({"status": "error", "error": "Connection failed"}))
        return

    try:
        response_text = consult(core.driver, path, prompt)
        result = {"status": "success", "data": response_text}
    except Exception as e:
        result = {"status": "error", "error": str(e)}
    finally:
        core.close()

    print(json.dumps(result))

if __name__ == "__main__":
    main()