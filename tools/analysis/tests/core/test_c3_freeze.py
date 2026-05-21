# tools/analysis/tests/core/test_c3_freeze.py

import ast
import json
from pathlib import Path

from tools.analysis.run_analysis_pipeline import run_analysis_pipeline
from tools.analysis.graph.project_graph_context import ProjectGraphContext
from tools.analysis.graph.context_classification import classify_symbol_with_context


def extract_snapshot(output: str):
    marker = "===== EVALUATION SNAPSHOT ====="
    parts = output.split(marker)

    if len(parts) < 2:
        raise AssertionError("No evaluation snapshot found in output")

    snapshot_block = parts[-1].strip().splitlines()[0]
    return ast.literal_eval(snapshot_block)


def test_c3_freeze_creates_baseline(tmp_path, capsys):
    db_path = tmp_path / "freeze.db"
    baseline_path = Path("tools/analysis/tests/core/c3_baseline.json")

    # ----------------------------
    # RUN PIPELINE
    # ----------------------------
    run_analysis_pipeline(
        project_root="tools/analysis",
        database_path=db_path,
        project_prefixes=[],
    )

    # ----------------------------
    # CAPTURE OUTPUT
    # ----------------------------
    captured = capsys.readouterr()
    snapshot = extract_snapshot(captured.out)

    # ----------------------------
    # WRITE BASELINE (ONLY ONCE)
    # ----------------------------
    if not baseline_path.exists():
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)

    # ----------------------------
    # CLASSIFICATION SANITY CHECKS ONLY
    # ----------------------------
    ctx = ProjectGraphContext(
        project_prefixes=set(),
        runtime_bindings={},
        project_symbols={"test_example"},
    )

    assert classify_symbol_with_context("test_example", ctx) == "project"
    assert classify_symbol_with_context("print", ctx) == "builtin"

    # NOTE: no snapshot comparison yet (this is baseline creation phase)