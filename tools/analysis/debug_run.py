from tools.analysis.run_analysis_pipeline import run_analysis_pipeline


if __name__ == "__main__":
    result = run_analysis_pipeline(
        project_root="tools/analysis",
        database_path="debug.db",
        project_prefixes=[],
    )

    print(result["edge_count"])
    print(result["gap_rate"])
    print(result["project_ratio"])