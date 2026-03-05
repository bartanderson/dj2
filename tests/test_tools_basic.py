import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools import agent_tools
from tools.agent_tools import read_file, write_file, read_files, list_files, search_files

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def tmp_project(tmp_path):
    """Set PROJECT_ROOT to a temporary directory."""
    original_root = agent_tools.PROJECT_ROOT
    agent_tools.PROJECT_ROOT = tmp_path
    yield tmp_path
    agent_tools.PROJECT_ROOT = original_root

@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for tools that call external commands."""
    with patch('subprocess.run') as mock:
        yield mock

# ----------------------------------------------------------------------
# Tests for read_file
# ----------------------------------------------------------------------
def test_read_file_success(tmp_project):
    """read_file should return content of existing file."""
    test_file = tmp_project / "hello.txt"
    test_file.write_text("Hello, world!", encoding='utf-8')
    content = read_file("hello.txt")
    assert content == "Hello, world!"

def test_read_file_not_found(tmp_project):
    """read_file should raise exception for missing file."""
    with pytest.raises(Exception, match="File not found: missing.txt"):
        read_file("missing.txt")

# ----------------------------------------------------------------------
# Tests for write_file
# ----------------------------------------------------------------------
def test_write_file_new(tmp_project):
    """write_file should create a new file with content."""
    result = write_file("new.txt", "test content")
    assert result == "Written new.txt"
    assert (tmp_project / "new.txt").read_text(encoding='utf-8') == "test content"

def test_write_file_overwrite(tmp_project):
    """write_file should back up existing file and write new content."""
    original = tmp_project / "data.txt"
    original.write_text("original")
    result = write_file("data.txt", "new content")
    assert result == "Written data.txt"
    assert original.read_text(encoding='utf-8') == "new content"
    # Check backup exists
    backup = tmp_project / "data.txt.bak"
    assert backup.exists()
    assert backup.read_text(encoding='utf-8') == "original"

# ----------------------------------------------------------------------
# Tests for read_files (handles string, list, comma‑separated)
# ----------------------------------------------------------------------
def test_read_files_single_string(tmp_project):
    """read_files should accept a single path as string."""
    (tmp_project / "a.txt").write_text("A")
    result = read_files("a.txt")
    assert result == {"a.txt": "A"}

def test_read_files_list(tmp_project):
    """read_files should accept a list of paths."""
    (tmp_project / "a.txt").write_text("A")
    (tmp_project / "b.txt").write_text("B")
    result = read_files(["a.txt", "b.txt"])
    assert result == {"a.txt": "A", "b.txt": "B"}

def test_read_files_comma_separated(tmp_project):
    """read_files should accept a comma‑separated string."""
    (tmp_project / "x.txt").write_text("X")
    (tmp_project / "y.txt").write_text("Y")
    result = read_files("x.txt, y.txt")
    assert result == {"x.txt": "X", "y.txt": "Y"}

def test_read_files_missing(tmp_project):
    """read_files should return error message for missing files."""
    (tmp_project / "exists.txt").write_text("ok")   # <-- create first
    result = read_files(["exists.txt", "missing.txt"])
    assert result == {
        "exists.txt": "ok",
        "missing.txt": "File not found: missing.txt"
    }

# ----------------------------------------------------------------------
# Tests for list_files
# ----------------------------------------------------------------------
def test_list_files_basic(tmp_project):
    """list_files should return files matching pattern."""
    (tmp_project / "a.py").touch()
    (tmp_project / "b.txt").touch()
    (tmp_project / "sub").mkdir()
    (tmp_project / "sub/c.py").touch()
    result = list_files(directory=".", pattern="*.py", recursive=False)
    assert set(result) == {"a.py"}
    result = list_files(directory=".", pattern="*.py", recursive=True)
    # Normalize backslashes to forward slashes for comparison
    normalized = [p.replace('\\', '/') for p in result]
    assert set(normalized) == {"a.py", "sub/c.py"}

def test_list_files_ignore_patterns(tmp_project, monkeypatch):
    """list_files should ignore directories in IGNORE_PATTERNS."""
    # Override IGNORE_PATTERNS temporarily
    monkeypatch.setattr(agent_tools, 'IGNORE_PATTERNS', ['__pycache__'])
    (tmp_project / "file.py").touch()
    (tmp_project / "__pycache__").mkdir()
    (tmp_project / "__pycache__/cache.py").touch()
    result = list_files(recursive=True)
    assert "file.py" in result
    assert "__pycache__/cache.py" not in result

# ----------------------------------------------------------------------
# Tests for search_files (mocked subprocess)
# ----------------------------------------------------------------------
def test_search_files_success(mock_subprocess):
    """search_files should parse output and return list."""
    mock_subprocess.return_value.stdout = (
        "path/to/file1.py\n"
        "path/to/file2.py\n"
        "[DEBUG] some debug line\n"
    )
    mock_subprocess.return_value.returncode = 0
    result = search_files(query="test", limit=5)
    assert result == ["path/to/file1.py", "path/to/file2.py"]
    mock_subprocess.assert_called_once()

def test_search_files_with_params(mock_subprocess):
    """search_files should pass parameters to subprocess."""
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = ""
    search_files(query="test", limit=5, group="world", path="src", file_type="py")
    args = mock_subprocess.call_args[0][0]
    # Ignore the first argument (sys.executable)
    assert args[1:] == ['ai.py', 'search', 'test', '--limit', '5', '--group', 'world', '--path', 'src', '--file-type', 'py']
        
def test_search_files_failure(mock_subprocess):
    """search_files should raise exception on non‑zero return."""
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.stderr = "error"
    with pytest.raises(Exception, match="Search failed: error"):
        search_files(query="test")