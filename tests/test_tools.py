import pytest
import time
from tools.agent_tools import arch_context, semantic_search, analyze_tools, retrieve_knowledge
from tools.knowledge_base import get_db

@pytest.fixture(autouse=True)
def clear_knowledge_db():
    """Clear the knowledge table before each test to ensure isolation."""
    conn = get_db()
    conn.execute("DELETE FROM knowledge")
    conn.commit()
    conn.close()

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