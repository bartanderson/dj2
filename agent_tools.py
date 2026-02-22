#!/usr/bin/env python3
"""
Tools for the agent – each function is a callable tool.
Uses your existing bridge and analyzer.
"""

import subprocess
import json
import sys
from pathlib import Path

_deepseek_bridge = None
import atexit

PROJECT_ROOT = Path(__file__).parent

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
# DeepSeek consultation – uses your reliable Selenium bridge
# ----------------------------------------------------------------------
# Global persistent bridge instance


def _close_bridge():
    global _deepseek_bridge
    if _deepseek_bridge is not None:
        try:
            _deepseek_bridge.close()  # your existing close
        except:
            pass
        # Also kill any lingering chrome processes with this profile?
        # Optional: subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
        # But that would kill all Chrome instances – not ideal.
        _deepseek_bridge = None

atexit.register(_close_bridge)

def _ensure_bridge_alive():
    """Return a working bridge instance, recreating if dead."""
    global _deepseek_bridge
    print("DEBUG: _ensure_bridge_alive called")
    if _deepseek_bridge is None:
        print("DEBUG: bridge is None, creating new")
        from tools.bridge.bridge_controller import BridgeController
        _deepseek_bridge = BridgeController()
        return _deepseek_bridge

    # Health check – try to access the driver via the correct chain
    try:
        # BridgeController.bridge is DeepSeekBridgeReact, which has _core with driver
        driver = _deepseek_bridge.bridge._core.driver
        _ = driver.current_url  # will raise if dead
        print("DEBUG: bridge is alive")
        return _deepseek_bridge
    except Exception as e:
        print(f"DEBUG: bridge dead ({e}), recreating")
        try:
            _deepseek_bridge.close()
        except:
            pass
        from tools.bridge.bridge_controller import BridgeController
        _deepseek_bridge = BridgeController()
        return _deepseek_bridge

def deepseek_consult(prompt, file=None, data=None):
    """
    Send a prompt and optional context to DeepSeek using a persistent bridge.
    The bridge stays open across calls and is closed when the process exits.
    """
    global _deepseek_bridge
    print(f"DEBUG: deepseek_consult called, bridge exists: {_deepseek_bridge is not None}")
    bridge = _ensure_bridge_alive()
    print(f"DEBUG: after _ensure_bridge_alive, bridge: {bridge}")
    if _deepseek_bridge is None:
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from tools.bridge.bridge_controller import BridgeController
        _deepseek_bridge = BridgeController()

    # Build full prompt with context
    full_prompt = prompt
    if file:
        file_path = Path(file)
        if not file_path.is_absolute():
            file_path = Path(__file__).parent / file_path
        if file_path.exists():
            file_content = file_path.read_text(encoding='utf-8')
            full_prompt = f"File content:\n{file_content}\n\n{full_prompt}"
    if data:
        if isinstance(data, dict):
            data_str = json.dumps(data, indent=2)
        else:
            data_str = str(data)
        full_prompt = f"Data:\n{data_str}\n\n{full_prompt}"

    _ensure_bridge_alive()

    response = _deepseek_bridge.ask_deepseek(full_prompt, use_tools=False)
    if response is None:
        raise Exception("DeepSeek returned no response")
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

def write_file(path, content):
    """Write content to file. Creates a backup (.bak) if file exists."""
    full_path = PROJECT_ROOT / path
    if full_path.exists():
        backup = full_path.with_suffix('.bak')
        full_path.rename(backup)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding='utf-8')
    return f"Written {path}"

def search_files(query, limit=10, group=None):
    """
    Search for files using ai.py search command.
    Returns a list of file paths (relative to project root) matching the query.
    """
    import subprocess
    from pathlib import Path

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

    # Parse output: assume one file path per line, ignore empty lines
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return files

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