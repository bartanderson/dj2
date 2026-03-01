#!/usr/bin/env python3
"""
Tools for the agent – each function is a callable tool.
Uses browser-use 0.12.0 with persistent session and file upload.
"""
import re
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
import ast

# MODERN BROWSER-USE IMPORTS (v0.12.0)
from browser_use import Agent, ChatOpenAI, Browser

# --- Correct path setup ---
TOOLS_DIR = Path(__file__).parent          # .../dj2/tools/
PROJECT_ROOT = TOOLS_DIR.parent             # .../dj2/   (project root)
LOG_FILE = TOOLS_DIR / 'agent_log.jsonl'    # keep log in tools/
# --------------------------

# ----------------------------------------------------------------------
# Logging (internal)
# ----------------------------------------------------------------------
def _log_event(event_type, data):
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
class _ChromePool:
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
            _log_event('browser_disconnect', {'status': 'agent_disconnected_chrome_running'})

# Global pool instance - Chrome stays running across agent sessions
_chrome_pool = _ChromePool(cdp_port=9222)

def _get_browser():
    """Get browser connection for agent use."""
    return _chrome_pool.get_browser()

async def _disconnect_browser():
    """Call to release agent connection (Chrome stays up for watcher)."""
    await _chrome_pool.disconnect()

# ----------------------------------------------------------------------
# DeepSeek Consultation (PUBLIC TOOL)
# ----------------------------------------------------------------------
def deepseek_consult(prompt, file=None, data=None, timeout=3600):
    """
    Consult DeepSeek using the local Playwright bridge.
    
    Args:
        prompt (str): The main question or instruction.
        file (str, optional): Path to a file to upload. Its content is NOT prepended; the file is uploaded separately.
        data (any, optional): Additional data to include in the prompt (converted to string).
        timeout (int): Maximum seconds to wait for response.
    
    Returns:
        str: The assistant's response, or an error message.
    """
    # Combine prompt and data
    full_prompt = prompt
    if data:
        data_str = json.dumps(data, indent=2) if isinstance(data, dict) else str(data)
        full_prompt = data_str + "\n\n" + prompt

    # Import our library
    from tools.bridge.deepseek_lib import full_consult

    # Generate a meaningful filename for any uploaded content
    import re
    safe_name = re.sub(r'[^\w\s-]', '', prompt[:30]).strip().replace(' ', '_')
    if not safe_name:
        safe_name = "consult"
    filename = f"{safe_name}.txt"

    try:
        if file:
            # Upload the file directly
            response = full_consult(prompt=full_prompt, file_path=file, timeout=timeout)
        else:
            # No file, just send the prompt
            response = full_consult(prompt=full_prompt, timeout=timeout)
        return response or "No response received"
    except Exception as e:
        logger.exception("DeepSeek consultation failed")
        return f"DeepSeek consultation failed: {e}"
        
# ----------------------------------------------------------------------
# Watcher Integration: Safe History Reading (internal, not a tool)
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
# Analysis tool – PUBLIC
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
# Display file – PUBLIC
# ----------------------------------------------------------------------
def display_file(path):
    """Alias for read_file – returns content of a file."""
    return read_file(path)

# ----------------------------------------------------------------------
# List files – PUBLIC
# ----------------------------------------------------------------------
def list_files(directory=".", pattern="*", recursive=False):
    """
    List files in a directory matching a pattern.
    Args:
        directory (str): relative path from project root
        pattern (str): glob pattern (e.g., "*.py")
        recursive (bool): whether to search subdirectories
    Returns:
        list of file paths (relative to project root)
    """
    from pathlib import Path
    base = PROJECT_ROOT / directory
    if recursive:
        files = base.rglob(pattern)
    else:
        files = base.glob(pattern)
    return [str(f.relative_to(PROJECT_ROOT)) for f in files if f.is_file()]

