# tools/analysis/tests/regression/test_local_agent.py
#
# Smoke tests for local_agent.py. Does not call Ollama - patches the
# Ollama call to return controlled responses and verifies the ReAct loop
# behaves correctly.

import sys
from unittest.mock import patch

# ------------------------------------------------------------------
# Minimal stubs
# ------------------------------------------------------------------

class _FakeOracle:
    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.db_path = None
    def get_project_root(self): return "/project"
    def find_symbols(self, *a, **kw): return []
    def find_files(self, *a, **kw): return []
    def get_edge_maps(self): return {}, {}
    def builtin_symbols(self): return frozenset()
    def discover_seed_symbols(self, *a, **kw): return []


class _FakeAssessor:
    def __init__(self, oracle):
        self._oracle = oracle
        self._knowledge_conn = None
    def ask(self, q):
        class R:
            def get_field(self, k): return "[stub]"
        return R()
    def semantic_summary(self, *a, **kw):
        return {"content": "stub summary", "cache_hit": False}
    def generate_task_md(self, symbol, **kw):
        return f"# task: {symbol}\n## Direct callers (confirmed)\n- stub\n## Impact zone\n- stub\n"
    def get_artifacts(self, *a): return []
    def add_artifact(self, *a): pass


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_import_succeeds():
    import tools.analysis.agent.local_agent  # noqa: F401


def test_answer_returns_direct_response_when_no_tool_call():
    """When model returns plain text (no TOOL: block), it's the final answer."""
    from tools.analysis.agent.local_agent import _answer
    oracle = _FakeOracle()
    assessor = _FakeAssessor(oracle)

    with patch("tools.analysis.agent.local_agent._call_ollama",
               return_value="The encounter system lives in encounter_generator.py."):
        answer, history = _answer("what is the encounter system?", [], oracle, assessor)

    assert "encounter_generator" in answer
    assert len(history) == 2  # user + assistant
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_answer_executes_tool_then_answers():
    """Model calls a tool, gets result, then answers without another tool call."""
    from tools.analysis.agent.local_agent import _answer
    oracle = _FakeOracle()
    assessor = _FakeAssessor(oracle)

    responses = iter([
        'TOOL: search_symbols\nARGS: {"query": "encounter"}',
        "Based on the results, the encounter system has generate_encounter.",
    ])

    with patch("tools.analysis.agent.local_agent._call_ollama",
               side_effect=lambda msgs, verbose=False: next(responses)):
        answer, history = _answer("what is the encounter system?", [], oracle, assessor)

    assert "generate_encounter" in answer or "encounter" in answer.lower()
    assert len(history) == 2


def test_answer_respects_tool_limit():
    """If model keeps calling tools past MAX_TOOL_TURNS, loop forces final answer."""
    from tools.analysis.agent.local_agent import _answer, MAX_TOOL_TURNS
    oracle = _FakeOracle()
    assessor = _FakeAssessor(oracle)

    call_count = {"n": 0}

    def _always_tool(msgs, verbose=False):
        call_count["n"] += 1
        if call_count["n"] > MAX_TOOL_TURNS:
            return "Here is my final answer after all those tool calls."
        return 'TOOL: search_symbols\nARGS: {"query": "x"}'

    with patch("tools.analysis.agent.local_agent._call_ollama", side_effect=_always_tool):
        answer, history = _answer("keep calling tools", [], oracle, assessor)

    assert call_count["n"] == MAX_TOOL_TURNS + 1
    assert "final answer" in answer.lower()


def test_answer_preserves_history_across_turns():
    """History from first question is available as context for second question."""
    from tools.analysis.agent.local_agent import _answer
    oracle = _FakeOracle()
    assessor = _FakeAssessor(oracle)

    with patch("tools.analysis.agent.local_agent._call_ollama",
               return_value="The travel system handles movement."):
        _, history = _answer("what is the travel system?", [], oracle, assessor)

    with patch("tools.analysis.agent.local_agent._call_ollama",
               return_value="It connects to the encounter system."):
        _, history = _answer("how does it connect?", history, oracle, assessor)

    assert len(history) == 4  # 2 turns * (user + assistant)
    assert history[0]["content"] == "what is the travel system?"


def test_ollama_connection_error_returns_message():
    """If Ollama is down, _answer returns a readable error, not an exception."""
    from tools.analysis.agent.local_agent import _answer
    import requests
    oracle = _FakeOracle()
    assessor = _FakeAssessor(oracle)

    with patch("tools.analysis.agent.local_agent._call_ollama",
               return_value="ERROR: Ollama is not running. Start it with: ollama serve"):
        answer, history = _answer("anything", [], oracle, assessor)

    assert "ERROR" in answer
    assert len(history) == 0  # error before any history appended


# ------------------------------------------------------------------
# RUN DIRECTLY
# ------------------------------------------------------------------

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  FAIL  {t.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
