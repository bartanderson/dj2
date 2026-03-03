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
import tempfile
import requests
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from browser_use import Browser

# --- Correct path setup ---
TOOLS_DIR = Path(__file__).parent          # .../dj2/tools/
PROJECT_ROOT = TOOLS_DIR.parent             # .../dj2/   (project root)
LOG_FILE = TOOLS_DIR / 'agent_log.jsonl'    # keep log in tools/
# --------------------------
# Ignore patterns for filtering files (copied from arch_recon)
IGNORE_PATTERNS = ['__pycache__', 'venv', '.git', 'node_modules', 'Lib', 'docs', 'archive']

def _should_ignore(rel_path: str) -> bool:
    """Return True if path contains any ignore pattern."""
    path_lower = rel_path.lower()
    for pattern in IGNORE_PATTERNS:
        if pattern.lower() in path_lower:
            return True
    return False
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
    Consult DeepSeek AI via browser automation.
    Use this for any task requiring AI reasoning, content generation, or answering questions.
    Can optionally upload a file for context.
    
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

    from tools.bridge.deepseek_lib import full_consult

    import re
    safe_name = re.sub(r'[^\w\s-]', '', prompt[:30]).strip().replace(' ', '_')
    if not safe_name:
        safe_name = "consult"
    filename = f"{safe_name}.txt"

    try:
        if file:
            response = full_consult(prompt=full_prompt, file_path=file, timeout=timeout)
        else:
            response = full_consult(prompt=full_prompt, timeout=timeout)
        return response or "No response received"
    except Exception as e:
        import sys
        print(f"DeepSeek consultation failed: {e}", file=sys.stderr)
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
    """
    Run the tool analyzer to get a complete landscape report of all tools in the project.
    Use this to understand the tool ecosystem, find hotspots, orphans, duplicates, and get recommendations.
    
    Returns:
        dict: A comprehensive report containing inventory, summary, hotspots, orphans, duplicates, and recommendations.
    """
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
# Display file – PUBLIC (alias for read_file)
# ----------------------------------------------------------------------
def display_file(path):
    """
    Display the contents of a file. Alias for read_file.
    
    Args:
        path (str): Path to the file, relative to project root.
    
    Returns:
        str: File content.
    """
    return read_file(path)

# ----------------------------------------------------------------------
# List files – PUBLIC
# ----------------------------------------------------------------------
def list_files(directory=".", pattern="*", recursive=False):
    """
    List files by filename pattern using glob.
    Use this for queries about filenames, extensions, or directories.
    Examples: "list all Python files" recursive=True, "find .txt files in docs folder" default, "show files in tools directory" default.
    
    Args:
        directory (str): Directory to search, relative to project root. Default: "."
        pattern (str): File pattern (e.g., "*.py", "*.txt", "config.*"). Default: "*"
        recursive (bool): Whether to search subdirectories. True if "all" files requested. Default: False
    
    Returns:
        list: File paths relative to project root, excluding common ignored directories (__pycache__, venv, .git, etc.).
    """

    base = PROJECT_ROOT / directory
    if recursive:
        files = base.rglob(pattern)
    else:
        files = base.glob(pattern)
    
    result = []
    for f in files:
        if not f.is_file():
            continue
        rel = str(f.relative_to(PROJECT_ROOT))
        if not _should_ignore(rel):
            result.append(rel)
    
    print(f"[list_files] Found {len(result)} files")
    return result

