import pytest
import tempfile
import ast
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from tools import agent_tools
from tools.agent_tools import (
    search_files, read_file, read_files, write_file,
    analyze_tools, arch_context, deepseek_consult,
    semantic_search, create_branch, commit_changes,
    gather_context, show_diff, file_metadata,
    file_imports, file_importers, test_coverage as tool_test_coverage,
    file_concepts, concept_files, cluster_files,
    function_contract, function_parameters, extract_code,
    list_functions, display_file, list_files,
    parse_json_file, retrieve_knowledge
)
from tools.knowledge_base import get_db, store_knowledge_with_hash

# Fixture to set temporary project root
@pytest.fixture
def tmp_project(tmp_path):
    original_root = agent_tools.PROJECT_ROOT
    agent_tools.PROJECT_ROOT = tmp_path
    yield tmp_path
    agent_tools.PROJECT_ROOT = original_root

# Fixture to mock subprocess.run
@pytest.fixture
def mock_subprocess():
    with patch('subprocess.run') as mock:
        yield mock

# Fixture to mock database connection
@pytest.fixture
def mock_db():
    with patch('tools.agent_tools._get_db_connection') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock, mock_conn, mock_cursor

# Fixture to clear knowledge DB before each test
@pytest.fixture(autouse=True)
def clear_knowledge_db():
    conn = get_db()
    conn.execute("DELETE FROM knowledge")
    conn.commit()
    conn.close()

# ----------------------------------------------------------------------
# Basic file and search tools
# ----------------------------------------------------------------------

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
    normalized = [p.replace('\\', '/') for p in result]
    expected = {"file1.py", "file2.py", "subdir/file3.py"}
    assert set(normalized) == expected

def test_display_file(tmp_project):
    test_file = tmp_project / "show.txt"
    test_file.write_text("show me")
    result = display_file("show.txt")
    assert result == "show me"

def test_parse_json_file(tmp_project):
    json_content = '{"key": "value", "list": [1,2,3]}'
    json_file = tmp_project / "data.json"
    json_file.write_text(json_content)
    result = parse_json_file("data.json")
    assert result == {"key": "value", "list": [1,2,3]}
    extracted = parse_json_file("data.json", extract_path="list[1]")
    assert extracted == 2

# ----------------------------------------------------------------------
# Tools that call external subprocesses
# ----------------------------------------------------------------------

def test_analyze_tools(mock_subprocess):
    mock_subprocess.return_value.stdout = '{"inventory": []}'
    mock_subprocess.return_value.returncode = 0
    result = analyze_tools()
    assert isinstance(result, dict)

def test_arch_context(mock_subprocess):
    mock_subprocess.return_value.stdout = '{"intent": "test"}'
    mock_subprocess.return_value.returncode = 0
    result = arch_context(query="test", level="standard")
    assert isinstance(result, dict)
    assert result["intent"] == "test"

def test_deepseek_consult():
    # Mock the deepseek_lib.full_consult function
    with patch('tools.bridge.deepseek_lib.full_consult') as mock_consult:
        mock_consult.return_value = "Mock response"
        result = deepseek_consult(prompt="Hello")
        assert result == "Mock response"

def test_create_branch(mock_subprocess):
    result = create_branch("test-branch")
    assert result == "Switched to branch test-branch"
    mock_subprocess.assert_called_once()

def test_commit_changes(mock_subprocess):
    result = commit_changes("Test commit")
    assert result == "Committed: Test commit"
    assert mock_subprocess.call_count == 2  # git add and git commit

def test_show_diff(mock_subprocess):
    mock_subprocess.return_value.stdout = "diff --git a/file b/file"
    result = show_diff()
    assert result == "diff --git a/file b/file"

# ----------------------------------------------------------------------
# Scout database tools
# ----------------------------------------------------------------------

