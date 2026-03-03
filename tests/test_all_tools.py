import pytest
import time
from tools.knowledge_base import get_db
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from tools import agent_tools
from tools.agent_tools import (
    search_files, read_file, read_files, write_file,
    analyze_tools, arch_context, deepseek_consult,
    semantic_search, create_branch, commit_changes,
    gather_context, show_diff, file_metadata,
    file_imports, file_importers, test_coverage as tool_test_coverage,  # alias to avoid name clash
    file_concepts, concept_files, cluster_files,
    function_contract, function_parameters, extract_code,
    list_functions, display_file, list_files,
    parse_json_file, retrieve_knowledge
)

# Fixture to clear the knowledge table before each test
@pytest.fixture(autouse=True)
def clear_knowledge_db():
    """Clear the knowledge table before each test to ensure isolation."""
    conn = get_db()
    conn.execute("DELETE FROM knowledge")
    conn.commit()
    conn.close()

# Fixture to create a temporary project root for file operations
@pytest.fixture
def tmp_project(tmp_path):
    # Simulate PROJECT_ROOT
    original_root = agent_tools.PROJECT_ROOT
    agent_tools.PROJECT_ROOT = tmp_path
    yield tmp_path
    agent_tools.PROJECT_ROOT = original_root

# Fixture to mock subprocess.run for tools that call external commands
@pytest.fixture
def mock_subprocess():
    with patch('subprocess.run') as mock:
        yield mock

# Fixture to mock database connections (for scout DB tools)
@pytest.fixture
def mock_db():
    with patch('tools.agent_tools._get_db_connection') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock, mock_conn, mock_cursor

def test_search_files(mock_subprocess):
    mock_subprocess.return_value.stdout = "1. tools/agent.py\n2. tools/agent_tools.py"
    mock_subprocess.return_value.returncode = 0
    result = search_files("test", limit=2)
    assert isinstance(result, list)
    assert "tools/agent.py" in result

def test_read_file(tmp_project):
    test_file = tmp_project / "test.txt"
    test_file.write_text("hello")
    result = read_file("test.txt")
    assert result == "hello"

def test_read_files(tmp_project):
    (tmp_project / "a.txt").write_text("A")
    (tmp_project / "b.txt").write_text("B")
    result = read_files(["a.txt", "b.txt", "missing.txt"])
    assert result == {
        "a.txt": "A",
        "b.txt": "B",
        "missing.txt": "File not found: missing.txt"
    }

def test_write_file(tmp_project):
    result = write_file("new.txt", "content")
    assert result == "Written new.txt"
    assert (tmp_project / "new.txt").read_text() == "content"

def test_list_files(tmp_project):
    (tmp_project / "file1.py").touch()
    (tmp_project / "file2.py").touch()
    (tmp_project / "subdir").mkdir()
    (tmp_project / "subdir/file3.py").touch()
    result = list_files(directory=".", pattern="*.py", recursive=True)
    # Normalize paths to use forward slashes for comparison
    normalized = [p.replace('\\', '/') for p in result]
    expected = {"file1.py", "file2.py", "subdir/file3.py"}
    assert set(normalized) == expected

def test_file_metadata(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = ("Core", 0, 100, '{"imported_by": []}')
    result = file_metadata("some/path.py")
    assert result["success"] is True
    assert result["data"]["role"] == "Core"

# Test for the tool 'test_coverage' (renamed to avoid conflict)
def test_tool_test_coverage(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = ("tests/test_file.py", 1)
    result = tool_test_coverage("some/path.py")
    assert result["success"] is True
    assert result["data"]["test_path"] == "tests/test_file.py"
    assert result["data"]["test_exists"] is True

def test_arch_context_caching():
    """Test that arch_context caches results correctly."""
    # First call should run the tool
    start = time.time()
    result1 = arch_context(query="character creation", level="standard")
    first_duration = time.time() - start

    # Second call should hit cache (much faster)
    start = time.time()
    result2 = arch_context(query="character creation", level="standard")
    second_duration = time.time() - start

    assert second_duration < first_duration / 2  # Cache should be significantly faster
    assert result1 == result2

    # Verify knowledge base entry
    entries = retrieve_knowledge(query="character creation")
    assert len(entries) >= 1
    assert entries[0]["tool_name"] == "arch_context"

def test_semantic_search_caching():
    """Test that semantic_search caches results correctly."""
    query = "world controller"
    limit = 3

    # First call
    start = time.time()
    result1 = semantic_search(query=query, limit=limit)
    first_duration = time.time() - start

    # Second call (cached)
    start = time.time()
    result2 = semantic_search(query=query, limit=limit)
    second_duration = time.time() - start

    assert second_duration < first_duration / 2
    assert result1 == result2

    entries = retrieve_knowledge(query=query)
    assert len(entries) >= 1
    assert entries[0]["tool_name"] == "semantic_search"

def test_analyze_tools_caching():
    """Test that analyze_tools caches results correctly."""
    # First call
    start = time.time()
    result1 = analyze_tools()
    first_duration = time.time() - start

    # Second call (cached)
    start = time.time()
    result2 = analyze_tools()
    second_duration = time.time() - start

    assert second_duration < first_duration / 2
    assert result1 == result2

    entries = retrieve_knowledge(query="ecosystem")  # concepts include "ecosystem"
    assert len(entries) >= 1
    assert entries[0]["tool_name"] == "analyze_tools"
    
def test_retrieve_knowledge_basic():
    """Test basic storage and retrieval of knowledge entries."""
    from tools.knowledge_base import store_knowledge_with_hash
    import uuid

    # Store a test entry
    thread_id = f"test_{uuid.uuid4().hex[:8]}"
    tool_name = "test_tool"
    query_text = "test query"
    concepts = ["test", "example"]
    result_data = {"key": "value"}
    params = {"param": 1}
    store_knowledge_with_hash(
        tool_name=tool_name,
        result=result_data,
        params=params,
        query=query_text,
        concepts=concepts,
        thread_id=thread_id
    )

    # Retrieve by thread_id
    entries = retrieve_knowledge(thread_id=thread_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["tool_name"] == tool_name
    assert entry["query_text"] == query_text
    assert entry["concepts"] == concepts
    assert entry["result_data"] == result_data
    assert entry["thread_id"] == thread_id

    # Retrieve by query (keyword search)
    entries = retrieve_knowledge(query="test")
    assert len(entries) >= 1

    # Retrieve by both
    entries = retrieve_knowledge(query="example", thread_id=thread_id)
    assert len(entries) == 1

def test_retrieve_knowledge_by_thread():
    """Test that knowledge can be retrieved by thread ID."""
    import uuid
    thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"

    # Run a tool with the thread_id
    result = arch_context(query="dungeon generation", thread_id=thread_id)

    # Retrieve by thread
    entries = retrieve_knowledge(thread_id=thread_id)
    assert len(entries) == 1
    assert entries[0]["thread_id"] == thread_id
    assert entries[0]["query_text"] == "dungeon generation"
# Add more tests for other tools as needed