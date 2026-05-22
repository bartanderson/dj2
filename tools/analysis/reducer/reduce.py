# tools\analysis\reducer\reduce.py

def reduce(file_analyses):
    reduced_edges = 0
    reduced_gap = 0
    reduced_builtin = 0

    for i, snap in enumerate(file_analyses):

        print("\n[REDUCE STEP]", i)

        print("snapshot id:", snap.get("file_path", f"file_{i}"))

        edge = snap.get("edge_count", 0)
        bs = snap.get("bucket_summary", {})

        gap = bs.get("classification_gap", 0)
        builtin = bs.get("builtin", 0)
        project = bs.get("project", 0)

        print("incoming values:")
        print("  edge:", edge)
        print("  gap:", gap)
        print("  builtin:", builtin)
        print("  project:", project)

        # ---- FOLD STEP ----
        before = (reduced_edges, reduced_gap, reduced_builtin)

        reduced_edges += edge
        reduced_gap += gap
        reduced_builtin += builtin

        after = (reduced_edges, reduced_gap, reduced_builtin)

        print("fold:")
        print("  before:", before)
        print("  after:", after)

    print("\nFINAL REDUCED STATE")
    print("edges:", reduced_edges)
    print("gap:", reduced_gap)
    print("builtin:", reduced_builtin)
    print("=" * 80)

    print("\n[STEP 6 - FINAL INVARIANT CHECK]")

    assert reduced_edges >= 0, "edges negative?"
    assert reduced_gap >= 0, "gap negative?"
    assert reduced_builtin >= 0, "builtin negative?"

    return {
        "edges": reduced_edges,
        "gap": reduced_gap,
        "builtin": reduced_builtin
    }