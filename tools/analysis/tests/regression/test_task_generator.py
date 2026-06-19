# tools/analysis/tests/regression/test_task_generator.py
#
# Locks in task.md generator (TRACKER item 10, step 1, 2026-06-19).
# Two-tier model: direct callers (graph_edges WHERE callee=?) and impact zone
# (route_query with seeds override). See TRACKER item 6 audit for rationale.

import os
import sqlite3
import tempfile
from dataclasses import dataclass, field
from typing import List

from tools.analysis.persistence.persistence_engine import ensure_schema

os.environ.setdefault("PYTHONPATH", ".")


# =========================================================
# MINIMAL GRAPH STUB
# =========================================================

@dataclass
class FakeEdge:
    caller: str
    callee: str


@dataclass
class FakeGraph:
    edges: List[FakeEdge] = field(default_factory=list)


# =========================================================
# FIXTURE
# =========================================================

def _make_db():
    """
    Real in-memory DB with schema.
    Graph: dispatcher -> handler -> helper
    We'll generate task.md for 'handler'.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=MEMORY")
    ensure_schema(conn)

    rows = [
        # (file_path, caller, callee, line_number, bucket)
        ("dispatch.py", "dispatcher", "handler", 10, "project"),
        ("handle.py",   "handler",   "helper",   20, "project"),
    ]
    for fp, caller, callee, line, bucket in rows:
        conn.execute(
            "INSERT INTO symbol_references (file_path, caller, callee, line_number, bucket) "
            "VALUES (?, ?, ?, ?, ?)",
            (fp, caller, callee, line, bucket),
        )
        conn.execute(
            "INSERT INTO graph_edges (source_id, target_id, caller, callee, line_number) "
            "VALUES (?, ?, ?, ?, ?)",
            (caller, callee, caller, callee, line),
        )
    conn.commit()
    return conn


def _make_graph():
    return FakeGraph(edges=[
        FakeEdge("dispatcher", "handler"),
        FakeEdge("handler", "helper"),
    ])


def _find_symbols_stub(text, limit=20):
    # Returns empty list - seeds override will bypass this anyway
    return []


# =========================================================
# TESTS
# =========================================================

def test_direct_callers_found():
    from tools.analysis.agent.task_generator import _direct_callers
    conn = _make_db()
    callers = _direct_callers(conn, "handler")
    assert len(callers) == 1
    assert callers[0]["caller"] == "dispatcher"
    assert "dispatch.py" in callers[0]["file_path"]


def test_direct_callers_empty_for_unknown_symbol():
    from tools.analysis.agent.task_generator import _direct_callers
    conn = _make_db()
    callers = _direct_callers(conn, "nonexistent_symbol")
    assert callers == []


def test_impact_zone_excludes_seed():
    from tools.analysis.agent.task_generator import _impact_zone
    graph = _make_graph()
    zone = _impact_zone("handler", graph, _find_symbols_stub, frozenset())
    assert "handler" not in zone


def test_generate_returns_markdown_string():
    from tools.analysis.agent.task_generator import generate_task_md
    conn = _make_db()
    graph = _make_graph()
    md = generate_task_md(
        symbol="handler",
        conn=conn,
        graph=graph,
        find_symbols_fn=_find_symbols_stub,
    )
    assert isinstance(md, str)
    assert "handler" in md
    assert "Direct callers (confirmed)" in md
    assert "Impact zone" in md


def test_direct_callers_appear_in_output():
    from tools.analysis.agent.task_generator import generate_task_md
    conn = _make_db()
    graph = _make_graph()
    md = generate_task_md("handler", conn, graph, _find_symbols_stub)
    assert "dispatcher" in md
    assert "dispatch.py" in md


def test_generate_writes_file():
    from tools.analysis.agent.task_generator import generate_task_md
    conn = _make_db()
    graph = _make_graph()
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        path = f.name
    try:
        generate_task_md("handler", conn, graph, _find_symbols_stub, out_path=path)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "handler" in content
        assert "Direct callers (confirmed)" in content
    finally:
        os.remove(path)


def test_assessor_generate_task_md_wired():
    from tools.analysis.oracle.db_oracle import DBOracle
    from tools.analysis.assessor.assessor import Assessor

    tmp = tempfile.mktemp(suffix=".db")
    try:
        oracle = DBOracle(tmp)
        ensure_schema(oracle.conn)
        oracle.conn.execute(
            "INSERT INTO symbol_references (file_path, caller, callee, line_number, bucket) "
            "VALUES ('a.py', 'caller_fn', 'target_fn', 5, 'project')"
        )
        oracle.conn.execute(
            "INSERT INTO graph_edges (source_id, target_id, caller, callee, line_number) "
            "VALUES ('caller_fn', 'target_fn', 'caller_fn', 'target_fn', 5)"
        )
        oracle.conn.commit()

        assessor = Assessor(oracle)
        md = assessor.generate_task_md("target_fn")
        assert "target_fn" in md
        assert "Direct callers (confirmed)" in md
        assert "caller_fn" in md
    finally:
        import os
        oracle.conn.close()
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == "__main__":
    tests = [
        test_direct_callers_found,
        test_direct_callers_empty_for_unknown_symbol,
        test_impact_zone_excludes_seed,
        test_generate_returns_markdown_string,
        test_direct_callers_appear_in_output,
        test_generate_writes_file,
        test_assessor_generate_task_md_wired,
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print("ALL TESTS PASSED")
