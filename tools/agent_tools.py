#!/usr/bin/env python3
"""
Tools for the agent – each function is a callable tool.
Uses browser-use 0.12.0 with persistent session and file upload.
"""

import subprocess
import json
import sys
import os
import asyncio
import tempfile
import requests
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

# MODERN BROWSER-USE IMPORTS (v0.12.0)
from browser_use import Agent, ChatOpenAI, Browser

TOOLS_DIR = Path(__file__).parent          # of this file, ie. .../dj2/tools/
PROJECT_ROOT = Path(__file__).parent       # and project root is parent of that .../dj2
LOG_FILE = TOOLS_DIR / 'agent_log.jsonl'

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
# Persistent Browser Setup (Long-running Chrome Pool)
# ----------------------------------------------------------------------
class ChromePool:
    """
    Manages connection to long-running Chrome instance.
    Chrome stays running; agents connect/disconnect ephemerally.
    """
    
    def __init__(self, cdp_port: int = 9222):
        self.cdp_port = cdp_port
        self._ws_url: str | None = None
        self._browser: Browser | None = None
        
    def _get_ws_endpoint(self) -> str:
        """Fetch WebSocket debugger URL from Chrome."""
        try:
            resp = requests.get(
                f"http://127.0.0.1:{self.cdp_port}/json/version",
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            ws_url = data.get("webSocketDebuggerUrl")
            if not ws_url:
                raise RuntimeError("No webSocketDebuggerUrl in response")
            print(f"[ChromePool] Connected to: {data.get('Browser', 'Unknown')}")
            return ws_url
        except requests.RequestException as e:
            raise RuntimeError(
                f"Cannot connect to Chrome at port {self.cdp_port}. "
                f"Is Chrome running with --remote-debugging-port={self.cdp_port}? "
                f"Error: {e}"
            )
    
    def get_browser(self) -> Browser:
        """Get or create Browser connection to existing Chrome."""
        if self._browser is None:
            ws_url = self._get_ws_endpoint()
            self._browser = Browser(cdp_url=ws_url)
        return self._browser
    
    async def disconnect(self):
        """Disconnect agent but leave Chrome running."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            log_event('browser_disconnect', {'status': 'agent_disconnected_chrome_running'})

# Global pool instance - Chrome stays running across agent sessions
_chrome_pool = ChromePool(cdp_port=9222)

def get_browser():
    """Get browser connection for agent use."""
    return _chrome_pool.get_browser()

async def disconnect_browser():
    """Call to release agent connection (Chrome stays up for watcher)."""
    await _chrome_pool.disconnect()

# ----------------------------------------------------------------------
# DeepSeek Consultation (Using Long-Running Chrome via CDP)
# ----------------------------------------------------------------------
def deepseek_consult(prompt, file=None, data=None, timeout=3600):
    """
    Consult DeepSeek using the working Playwright bridge.
    Connects to existing Chrome on port 9222.
    """
    # Import the working bridge
    from tools.bridge.deepseek_bridge_react import DeepSeekBridgeReact
    
    # Prepare content
    content = prompt
    if file:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read() + "\n\n" + prompt
        except Exception as e:
            log_event('file_read_error', str(e))
            return f"Error reading file: {e}"
    
    if data:
        data_str = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
        content = data_str + "\n\n" + content
    
    # Use working bridge
    bridge = DeepSeekBridgeReact(verbose=True)
    
    if not bridge.connect():
        return "Error: Could not connect to Chrome"
    
    # Add consultant prompt wrapper
    consultant_prompt = f"""You are DeepSeek, an expert AI assistant.

Analyze the following content thoroughly and provide detailed insights.
Wrap your complete response in [FINAL] and [/FINAL] tags.

Content to analyze:
{content}

Provide your analysis:"""

    # Send via file upload (working method)
    success = bridge.send_via_file_upload(consultant_prompt, filename="consultation.txt")
    
    if not success:
        bridge.close()
        return "Error: Failed to send to DeepSeek"
    
    # Get response
    response = bridge._wait_for_response(timeout=timeout)
    bridge.close()
    
    # Strip [FINAL] tags if present (agent will add its own)
    import re
    if response:
        response = re.sub(r'\[FINAL\](.*?)\[/FINAL\]', r'\1', response, flags=re.DOTALL).strip()
    
    return response or "No response received"

# ----------------------------------------------------------------------
# Watcher Integration: Safe History Reading
# ----------------------------------------------------------------------
def get_chrome_history(profile_dir: str = None, limit: int = 10):
    """
    Read Chrome history safely (copy DB first to avoid locks).
    Call this from your watcher, NOT the agent.
    """
    if profile_dir is None:
        profile_dir = r"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\DeepSeekAI"
    
    history_db = Path(profile_dir) / "History"
    if not history_db.exists():
        return []
    
    # Copy to temp location—Chrome locks the original
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        shutil.copy(history_db, tmp.name)
        tmp_path = tmp.name
    
    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, title, last_visit_time 
            FROM urls 
            ORDER BY last_visit_time DESC 
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            url, title, visit_time = row
            # Chrome timestamp is microseconds since 1601-01-01
            epoch_start = datetime(1601, 1, 1)
            visit_datetime = epoch_start + __import__('datetime').timedelta(microseconds=visit_time)
            results.append({
                "url": url,
                "title": title,
                "visited": visit_datetime.isoformat()
            })
        conn.close()
        return results
    finally:
        Path(tmp_path).unlink(missing_ok=True)

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
    from tools.analysis.intent_matcher import _get_top_files_for_intent

    db_path = PROJECT_ROOT / "ai_context" / "scout.db"
    if not db_path.exists():
        print(f"Warning: Embeddings DB not found at {db_path}", file=sys.stderr)
        return []

    results = _get_top_files_for_intent(query, db_path, max_files=limit)
    return [{"path": path, "score": score} for path, score, _ in results]

# ----------------------------------------------------------------------
# Architecture context using arch_recon
# ----------------------------------------------------------------------
def arch_context(query, level='standard'):
    """
    Generate a context package using arch_recon.py --context.
    Returns a JSON string with file snippets, behavioral contracts, and metadata.
    """
    cmd = [
        sys.executable,
        'tools/analysis/arch_recon.py',
        '--context', query,
        '--context-level', level,
        '--format', 'json'
    ]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"arch_context failed: {result.stderr}")
    return result.stdout

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

def upload_file(file_path):
    """
    Upload a single file to the active DeepSeek conversation.
    The file becomes part of the context for subsequent prompts.
    Returns confirmation.
    """
    # This is kept for compatibility; the new deepseek_consult handles upload automatically.
    # You may want to integrate it with the persistent browser, but for now it's a placeholder.
    return f"Uploaded {file_path} (simulated)"

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
        if line.startswith('[DEBUG]') or line.startswith('Found '):
            continue
        if '. ' in line:
            parts = line.split('. ', 1)
            if len(parts) == 2:
                rest = parts[1]
                if ' (score:' in rest:
                    path = rest.split(' (score:', 1)[0]
                else:
                    path = rest
                file_paths.append(path.strip())
            else:
                file_paths.append(line)
        else:
            file_paths.append(line)
    return file_paths

# ----------------------------------------------------------------------
# Git operations
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