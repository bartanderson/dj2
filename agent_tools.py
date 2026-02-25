#!/usr/bin/env python3
"""
Tools for the agent – each function is a callable tool.
Uses your existing bridge and analyzer.
"""

import subprocess
import json
import sys
import os
import atexit
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
LOG_FILE = PROJECT_ROOT / 'agent_log.jsonl'

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def log_event(event_type, data):
    """Append an event to the log file."""
    entry = {
        'timestamp': datetime.now().isoformat(timespec='milliseconds'),
        'type': event_type,
        'data': data
    }
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except:
        pass

# ----------------------------------------------------------------------
# Analysis tool – calls your existing tool_analyzer
# ----------------------------------------------------------------------
def analyze_tools():
    """Run the tool_analyzer and return the full analysis dict."""
    tool_path = PROJECT_ROOT / 'tools' / 'tool_analyzer' / 'run.py'
    if not tool_path.exists():
        raise Exception(f"Analyzer not found at {tool_path}")
    result = subprocess.run(
        [sys.executable, str(tool_path), "{}"],
        capture_output=True, text=True,
        cwd=PROJECT_ROOT
    )
    if result.returncode != 0:
        raise Exception(f"Analyzer failed: {result.stderr}")
    return json.loads(result.stdout)

# ----------------------------------------------------------------------
# Semantic search using intent_matcher
# ----------------------------------------------------------------------
def semantic_search(query, limit=5):
    """
    Use embedding index to find files relevant to the query.
    Returns a list of dicts: [{"path": "file.py", "score": 0.95}, ...]
    """
    # Import here to avoid circular imports
    from tools.analysis.intent_matcher import _get_top_files_for_intent

    # Path to the embeddings database (adjust if different)
    db_path = PROJECT_ROOT / "ai_context" / "embeddings.db"
    if not db_path.exists():
        # Fallback: maybe run indexer first? For now, warn and return empty.
        print(f"Warning: Embeddings DB not found at {db_path}", file=sys.stderr)
        return []

    results = _get_top_files_for_intent(query, db_path, max_files=limit)
    # results is list of (file_path, score, file_data)
    return [{"path": path, "score": score} for path, score, _ in results]

# ----------------------------------------------------------------------
# DeepSeek consultation – persistent bridge
# ----------------------------------------------------------------------
_deepseek_bridge = None

def _ensure_bridge_alive():
    """Return a working bridge instance, recreating if dead."""
    global _deepseek_bridge
    if _deepseek_bridge is None:
        from tools.bridge.bridge_controller import BridgeController
        _deepseek_bridge = BridgeController()
        log_event('bridge', 'created new bridge')
        return _deepseek_bridge

    # Health check – try to access driver via the correct chain
    try:
        # BridgeController.bridge is DeepSeekBridgeReact, which has _core with driver
        driver = _deepseek_bridge.bridge._core.driver
        _ = driver.current_url
        log_event('bridge', 'bridge is alive')
        return _deepseek_bridge
    except Exception as e:
        log_event('bridge', f'bridge dead ({e}), recreating')
        try:
            _deepseek_bridge.close()
        except:
            pass
        from tools.bridge.bridge_controller import BridgeController
        _deepseek_bridge = BridgeController()
        return _deepseek_bridge

def _close_bridge():
    global _deepseek_bridge
    if _deepseek_bridge is not None:
        try:
            _deepseek_bridge.close()
        except:
            pass
        _deepseek_bridge = None
        log_event('bridge', 'closed')

atexit.register(_close_bridge)

def deepseek_consult(prompt, file=None, data=None):
    """
    Send a prompt and optional context to DeepSeek using a persistent bridge.
    file: path to a file (relative to project root) whose content will be prepended.
    data: any extra data (dict/string) to include.
    Returns response string.
    """
    bridge = _ensure_bridge_alive()

    # Build full prompt with context
    full_prompt = prompt
    if file:
        file_path = Path(file)
        if not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path
        if file_path.exists():
            file_content = file_path.read_text(encoding='utf-8')
            full_prompt = f"File content:\n{file_content}\n\n{full_prompt}"
    if data:
        if isinstance(data, dict):
            data_str = json.dumps(data, indent=2)
        else:
            data_str = str(data)
        full_prompt = f"Data:\n{data_str}\n\n{full_prompt}"

    log_event('prompt', full_prompt)
    response = bridge.ask_deepseek(full_prompt, use_tools=False)
    if response is None:
        raise Exception("DeepSeek returned no response")
    log_event('response', response)
    return response

# ----------------------------------------------------------------------
# File operations
# ----------------------------------------------------------------------
def read_file(path):
    """Return content of file as string. Path relative to project root."""
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        raise Exception(f"File not found: {path}")
    return full_path.read_text(encoding='utf-8')

def read_files(file_paths):
    """
    Read multiple files and return a dictionary mapping file path to content.
    file_paths: list of paths (relative to project root).
    """
    contents = {}
    for path in file_paths:
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            contents[path] = full_path.read_text(encoding='utf-8')
        else:
            contents[path] = f"File not found: {path}"
    return contents

def write_file(path, content):
    """Write content to file. Creates a backup (.bak) if file exists."""
    full_path = PROJECT_ROOT / path
    if full_path.exists():
        backup = full_path.with_suffix('.bak')
        full_path.rename(backup)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding='utf-8')
    return f"Written {path}"

# ----------------------------------------------------------------------
# Search tool using ai.py search and return valid paths
# ----------------------------------------------------------------------
def search_files(query, limit=10, group=None):
    """
    Search for files using ai.py search command.
    Returns a list of file paths (relative to project root) matching the query.
    """
    cmd = [sys.executable, 'ai.py', 'search', query, '--limit', str(limit)]
    if group:
        cmd.extend(['--group', group])

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"Search failed: {result.stderr}")

    lines = result.stdout.splitlines()
    file_paths = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip debug lines
        if line.startswith('[DEBUG]') or line.startswith('Found '):
            continue

        # Extract the file path from lines like "1. world\\ai_dungeon_master.py (score: 33.973)"
        if '. ' in line:
            parts = line.split('. ', 1)
            if len(parts) == 2:
                rest = parts[1]
                # Remove the score part if present
                if ' (score:' in rest:
                    path = rest.split(' (score:', 1)[0]
                else:
                    path = rest
                file_paths.append(path.strip())
            else:
                # Fallback to whole line if format unexpected
                file_paths.append(line)
        else:
            file_paths.append(line)
    return file_paths

# ----------------------------------------------------------------------
# Git operations (from your nativeclaw code)
# ----------------------------------------------------------------------
def create_branch(branch_name):
    """Create and switch to a new git branch."""
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