# ----------------------------------------------------------------------
# Semantic search – PUBLIC
# ----------------------------------------------------------------------
def semantic_search(query, limit=5):
    """
    Semantic search for files based on conceptual content, not filename.
    Use this to find files that discuss a topic, implement a feature, or contain related ideas.
    Examples: "files related to character creation", "where is the DM agent defined?", "concept movement in dungeon".
    
    Args:
        query (str): Natural language description of what you're looking for.
        limit (int): Maximum number of results. Default: 5
    
    Returns:
        list: List of dicts with 'path' and 'score', ranked by relevance.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5
        
    from tools.analysis.intent_matcher import _get_top_files_for_intent

    db_path = PROJECT_ROOT / "ai_context" / "scout.db"
    if not db_path.exists():
        print(f"Warning: Embeddings DB not found at {db_path}", file=sys.stderr)
        return []

    results = _get_top_files_for_intent(query, db_path, max_files=limit)
    return [{"path": path, "score": float(score)} for path, score, _ in results]

# ----------------------------------------------------------------------
# Architecture context – PUBLIC
# ----------------------------------------------------------------------
def arch_context(query=None, level='standard'):
    """
    Generate an architecture context package for a given intent.
    Use this when you need deep understanding of a feature or area.
    
    Args:
        query (str, required): Intent or topic, e.g., "character creation".
        level (str): Detail level: 'brief', 'standard', or 'deep'. Default: 'standard'.
    
    Returns:
        str: JSON string with file snippets, behavioral contracts, and metadata.
    """
    if query is None:
        return "Error: arch_context requires a 'query' argument (the topic to analyze)."
    cmd = [
        sys.executable,
        'tools/analysis/arch_recon.py',
        '--context', query,
        '--context-level', level,
        '--format', 'json',
        '--no-prompt'  # Prevent interactive prompts
    ]
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return f"Error executing arch_context: {result.stderr}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: arch_context timed out after 30 seconds. The subprocess may be hung."
    except Exception as e:
        return f"Error executing arch_context: {e}"

# ----------------------------------------------------------------------
# Gather context – PUBLIC
# ----------------------------------------------------------------------
def gather_context(topic, limit=5):
    """
    Gather comprehensive context about a topic.
    Finds relevant files via semantic_search and reads their full content.
    Use this when you need to understand the code related to a concept.
    
    Args:
        topic (str): The topic or concept.
        limit (int): Maximum number of files to include. Default: 5
    
    Returns:
        dict: Contains 'topic' and 'files' list with path, score, and content.
    """
    files_with_scores = semantic_search(topic, limit)
    paths = [item["path"] for item in files_with_scores]
    contents = read_files(paths)
    
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
    """
    Read a file and return its content.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        str: File content.
    """
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        raise Exception(f"File not found: {path}")
    return full_path.read_text(encoding='utf-8')

def read_files(file_paths):
    """
    Read multiple files and return a dict mapping path to content.
    
    Args:
        file_paths (list): List of paths relative to project root.
    
    Returns:
        dict: {path: content}
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
    """
    Write content to a file. Creates a backup (.bak) if file exists.
    
    Args:
        path (str): Path relative to project root.
        content (str): Content to write.
    
    Returns:
        str: Confirmation message.
    """
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
    Search for files using a text‑based command (ai.py search). This is a simple wrapper around a CLI tool.
    Prefer semantic_search for conceptual queries, but use this for exact keyword searches if needed.
    
    Args:
        query (str): Keyword or phrase to search for in file names/paths.
        limit (int): Maximum number of results.
        group (str, optional): Filter by code group (e.g., 'world', 'engine').
    
    Returns:
        list: File paths relative to project root.
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
        if re.match(r'^-+$', line):
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
    """
    Create and switch to a new git branch.
    
    Args:
        branch_name (str): Name of the new branch.
    
    Returns:
        str: Confirmation message.
    """
    subprocess.run(['git', 'checkout', '-b', branch_name], cwd=PROJECT_ROOT, check=True)
    return f"Switched to branch {branch_name}"

def commit_changes(message):
    """
    Commit all changes with a message.
    
    Args:
        message (str): Commit message.
    
    Returns:
        str: Confirmation message.
    """
    subprocess.run(['git', 'add', '.'], cwd=PROJECT_ROOT, check=True)
    subprocess.run(['git', 'commit', '-m', message], cwd=PROJECT_ROOT, check=True)
    return f"Committed: {message}"

