from tools.analysis.context.build_context_bundle import build_context_bundle
import sqlite3

conn = sqlite3.connect("tools/analysis/data/analysis.db")

bundle = build_context_bundle(
    conn,
    "tools/analysis/run_analysis_pipeline.py"
)

print(bundle)