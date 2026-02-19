#!/usr/bin/env python3
"""
Tool Diagnostic: Test all registered tools with a short timeout.
For JSON tools, sends an empty JSON object; for CLI tools, sends --help.
"""

import sys
import subprocess
import yaml
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TIMEOUT = 10

def find_tool_yamls(root):
    return list(root.rglob('tool.yaml'))

def load_tool_info(yaml_path):
    with open(yaml_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return {
        'name': data.get('name', yaml_path.parent.name),
        'path': data.get('path'),
        'execution': data.get('execution', 'cli'),
        'input_format': data.get('input_format'),  # may be None
        'yaml': yaml_path
    }

def test_tool(tool):
    if tool['execution'] != 'cli':
        return {'status': 'skipped', 'reason': 'non-CLI tool'}

    script_path_str = tool.get('path')
    if not script_path_str:
        return {'status': 'missing', 'reason': 'no path in tool.yaml'}

    script_path = PROJECT_ROOT / script_path_str
    if not script_path.exists():
        return {'status': 'missing', 'reason': f'file not found: {script_path}'}

    # Build command based on input format
    if tool.get('input_format') == 'json':
        cmd = [sys.executable, str(script_path), '{}']  # empty JSON
    else:
        cmd = [sys.executable, str(script_path), '--help']

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            return {'status': 'ok', 'elapsed': elapsed, 'output': result.stdout[:200]}
        else:
            return {'status': 'failed', 'elapsed': elapsed,
                    'returncode': result.returncode, 'stderr': result.stderr[:200]}
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {'status': 'timeout', 'elapsed': elapsed}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def main():
    yamls = find_tool_yamls(PROJECT_ROOT)
    print(f"Found {len(yamls)} tool definitions.\n")
    results = []
    for y in yamls:
        try:
            tool = load_tool_info(y)
            print(f"Testing {tool['name']}...", end='', flush=True)
            res = test_tool(tool)
            results.append((tool['name'], res))
            print(f" {res['status']}")
        except Exception as e:
            print(f" ERROR: {e}")
            results.append((y.name, {'status': 'error', 'error': str(e)}))

    # Summary (same as before, omitted for brevity – keep your existing summary code)
    print_summary(results)

def print_summary(results):
    # (copy the summary code from the previous version here)
    pass  # placeholder

if __name__ == '__main__':
    main()