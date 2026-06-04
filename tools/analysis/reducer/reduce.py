# tools\analysis\reducer\reduce.py

def reduce(file_analyses):
    edge_activity_total= 0
    reduced_gap = 0
    reduced_builtin = 0

    for i, snap in enumerate(file_analyses):

        print("\n[REDUCE STEP]", i)

        print("snapshot id:", snap.get("file_path", f"file_{i}"))

        edge_activity = snap.get("edge_count", 0)
        bs = snap.get("bucket_summary", {})

        gap = bs.get("classification_gap", 0)
        builtin = bs.get("builtin", 0)
        project = bs.get("project", 0) # reserved for future structural signal

        print("incoming values:")
        print("  edge_activity:", edge_activity)
        print("  gap:", gap)
        print("  builtin:", builtin)
        print("  project:", project) # reserved for future structural signal

        # ---- FOLD STEP ----
        before = (edge_activity_total, reduced_gap, reduced_builtin)

        edge_activity_total += edge_activity
        reduced_gap += gap
        reduced_builtin += builtin

        after = (edge_activity_total, reduced_gap, reduced_builtin)

        print("fold:")
        print("  before:", before)
        print("  after:", after)

    print("\nFINAL REDUCED STATE")
    print("edge_activity_total:", edge_activity_total)
    print("gap:", reduced_gap)
    print("builtin:", reduced_builtin)
    print("=" * 80)

    print("\n[STEP 6 - FINAL INVARIANT CHECK]")

    assert edge_activity_total >= 0, "edge_activity_total negative?"
    assert reduced_gap >= 0, "gap negative?"
    assert reduced_builtin >= 0, "builtin negative?"

    return {
        "edge_activity_total": edge_activity_total,
        "gap": reduced_gap,
        "builtin": reduced_builtin
    }