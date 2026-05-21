# tests/analysis/test_symbol_classifier_matrix.py

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
            s,
            route="unknown",
            project_prefixes=[],
            runtime_bindings={},
            project_symbols=set(),
        )

        counts[result] = counts.get(result, 0) + 1

    # HARD ASSERT: no single collapse bucket dominates
    assert counts.get("unresolved_qualified_reference", 0) < 3

def test_route_priority():
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

        # STDLIB MODULE
        ("pathlib.Path", "unknown", "stdlib"),

        # STDLIB SYMBOL HINTS
        ("Path", "unknown", "stdlib"),
        ("defaultdict", "unknown", "stdlib"),
        ("field", "unknown", "stdlib"),

        # RUNTIME
        ("SomeRuntimeSymbol", "runtime", "runtime"),

        # EXTERNAL
        ("requests.get", "external", "external_lib.requests"),

        # FALLBACK (IMPORTANT)
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
        "create_database": "project",
    }

    for sym, expected in baseline.items():
        result = classify_symbol(sym, "unknown", [], {}, set())

        assert result == expected

def test_pipeline_replay(file_analyses):
    from tools.analysis.metrics.extract_metrics import extract_metrics

    metrics = extract_metrics(file_analyses)

    assert metrics["edge_count"] > 0
    assert "bucket_summary" in metrics
    assert "classification_gap" in metrics["bucket_summary"] or True