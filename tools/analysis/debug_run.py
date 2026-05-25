from tools.analysis.run_analysis_pipeline import run_analysis_pipeline


if __name__ == "__main__":
    result = run_analysis_pipeline(
        project_root="tools/analysis",
        database_path="debug.db",
        project_prefixes=[],
    )

print(result["metrics"]["total_edges"])

print(
    result["metrics"]["bucket_totals"]["classification_gap"]
    / max(1, result["metrics"]["total_edges"])
)

metrics = result["metrics"]

total_edges = metrics["total_edges"]
bucket = metrics["bucket_totals"]

assert (
    bucket["project"]
    + bucket["builtin"]
    + bucket["classification_gap"]
    + bucket["external_lib"]
    + bucket["runtime"]
    + bucket["unresolved_qualified_reference"]
    == total_edges
)

print("✔ EDGE CONSERVATION OK")

print("project ratio:",
      bucket["project"] / max(1, total_edges))

print("gap ratio:",
      bucket["classification_gap"] / max(1, total_edges))