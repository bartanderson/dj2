# tools/analysis/metrics/extract_metrics.py

from __future__ import annotations


def extract_metrics(file_analyses: list) -> dict:
    # ================================
    # RAW DISTRIBUTION DEBUG ENTRY
    # ================================
    print("\n================ METRICS RAW INPUT ================\n")
    print("file_count:", len(file_analyses))

    # ----------------------------
    # INPUT EXTRACTION + FILE SAMPLE DEBUG
    # ----------------------------

    total_gap = 0
    total_builtin = 0
    total_edges = 0
    total_project = 0

    bucket_breakdown  = {}

    for i, a in enumerate(file_analyses):

        bs = a.get("bucket_summary", {})

        # ----------------------------
        # BUCKET CONTRACT VALIDATION
        # ----------------------------
        required_keys = ["classification_gap", "builtin", "project"]

        for k in required_keys:
            if k not in bs:
                print(f"⚠ missing bucket key: {k}")

        edges = a.get("edge_count", 0)

        gap = bs.get("classification_gap", 0)
        builtin = bs.get("builtin", 0)
        project = bs.get("project", 0)

        total_gap += gap
        total_builtin += builtin
        total_edges += edges
        total_project += project

        # FILE SAMPLE DEBUG (ONLY FIRST 3 FILES)
        if i < 3:
            print("\n---------------- FILE SAMPLE ----------------")
            print("index:", i)
            print("edges:", edges)
            print("gap:", gap)
            print("builtin:", builtin)

    bucket_breakdown  = {}
    for a in file_analyses:
        fb = a.get("bucket_breakdown ", {})
        for k, v in fb.items():
            bucket_breakdown [k] = bucket_breakdown .get(k, 0) + v

    # ----------------------------
    # DEBUG INPUT (ONLY SEMANTIC BOUNDARY)
    # ----------------------------
    print("\n" + "=" * 90)
    print("📊 METRICS INPUT BOUNDARY")
    print("file_count:", len(file_analyses))

    print("total_edges:", total_edges)
    print("total_gap:", total_gap)
    print("total_builtin:", total_builtin)
    print("TOTAL PROJECT:", total_project)
    print("\n================ VALIDATION =================\n")

    assert total_project >= 0
    assert total_edges >= 0
    assert total_builtin >= 0

    print("PROJECT sanity check:", total_project, "vs edges:", total_edges)

    if total_project == 0 and total_edges > 0:
        print("⚠ WARNING: project signal is completely missing from pipeline")
    # ----------------------------
    # COMPUTATION
    # ----------------------------
    classification_gap = total_gap
    runtime = total_builtin

    gap_rate = classification_gap / max(1, total_edges)
    project_ratio = total_project / max(1, total_edges)

    # ----------------------------
    # OUTPUT RESULT
    # ----------------------------
    metrics = {
        "edge_count": total_edges,
        "bucket_summary": {
            "classification_gap": total_gap,
            "builtin": total_builtin,
        },
        "bucket_breakdown ": bucket_breakdown ,
        "gap_rate": gap_rate,
        "runtime_noise": runtime,
        "project_ratio": project_ratio,
    }

    # ----------------------------
    # DEBUG OUTPUT
    # ----------------------------
    print("\n" + "=" * 90)
    print("📈 METRICS OUTPUT BOUNDARY")
    print("gap_rate:", gap_rate)
    print("runtime_noise:", runtime)
    print("project_ratio:", project_ratio)

    print("\n================ GLOBAL TOTALS ================\n")
    print("edges:", total_edges)
    print("gap:", total_gap)
    print("builtin:", total_builtin)

    print("\n================ NORMALIZED CHECKS ================\n")
    print("gap/edges:", total_gap / max(1, total_edges))
    print("builtin/edges:", total_builtin / max(1, total_edges))

    return metrics