# ----------------------------------------------------------------------
# Semantic search – PUBLIC
# ----------------------------------------------------------------------
def semantic_search(query, limit=5):
    """
    Use embedding index to find files relevant to the query.
    Returns a list of dicts: [{"path": "file.py", "score": 0.95}, ...]
    """
    try:
        limit = int(limit)  # ensure integer
    except (TypeError, ValueError):
        limit = 5
        
    from tools.analysis.intent_matcher import _get_top_files_for_intent

    db_path = PROJECT_ROOT / "ai_context" / "scout.db"
    if not db_path.exists():
        print(f"Warning: Embeddings DB not found at {db_path}", file=sys.stderr)
        return []

    results = _get_top_files_for_intent(query, db_path, max_files=limit)
    # Convert score to float for JSON serialization
    return [{"path": path, "score": float(score)} for path, score, _ in results]

# ----------------------------------------------------------------------
# Architecture context – PUBLIC
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
# Gather context – PUBLIC
# ----------------------------------------------------------------------

def gather_context(topic, limit=5):
    """
    Gather comprehensive context about a topic.
    - Finds relevant files via semantic_search.
    - Reads their full content.
    - Returns a structured JSON object.
    """
    # 1. Get relevant files with scores
    files_with_scores = semantic_search(topic, limit)
    
    # 2. Extract paths
    paths = [item["path"] for item in files_with_scores]
    
    # 3. Read file contents
    contents = read_files(paths)
    
    # 4. Build context object
    context = {
        "topic": topic,
        "files": []
    }
    for item in files_with_scores:
        path = item["path"]
        context["files"].append({
            "path": path,
            "score": item["score"],
            "content": contents.get(path, "Error reading file")
        })
    
    return context

# ----------------------------------------------------------------------
# File operations – PUBLIC
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
# Search tool – PUBLIC
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
        if re.match(r'^-+$', line): # eliminate the --------------------- that are found in scraping tool output
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
# Git operations – PUBLIC
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

# ----------------------------------------------------------------------
# Newly added to create suite of tests
# ----------------------------------------------------------------------
def _get_db_connection():
    """Return a connection to the scout database, or None if DB doesn't exist."""
    db_path = PROJECT_ROOT / "ai_context" / "scout.db"
    if not db_path.exists():
        return None
    return sqlite3.connect(str(db_path))

def _error_response(message):
    """Return a standard error dictionary."""
    return {"success": False, "error": message}

