# t.py
# simple health shell

from tools.analysis.engine.run_engine import EngineRunner
from tools.analysis.tests.observability.system_health import compute_health, print_health
import sqlite3
import sys

def run():
    runner = EngineRunner()

    corpus = type("Corpus", (), {"root_path": "tools/analysis/engine"})()

    result = runner.run(
        corpus=corpus,
        project_prefixes=[],
        repo_root=".",
        connection=sqlite3.connect(":memory:"),
        chaos_mode=False,   # 👈 toggle this
    )

    report = compute_health(result)
    print_health(report)

if __name__ == "__main__":
    with open("test.txt", "w") as f:
        sys.stdout = f
        run()
    sys.stdout = sys.__stdout__  # restore after