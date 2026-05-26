from tools.analysis.graph.symbol_classifier import classify_symbol


def test_no_mass_classification_gap():
    symbols = [
        "create_database",
        "Path",
        "defaultdict",
        "len",
        "requests.get",
        "field",
    ]

    counts = {}

    for s in symbols:
        result = classify_symbol(
            name=s,
            route="unknown",
            project_prefixes=[],
            runtime_bindings={},
            project_symbols=set(),
        )

        counts[result] = counts.get(result, 0) + 1

    # Keep classifier from collapsing into a single failure bucket
    assert counts.get("unresolved_qualified_reference", 0) <= 4


def test_route_priority():
    # route override behavior
    assert classify_symbol("anything", "project", [], None, set()) == "project"
    assert classify_symbol("anything", "builtin", [], None, set()) == "builtin"
    assert classify_symbol("anything", "stdlib", [], None, set()) == "stdlib"
    assert classify_symbol("anything", "runtime", [], None, set()) == "runtime"


def test_symbol_classifier_matrix():
    cases = [
        # PROJECT
        ("create_database", "project", "project"),
        ("tools.analysis.graph", "project", "project"),

        # BUILTIN
        ("len", "unknown", "builtin"),
        ("dict", "unknown", "builtin"),

        # STDLIB (heuristic-based)
        ("pathlib.Path", "unknown", "stdlib"),
        ("Path", "unknown", "stdlib"),
        ("defaultdict", "unknown", "stdlib"),
        ("field", "unknown", "stdlib"),

        # RUNTIME
        ("SomeRuntimeSymbol", "runtime", "runtime"),

        # EXTERNAL
        ("requests.get", "external", "external_lib.requests"),

        # FALLBACK
        ("weird_symbol_xyz", "unknown", "unresolved_qualified_reference"),
    ]

    for name, route, expected in cases:
        result = classify_symbol(
            name=name,
            route=route,
            project_prefixes=[],
            runtime_bindings={"SomeRuntimeSymbol": "runtime"},
            project_symbols=set(),
        )

        assert result == expected, f"{name=} {route=} => {result}, expected {expected}"


def test_symbol_drift_detection():
    baseline = {
        "Path": "stdlib",
        "defaultdict": "stdlib",
        "create_database": "unresolved_qualified_reference",
    }

    for sym, expected in baseline.items():
        result = classify_symbol(sym, "unknown", [], {}, set())
        assert result == expected


def test_pipeline_replay():
    """
    Minimal forward-facing sanity test.

    We do NOT depend on snapshot structure anymore.
    We only validate that extract_metrics runs and produces coherent totals.
    """
    from tools.analysis.metrics.extract_metrics import extract_metrics

    fake_snapshots = [
        {
            "edge_count": 3,
            "bucket_summary": {
                "project": 1,
                "builtin": 1,
                "runtime": 1,
                "classification_gap": 0,
                "external_lib": 0,
                "unresolved_qualified_reference": 0,
            },
            "failure_breakdown": {},
            "unknown_samples": [],
        }
    ]

    metrics = extract_metrics(fake_snapshots)

    assert metrics["total_edges"] > 0
    assert "bucket_totals" in metrics
    assert isinstance(metrics["bucket_totals"], dict)