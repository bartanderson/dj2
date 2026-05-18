from collections import defaultdict
from tools.analysis.graph.semantic_roles import classify_semantic_role


def score_node(node_name: str) -> int:
    if not node_name:
        return 0

    lowered = node_name.lower()

    if lowered == "print":
        return -10
    if lowered == "<module>":
        return -8
    if lowered.startswith("test_"):
        return -6
    if lowered == "main":
        return -4

    if "." in node_name:
        return 3

    if node_name and node_name[0].isupper():
        return 5

    return 1


def build_evaluation_snapshot(
    analysis,
    bucket_counts,
    graph,
    failure_events=None,
):
    failure_events = failure_events or []
    failure_breakdown = defaultdict(int)
    unknown_examples = []
    for event in failure_events:
        if not isinstance(event, dict):
            continue

        bucket = event.get("bucket", "unknown")
        failure_breakdown[bucket] += 1

        # keep only a few samples (avoid log explosion)
        if len(unknown_examples) < 10:
            unknown_examples.append(event)
                
    node_degree = defaultdict(int)

    for edge in graph.edges:
        node_degree[edge.caller] += 1
        node_degree[edge.callee] += 1

    weighted_nodes = []

    for node, degree in node_degree.items():
        weighted_score = degree + score_node(node)
        role = classify_semantic_role(node)

        weighted_nodes.append(
            (node, degree, weighted_score, role)
        )

    top_nodes = sorted(weighted_nodes, key=lambda x: -x[2])[:10]

    high_fanout = [
        (n, d, s, r)
        for n, d, s, r in top_nodes
        if s > 3
    ]

    failure_breakdown = defaultdict(int)

    for event in failure_events:
        if not event:
            continue

        if isinstance(event, dict):
            bucket = event.get("bucket", "classification_gap")
        else:
            bucket = str(event)

        failure_breakdown[bucket] += 1

    return {
        "file_count": getattr(analysis, "file_count", None),
        "edge_count": len(graph.edges),

        "bucket_summary": dict(bucket_counts),

        "graph_insights": {
            "top_nodes_by_degree": top_nodes,
        },

        "structural_signals": {
            "high_fanout_nodes": high_fanout,
        },

        # NEW STRUCTURED FAILURE VIEW
        "failure_breakdown": dict(failure_breakdown),
        "unknown_samples": unknown_examples,
    }