def show_diff():
    """
    Show git diff of current changes (unstaged and staged).
    
    Returns:
        str: Diff output.
    """
    result = subprocess.run(['git', 'diff'], cwd=PROJECT_ROOT, capture_output=True, text=True)
    return result.stdout

# ----------------------------------------------------------------------
# Database query tools (require scout DB)
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
    Get metadata for a file from the scout database.
    Use this to understand a file's role, whether it's "hot", line count, and what imports it.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        dict: Contains success, error (if any), and data with role, is_hot, line_count, importers.
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
    Get list of modules imported by a file.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        dict: success, error, data (list of module names).
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
    Get list of files that import the given file.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        dict: success, error, data (list of file paths).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
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
    Check if a file has a corresponding test.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        dict: success, error, data with test_path and test_exists.
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
    Get concepts (topics) associated with a file from the scout DB.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        dict: success, error, data (list of concept strings).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT concept FROM concepts WHERE file_path = ?", (path,))
        rows = cur.fetchall()
        concepts = [r[0] for r in rows]
        return {"success": True, "data": concepts}
    except Exception as e:
        return _error_response(str(e))
    finally:
        conn.close()

def concept_files(concept):
    """
    Find all files associated with a given concept.
    
    Args:
        concept (str): Concept word.
    
    Returns:
        dict: success, error, data (list of file paths).
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
    Get all files in a named cluster (from discovered categories).
    
    Args:
        cluster_name (str): Name of the cluster.
    
    Returns:
        dict: success, error, data (list of file paths).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
        cur.execute("SELECT file_paths FROM clusters WHERE cluster_name = ?", (cluster_name,))
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
    Get the behavioral contract of a function (description, side effects, testable behaviors, complexity).
    
    Args:
        path (str): Path relative to project root.
        function_name (str): Name of the function (or method in format ClassName.method).
    
    Returns:
        dict: success, error, data with contract info (or None if not found).
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
        """, (path, function_name))
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
    Get parameters of a function or method.
    
    Args:
        path (str): Path relative to project root.
        function_name (str): Function or method name.
        class_name (str, optional): If it's a method, provide the class name.
    
    Returns:
        dict: success, error, data (list of params with name and position).
    """
    conn = _get_db_connection()
    if not conn:
        return _error_response("Database not found. Run scout first.")
    try:
        cur = conn.cursor()
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

def parse_json_file(file_path: str, extract_path: str = None):
    """
    Parse a JSON file and optionally extract a sub‑path (dot notation with slices).
    """
    full_path = PROJECT_ROOT / file_path
    if not full_path.exists():
        raise Exception(f"File not found: {file_path}")

    with open(full_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if extract_path:
        parts = extract_path.split('.')
        for part in parts:
            if '[' in part and ']' in part:
                name, slice_str = part.split('[')
                slice_str = slice_str.rstrip(']')
                data = data[name]
                if ':' in slice_str:
                    start, end = map(int, slice_str.split(':'))
                    data = data[start:end]
                else:
                    idx = int(slice_str)
                    data = data[idx]
            else:
                data = data[part]
    return data

def extract_code(path, element_type, element_name):
    """
    Extract the source code of a function or class from a file.
    
    Args:
        path (str): Path relative to project root.
        element_type (str): 'function' or 'class'.
        element_name (str): Name of the element.
    
    Returns:
        dict: success, error, data (source code string).
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
    List all functions and methods in a file.
    Methods are returned as 'ClassName.method_name'.
    
    Args:
        path (str): Path relative to project root.
    
    Returns:
        dict: success, error, data (list of function/method names).
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
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef) and node in ast.walk(parent):
                        functions.append(f"{parent.name}.{node.name}")
                        break
                else:
                    functions.append(node.name)
        return {"success": True, "data": functions}
    except Exception as e:
        return _error_response(str(e))