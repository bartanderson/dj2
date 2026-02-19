#!/usr/bin/env python3
"""
Tool Diagnostic: Test all registered tools with a short timeout.
Runs each tool's script with --help (or a simple command) and reports success/failure.
"""

import os
import sys
import subprocess
import yaml
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TIMEOUT = 10  # seconds

def find_tool_yamls(root):
    """Recursively find all tool.yaml files."""
    return list(root.rglob('tool.yaml'))

def load_tool_info(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return {
        'name': data.get('name', yaml_path.parent.name),
        'path': data.get('path'),
        'execution': data.get('execution', 'cli'),
        'yaml': yaml_path
    }

def test_tool(tool):
    """Run the tool's script with --help and return status."""
    if tool['execution'] != 'cli':
        return {'status': 'skipped', 'reason': 'non-CLI tool'}
    
    script_path_str = tool.get('path')
    if not script_path_str:
        return {'status': 'missing', 'reason': 'no path specified in tool.yaml'}
    
    script_path = PROJECT_ROOT / script_path_str
    if not script_path.exists():
        return {'status': 'missing', 'reason': f'script not found: {script_path}'}
    
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
            return {'status': 'failed', 'elapsed': elapsed, 'returncode': result.returncode, 'stderr': result.stderr[:200]}
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {'status': 'timeout', 'elapsed': elapsed}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def main():
    tool_yamls = find_tool_yamls(PROJECT_ROOT)
    print(f"Found {len(tool_yamls)} tool definitions.\n")
    results = []
    for yaml_path in tool_yamls:
        try:
            tool = load_tool_info(yaml_path)
            print(f"Testing {tool['name']}...", end='', flush=True)
            res = test_tool(tool)
            results.append((tool['name'], res))
            print(f" {res['status']}")
        except Exception as e:
            print(f" ERROR: {e}")
            results.append((yaml_path.name, {'status': 'error', 'error': str(e)}))

    # Summary
    print("\n" + "="*60)
    print("TOOL HEALTH SUMMARY")
    print("="*60)
    ok = [r for r in results if r[1]['status'] == 'ok']
    failed = [r for r in results if r[1]['status'] == 'failed']
    timeout = [r for r in results if r[1]['status'] == 'timeout']
    missing = [r for r in results if r[1]['status'] == 'missing']
    skipped = [r for r in results if r[1]['status'] == 'skipped']
    error = [r for r in results if r[1]['status'] == 'error']
    print(f"✅ OK: {len(ok)}")
    for name, res in ok:
        print(f"   {name} ({res['elapsed']:.2f}s)")
    if failed:
        print(f"\n❌ Failed ({len(failed)}):")
        for name, res in failed:
            print(f"   {name} (code {res['returncode']}) - {res.get('stderr','')[:60]}")
    if timeout:
        print(f"\n⏰ Timeout ({len(timeout)}):")
        for name, res in timeout:
            print(f"   {name} (>={TIMEOUT}s)")
    if missing:
        print(f"\n⚠️  Missing script ({len(missing)}):")
        for name, res in missing:
            print(f"   {name} - {res['reason']}")
    if skipped:
        print(f"\n⏭️  Skipped ({len(skipped)}):")
        for name, res in skipped:
            print(f"   {name} - {res['reason']}")
    if error:
        print(f"\n💥 Errors ({len(error)}):")
        for name, res in error:
            print(f"   {name} - {res['error']}")

if __name__ == '__main__':
    main()