def file_metadata(path):
    """
    Return metadata for a given file path.
    Returns dict with keys: success, error, data (role, is_hot, line_count, importers).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT role, is_hot, line_count, data FROM files WHERE path = ?", (path,))
        row = cur.fetchone()
        if not row:
            return _error_response(f"File '{path}' not found in database.")
        role, is_hot, line_count, data_json = row
        data = json.loads(data_json) if data_json else {}
        importers = data.get('imported_by', [])
        return {
            "success": True,
            "data": {
                "role": role,
                "is_hot": bool(is_hot),
                "line_count": line_count,
                "importers": importers
            }
        }
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def file_imports(path):
    """
    Return list of modules imported by the file.
    Returns dict with keys: success, error, data (list of module names).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT full_module FROM imports WHERE importer_path = ?", (path,))
        rows = cur.fetchall()
        modules = [r[0] for r in rows]
        return {"success": True, "data": modules}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def file_importers(path):
    """
    Return list of files that import the given file.
    Returns dict with keys: success, error, data (list of file paths).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        # Use the 'imported_by' field stored in the files table's JSON data
        cur = conn.cursor()
        cur.execute("SELECT data FROM files WHERE path = ?", (path,))
        row = cur.fetchone()
        if not row:
            return _error_response(f"File '{path}' not found.")
        data = json.loads(row[0]) if row[0] else {}
        importers = data.get('imported_by', [])
        return {"success": True, "data": importers}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def test_coverage(path):
    """
    Return test path and whether tests exist for a given file.
    Returns dict with keys: success, error, data (test_path, test_exists).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT test_path, test_exists FROM test_coverage WHERE source_path = ?", (path,))
        row = cur.fetchone()
        if not row:
            return {"success": True, "data": {"test_path": None, "test_exists": False}}
        test_path, test_exists = row
        return {
            "success": True,
            "data": {
                "test_path": test_path,
                "test_exists": bool(test_exists)
            }
        }
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def file_concepts(path):
    """
    Return list of concepts associated with a file.
    Returns dict with keys: success, error, data (list of concept strings).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT concept FROM concepts WHERE path = ?", (path,))
        rows = cur.fetchall()
        concepts = [r[0] for r in rows]
        return {"success": True, "data": concepts}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def concept_files(concept):
    """
    Return list of file paths associated with a given concept.
    Returns dict with keys: success, error, data (list of file paths).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM concepts WHERE concept = ?", (concept,))
        rows = cur.fetchall()
        files = [r[0] for r in rows]
        return {"success": True, "data": files}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def cluster_files(cluster_name):
    """
    Return list of file paths in a named cluster.
    Returns dict with keys: success, error, data (list of file paths).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT paths FROM clusters WHERE cluster_name = ?", (cluster_name,))
        row = cur.fetchone()
        if not row:
            return {"success": True, "data": []}
        files = json.loads(row[0]) if row[0] else []
        return {"success": True, "data": files}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def function_contract(path, function_name):
    """
    Return behavioral contract for a function or method.
    Returns dict with success, error, data containing description, side_effects,
    testable_behaviors, complexity_score.
    If no contract found, data is None.
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT description, side_effects, testable_behaviors, complexity_score
            FROM behavioral_contracts
            WHERE file_path = ? AND function_name = ?
        """, (path, function_name))  # column is file_path, parameter is path
        row = cur.fetchone()
        if not row:
            return {"success": True, "data": None}
        desc, side_effects_json, testable_json, complexity = row
        side_effects = json.loads(side_effects_json) if side_effects_json else []
        testable = json.loads(testable_json) if testable_json else []
        return {
            "success": True,
            "data": {
                "description": desc,
                "side_effects": side_effects,
                "testable_behaviors": testable,
                "complexity_score": complexity
            }
        }
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def function_parameters(path, function_name, class_name=None):
    """
    Return list of parameters for a function or method.
    Each parameter is a dict with keys: name, position.
    Returns dict with success, error, data (list).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        # Query method_params table; for __init__ we could also check class_constructors,
        # but we'll assume __init__ is stored as a method with name '__init__'.
        if class_name:
            cur.execute("""
                SELECT param_name, param_position
                FROM method_params
                WHERE file_path = ? AND class_name = ? AND method_name = ?
                ORDER BY param_position
            """, (path, class_name, function_name))
        else:
            cur.execute("""
                SELECT param_name, param_position
                FROM method_params
                WHERE file_path = ? AND class_name IS NULL AND method_name = ?
                ORDER BY param_position
            """, (path, function_name))
        rows = cur.fetchall()
        params = [{"name": r[0], "position": r[1]} for r in rows]
        return {"success": True, "data": params}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def extract_code(path, element_type, element_name):
    """
    Extract source code of a function or class from a file.
    element_type: 'function' or 'class'
    element_name: name of the function or class.
    Returns dict with success, error, data (source code string).
    """
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        return _error_response(f"File '{path}' does not exist.")
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if element_type == 'function' and isinstance(node, ast.FunctionDef) and node.name == element_name:
                start = node.lineno - 1
                end = node.end_lineno
                code = '\n'.join(lines[start:end])
                return {"success": True, "data": code}
            elif element_type == 'class' and isinstance(node, ast.ClassDef) and node.name == element_name:
                start = node.lineno - 1
                end = node.end_lineno
                code = '\n'.join(lines[start:end])
                return {"success": True, "data": code}
        return _error_response(f"{element_type} '{element_name}' not found in file.")
    except Exception as e:
        return _error_response(str(e))

def list_functions(path):
    """
    Return a list of function and method names in a file.
    Methods are returned as 'ClassName.method_name'.
    """
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        return _error_response(f"File not found: {path}")
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if inside a class
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef) and node in ast.walk(parent):
                        functions.append(f"{parent.name}.{node.name}")
                        break
                else:
                    functions.append(node.name)
        return {"success": True, "data": functions}
    except Exception as e:
        return _error_response(str(e))