#!/usr/bin/env python3
"""
Tools for the agent. Each function is a tool the AI can call.
"""

import subprocess
import json
import sys
from pathlib import Path

# Get project root (where agent.py lives)
PROJECT_ROOT = Path(__file__).parent

# ----------------------------------------------------------------------
# Analysis tool – uses your existing tool_analyzer
# ----------------------------------------------------------------------
def analyze_tools():
    """Run the existing tool_analyzer and return the full analysis dict."""
    tool_path = PROJECT_ROOT / 'tools' / 'tool_analyzer' / 'run.py'
    if not tool_path.exists():
        raise Exception(f"Analyzer not found at {tool_path}")
    # The tool expects a JSON argument, even if empty
    result = subprocess.run(
        [sys.executable, str(tool_path), "{}"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        raise Exception(f"Analyzer failed: {result.stderr}")
    return json.loads(result.stdout)

# ----------------------------------------------------------------------
# DeepSeek consultation – uses your bridge
# ----------------------------------------------------------------------
def deepseek_consult(prompt, file=None, data=None):
    """Send a prompt and optional context to DeepSeek. Returns response text."""
    bridge = PROJECT_ROOT / 'tools' / 'deepseek_bridge' / 'run.py'
    if not bridge.exists():
        raise Exception(f"DeepSeek bridge not found at {bridge}")
    payload = {'prompt': prompt}
    if file:
        # file can be a Path or string
        payload['file'] = str(file)
    if data:
        payload['data'] = data
    result = subprocess.run(
        [sys.executable, str(bridge), json.dumps(payload)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise Exception(f"DeepSeek bridge error: {result.stderr}")
    output = json.loads(result.stdout)
    if output.get('status') != 'success':
        raise Exception(f"DeepSeek error: {output.get('error')}")
    return output.get('data', '')

# ----------------------------------------------------------------------
# File operations
# ----------------------------------------------------------------------
def read_file(path):
    """Return content of file as string. Path relative to project root."""
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        raise Exception(f"File not found: {path}")
    return full_path.read_text(encoding='utf-8')

def write_file(path, content):
    """Write content to file (relative path). Creates a backup (.bak) if file exists."""
    full_path = PROJECT_ROOT / path
    if full_path.exists():
        backup = full_path.with_suffix('.bak')
        full_path.rename(backup)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding='utf-8')
    return f"Written {path}"

# ----------------------------------------------------------------------
# Git operations (from nativeclaw)
# ----------------------------------------------------------------------
def create_branch(branch_name):
    """Create a new git branch and switch to it."""
    subprocess.run(['git', 'checkout', '-b', branch_name], cwd=PROJECT_ROOT, check=True)
    return f"Switched to branch {branch_name}"

def commit_changes(message):
    """Commit all changes with message."""
    subprocess.run(['git', 'add', '.'], cwd=PROJECT_ROOT, check=True)
    subprocess.run(['git', 'commit', '-m', message], cwd=PROJECT_ROOT, check=True)
    return f"Committed: {message}"

def show_diff():
    """Return git diff of current changes."""
    result = subprocess.run(['git', 'diff'], cwd=PROJECT_ROOT, capture_output=True, text=True)
    return result.stdout