def test_file_metadata(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = ("Core", 0, 100, '{"imported_by": []}')
    result = file_metadata("some/path.py")
    assert result["success"] is True
    assert result["data"]["role"] == "Core"

def test_file_imports(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchall.return_value = [("os",), ("sys",)]
    result = file_imports("some/path.py")
    assert result["success"] is True
    assert result["data"] == ["os", "sys"]

def test_file_importers(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = ('{"imported_by": ["a.py", "b.py"]}',)
    result = file_importers("some/path.py")
    assert result["success"] is True
    assert result["data"] == ["a.py", "b.py"]

def test_test_coverage_tool(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = ("tests/test_file.py", 1)
    result = tool_test_coverage("some/path.py")
    assert result["success"] is True
    assert result["data"]["test_path"] == "tests/test_file.py"
    assert result["data"]["test_exists"] is True

def test_file_concepts(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchall.return_value = [("concept1",), ("concept2",)]
    result = file_concepts("some/path.py")
    assert result["success"] is True
    assert result["data"] == ["concept1", "concept2"]

def test_concept_files(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchall.return_value = [("a.py",), ("b.py",)]
    result = concept_files("concept")
    assert result["success"] is True
    assert result["data"] == ["a.py", "b.py"]

def test_cluster_files_with_name(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = ('["a.py", "b.py"]',)
    result = cluster_files(cluster_name="test")
    assert result["success"] is True
    assert result["data"] == ["a.py", "b.py"]

def test_cluster_files_without_name(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchall.return_value = [("c1",), ("c2",)]
    result = cluster_files()
    assert result["success"] is True
    assert result["data"] == ["c1", "c2"]

def test_function_contract(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchone.return_value = (
        "Test function",
        '["side effect"]',
        '["behavior"]',
        5
    )
    result = function_contract("path.py", "func")
    assert result["success"] is True
    assert result["data"]["description"] == "Test function"
    assert result["data"]["side_effects"] == ["side effect"]
    assert result["data"]["testable_behaviors"] == ["behavior"]
    assert result["data"]["complexity_score"] == 5

def test_function_parameters(mock_db):
    mock_cursor = mock_db[2]
    mock_cursor.fetchall.return_value = [("x", 0), ("y", 1)]
    result = function_parameters("path.py", "func")
    assert result["success"] is True
    assert result["data"] == [{"name": "x", "position": 0}, {"name": "y", "position": 1}]

# ----------------------------------------------------------------------
# Tools that parse Python code
# ----------------------------------------------------------------------

def test_extract_code(tmp_project):
    code = '''
def hello():
    print("world")

class Test:
    def method(self):
        pass
'''
    py_file = tmp_project / "sample.py"
    py_file.write_text(code)

    func_result = extract_code("sample.py", "function", "hello")
    if not func_result["success"]:
        print("Error in extract_code:", func_result.get("error"))
    assert func_result["success"] is True
    assert "def hello():" in func_result["data"]

    class_result = extract_code("sample.py", "class", "Test")
    if not class_result["success"]:
        print("Error in extract_code (class):", class_result.get("error"))
    assert class_result["success"] is True
    assert "class Test:" in class_result["data"]

def test_list_functions(tmp_project):
    code = '''
def global_func():
    pass

class Cls:
    def method(self):
        pass
'''
    py_file = tmp_project / "sample.py"
    py_file.write_text(code)

    result = list_functions("sample.py")
    if not result["success"]:
        print("Error in list_functions:", result.get("error"))
    assert result["success"] is True
    functions = result["data"]
    assert "global_func" in functions
    assert "Cls.method" in functions
    assert len(functions) == 2
# ----------------------------------------------------------------------
# Semantic and context gathering tools
# ----------------------------------------------------------------------

def test_semantic_search():
    # Mock the underlying _get_top_files_for_intent from intent_matcher
    with patch('tools.analysis.intent_matcher._get_top_files_for_intent') as mock_get:
        mock_get.return_value = [("a.py", 0.9, {}), ("b.py", 0.8, {})]
        result = semantic_search("test query", limit=2)
        assert result == [{"path": "a.py", "score": 0.9}, {"path": "b.py", "score": 0.8}]

def test_gather_context():
    # Mock semantic_search and read_files
    with patch('tools.agent_tools.semantic_search') as mock_semantic, \
         patch('tools.agent_tools.read_files') as mock_read:
        mock_semantic.return_value = [{"path": "a.py", "score": 0.9}, {"path": "b.py", "score": 0.8}]
        mock_read.return_value = {"a.py": "content A", "b.py": "content B"}
        result = gather_context("test topic", limit=2)
        assert result["topic"] == "test topic"
        assert len(result["files"]) == 2
        assert result["files"][0]["path"] == "a.py"
        assert result["files"][0]["content"] == "content A"

# ----------------------------------------------------------------------
# Knowledge base retrieval tests
# ----------------------------------------------------------------------

def test_retrieve_knowledge_basic():
    """Test basic storage and retrieval of knowledge entries."""
    import uuid
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

    entries = retrieve_knowledge(thread_id=thread_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["tool_name"] == tool_name
    assert entry["query_text"] == query_text
    assert entry["concepts"] == concepts
    assert entry["result_data"] == result_data
    assert entry["thread_id"] == thread_id

    entries = retrieve_knowledge(query="test")
    assert len(entries) >= 1

    entries = retrieve_knowledge(query="example", thread_id=thread_id)
    assert len(entries) == 1

def test_retrieve_knowledge_by_thread():
    """Test that knowledge can be retrieved by thread ID from an actual tool call."""
    import uuid
    thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
    with patch('tools.agent_tools.subprocess.run') as mock_sub:
        mock_sub.return_value.stdout = '{"intent": "dungeon generation"}'
        mock_sub.return_value.returncode = 0
        result = arch_context(query="dungeon generation", thread_id=thread_id)

    entries = retrieve_knowledge(thread_id=thread_id)
    assert len(entries) == 1
    assert entries[0]["thread_id"] == thread_id
    assert entries[0]["query_text"] == "dungeon generation"